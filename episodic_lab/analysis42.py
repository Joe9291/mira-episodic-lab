"""Round 4.2 model-free analysis (docs/ROUND_4_2.md sections 1, 3, 5, 6): decisions from
recorded encodings, threshold calibration, the collector, arms G / E, the two comparisons
per question, the cause analysis and the repair check.

The extraction side (decide_note, collect) uses only the encoding, the note header and
the world's source names; gold reports are used only for calibration and scoring.
"""
from __future__ import annotations

from .cands42 import KEEP, USES, allowed_surface, decide, ranking, truth
from .r40_memory import Memory
from .r40_reference import reference_answers

RANKS = {"own": 3, "trusted": 2, "hearsay": 1}
TYPE_TO_KIND = {"statement": ("assert", False), "repeated statement": ("assert", True),
                "correction": ("correct", False), "retraction": ("retract", False), "meeting": ("assert", False)}


def _scored(encoding: dict, slot: str, predicted_type: str | None):
    rows = encoding[slot]
    if predicted_type is not None:
        rows = [r for r in rows if allowed_surface(slot, r[0], predicted_type)]
    return [(s, c, x) for s, c, x in rows]


def decide_note(encoding: dict, taus: dict) -> dict:
    """{"status": "ok" | "declined", "type", "fields", "reason", "decisions"}: the type
    first, then only the slots of the predicted type with their allowed candidates."""
    t, m, st = decide(_scored(encoding, "type", None), taus.get("type"))
    decisions = {"type": [t, m, st]}
    if st == "unknown":
        return {"status": "declined", "type": None, "fields": {}, "reason": "type uncertain", "decisions": decisions}
    fields = {}
    for slot in USES[t]:
        v, m, st = decide(_scored(encoding, slot, t), taus.get(slot))
        decisions[slot] = [v, m, st]
        if st == "unknown":
            return {"status": "declined", "type": t, "fields": fields, "reason": f"{slot} uncertain",
                    "decisions": decisions}
        fields[slot] = v
    if t == "correction" and fields.get("value") == KEEP and fields.get("valid_from") == KEEP:
        return {"status": "declined", "type": t, "fields": fields, "reason": "correction keeps both", "decisions": decisions}
    return {"status": "ok", "type": t, "fields": fields, "reason": None, "decisions": decisions}


# ---------------------------------------------------------------- calibration
def calibrate(cases: list[tuple], min_accepted: int = 200, precision: float = 0.99):
    """cases: (margin or None for a single candidate, correct?) of one slot. Returns the
    smallest tau with the highest acceptance among taus with precision >= 0.99 and
    >= min_accepted accepted values; None if no tau qualifies (the slot always declines)."""
    margins = sorted({0.0} | {m for m, _ in cases if m is not None})
    best = None
    for tau in margins:
        acc = [ok for m, ok in cases if m is None or (m > 0 and m >= tau)]
        if len(acc) >= min_accepted and sum(acc) >= precision * len(acc):
            if best is None or len(acc) > best[1]:
                best = (tau, len(acc))
    return None if best is None else best[0]


def calibration_cases(notes: list[dict], encodings: dict) -> dict:
    """Per slot, (margin, correct) over the notes whose TRUE type uses the slot, with the
    candidate filter of the true type (type: over all notes)."""
    out = {}
    for n in notes:
        enc = encodings[n["key"]]
        tr = n["truth"]
        v, m, n_vals = ranking(_scored(enc, "type", None))
        out.setdefault("type", []).append((m, v == tr["type"]))
        for slot in USES[tr["type"]]:
            v, m, _ = ranking(_scored(enc, slot, tr["type"]))
            out.setdefault(slot, []).append((m, v == tr[slot]))
    return out


# ---------------------------------------------------------------- collector
def collect(notes: list[dict], decisions: dict, policy_ranks: dict) -> tuple[list[dict], list[dict]]:
    """Arm E: notes in arrival order -> stored reports (same ids as the notes) and a log
    per note. References are resolved only against reports already stored in E."""
    stored, log = [], []
    for n in notes:
        d = decisions[n["note_id"]]
        entry = {"note_id": n["note_id"], "status": d["status"], "type": d["type"], "reason": d["reason"],
                 "fields": d["fields"], "decisions": d["decisions"]}
        if d["status"] != "ok":
            log.append(entry)
            continue
        f, t = d["fields"], d["type"]
        author, rd = n["author"], n["report_day"]
        rep = {"report_id": n["note_id"], "report_day": rd, "source": author, "rank": policy_ranks[author],
               "origin": "o-" + n["note_id"], "kind": TYPE_TO_KIND[t][0], "value": None, "valid_from": None,
               "target_report_id": None}
        if t == "meeting":
            rep.update(subject=f"event:met {f['person']} at {f['place']}", attribute="day", value=f["day"], valid_from=0)
        else:
            rep.update(subject="the " + f["subject"], attribute=f["attribute"])
            if t in ("statement", "repeated statement"):
                rep.update(value=f["value"], valid_from=f["valid_from"])
            if t == "correction":
                rep.update(value=None if f["value"] == KEEP else f["value"],
                           valid_from=None if f["valid_from"] == KEEP else f["valid_from"])
            if t != "statement":
                key = (f["ref_source"], f["ref_day"], rep["subject"], rep["attribute"])
                hits = [r for r in stored if (r["source"], r["report_day"], r["subject"], r["attribute"]) == key]
                if len(hits) != 1:
                    entry.update(status="declined", reason=f"reference unresolved ({len(hits)} matches)")
                    log.append(entry)
                    continue
                if t == "repeated statement":
                    rep["origin"] = hits[0]["origin"]
                else:
                    rep["target_report_id"] = hits[0]["report_id"]
        stored.append(rep)
        entry["report"] = rep
        log.append(entry)
    return stored, log


# ---------------------------------------------------------------- arms, causes, repair
def answer_all(reports, questions):
    m = Memory(reports)
    return {q["qid"]: m.answer(q) for q in questions}, reference_answers(reports, questions)[0]


def relevant_note_ids(gold: list[dict], fact, anchor) -> set:
    """Notes of the asked fact and of its anchor event in G, plus everything they reference
    (targets, repeated statements), transitively."""
    by_id = {r["report_id"]: r for r in gold}
    keys = {tuple(fact)} | ({("event:" + anchor, "day")} if anchor else set())
    ids = {r["report_id"] for r in gold if (r["subject"], r["attribute"]) in keys}
    changed = True
    while changed:
        changed = False
        for rid in list(ids):
            r = by_id[rid]
            for ref in (r["target_report_id"], r["origin"][2:] if r["origin"] != "o-" + rid else None):
                if ref and ref not in ids:
                    ids.add(ref)
                    changed = True
    return ids


def note_status(gold: list[dict], stored: list[dict]) -> dict:
    """Per note: "correct" (E report equals G report), "declined" (not stored) or "wrong"."""
    g = {r["report_id"]: r for r in gold}
    e = {r["report_id"]: r for r in stored}
    return {rid: ("declined" if rid not in e else "correct" if e[rid] == g[rid] else "wrong") for rid in g}


def repair(gold: list[dict], stored: list[dict], scope: set, fact, anchor) -> list[dict]:
    """A copy of E where the notes of the repair scope get their gold reports (same ids)
    and reports injected into the asked fact or its anchor are removed."""
    keys = {tuple(fact)} | ({("event:" + anchor, "day")} if anchor else set())
    g = {r["report_id"]: r for r in gold}
    out = {}
    for r in stored:
        if r["report_id"] in scope:
            continue
        if (r["subject"], r["attribute"]) in keys and (g[r["report_id"]]["subject"], g[r["report_id"]]["attribute"]) not in keys:
            continue                                             # injected into the asked fact / anchor
        out[r["report_id"]] = r
    for rid in scope:
        out[rid] = g[rid]
    return [out[k] for k in sorted(out, key=lambda k: (out[k]["report_day"], k))]


def fields_correct(decision: dict, tr: dict) -> bool:
    if decision["type"] != tr["type"]:
        return False
    return all(decision["fields"].get(s) == tr[s] for s in USES[tr["type"]])


def expected_report(note: dict, decision: dict, history: list[dict], policy_ranks: dict):
    """An independent restatement of the collector contract for ONE note, given the E
    history before it (used to detect collector errors); None = the note must be declined."""
    if decision["status"] != "ok":
        return None
    f, t = decision["fields"], decision["type"]
    base = {"report_id": note["note_id"], "report_day": note["report_day"], "source": note["author"],
            "rank": policy_ranks[note["author"]], "origin": "o-" + note["note_id"], "target_report_id": None}
    if t == "meeting":
        return dict(base, kind="assert", subject="event:met %s at %s" % (f["person"], f["place"]),
                    attribute="day", value=f["day"], valid_from=0)
    subj = "the " + f["subject"]
    rep = dict(base, subject=subj, attribute=f["attribute"])
    if t == "statement":
        return dict(rep, kind="assert", value=f["value"], valid_from=f["valid_from"])
    match = [r for r in history if r["source"] == f["ref_source"] and r["report_day"] == f["ref_day"]
             and r["subject"] == subj and r["attribute"] == f["attribute"]]
    if len(match) != 1:
        return None
    if t == "repeated statement":
        return dict(rep, kind="assert", value=f["value"], valid_from=f["valid_from"], origin=match[0]["origin"])
    if t == "retraction":
        return dict(rep, kind="retract", value=None, valid_from=None, target_report_id=match[0]["report_id"])
    return dict(rep, kind="correct", value=None if f["value"] == KEEP else f["value"],
                valid_from=None if f["valid_from"] == KEEP else f["valid_from"],
                target_report_id=match[0]["report_id"])


def collector_errors(notes, decisions, stored, policy_ranks) -> list[str]:
    e = {r["report_id"]: r for r in stored}
    history, bad = [], []
    for n in notes:
        exp = expected_report(n, decisions[n["note_id"]], history, policy_ranks)
        got = e.get(n["note_id"])
        if exp != got:
            bad.append(n["note_id"])
        if got is not None:
            history.append(got)
    return bad


def causes(gold, stored, notes, decisions, truths, fact, anchor) -> dict:
    """Causes in the scope of one asked fact (and its anchor), by note id."""
    status = note_status(gold, stored)
    scope = relevant_note_ids(gold, fact, anchor)
    keys = {tuple(fact)} | ({("event:" + anchor, "day")} if anchor else set())
    g = {r["report_id"]: r for r in gold}
    out = {"direct": [], "follow_up": [], "injected": []}
    for rid in sorted(scope):
        if status[rid] == "correct":
            continue
        if fields_correct(decisions[rid], truths[rid]):
            out["follow_up"].append(rid)
        else:
            out["direct"].append(rid)
    for r in stored:
        if (r["subject"], r["attribute"]) in keys and (g[r["report_id"]]["subject"], g[r["report_id"]]["attribute"]) not in keys:
            out["injected"].append(r["report_id"])
    out["repair_scope"] = sorted(rid for rid in scope if status[rid] != "correct")
    return out
