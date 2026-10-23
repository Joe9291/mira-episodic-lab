"""Round 4.2 model-free analysis (docs/ROUND_4_2.md sections 1, 3, 5, 6): decisions from
recorded encodings, threshold calibration, the collector, arms G / E, the two comparisons
per question, the cause analysis and the repair check.

The extraction side (decide_note, collect) uses only the encoding, the note header and
the world's source names; gold reports are used only for calibration and scoring.
"""
from __future__ import annotations

from .cands42 import KEEP, USES, allowed_surface, decide, ranking, truth, used_slots
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


def apply_priors(encoding: dict, priors: dict | None) -> dict:
    """Label-prior correction (development option after probe 5, encoder42.label_priors):
    score minus the label's content-free log-prior, for the label slots only."""
    if not priors:
        return encoding
    return {slot: [[s, c, x - priors[slot][s]] if slot in priors else [s, c, x] for s, c, x in rows]
            for slot, rows in encoding.items()}


# ---------------------------------------------------------------- label offsets (variant D)
# Astra's decision on the development decision package (reviews/2026-10-23_r42dev_astra.txt):
# additive offsets s'_y = s_y + b_y for the label slots type, attribute and change, fitted
# per model and slot on the DISTINCT development notes whose TRUE type uses the slot
# (type: all notes); first label fixed at 0; grid step 0.25 in [-30, 30]; objective = the
# number of right top-1 choices; start at 0, fixed coordinate order (the label order of
# cands42), ties -> smallest L1 norm, then the lexicographically smallest vector; stop
# after a full pass without change. Then the offsets are frozen and tau is calibrated on
# the full calibration split with the corrected scores.
LABEL_SLOTS = ("type", "attribute", "change")
GRID = tuple(x / 4 for x in range(-120, 121))


def top_label(scores: dict, offsets: dict):
    """The label with the strictly highest corrected score; None on a tie (a margin of 0 is
    declined by every threshold, so a tie never counts as right)."""
    ranked = sorted(scores, key=lambda lab: (-(scores[lab] + offsets.get(lab, 0.0)), lab))
    if len(ranked) > 1 and scores[ranked[0]] + offsets.get(ranked[0], 0.0) == scores[ranked[1]] + offsets.get(ranked[1], 0.0):
        return None
    return ranked[0]


def fit_offsets(rows: list[tuple], labels: list[str]) -> dict:
    """rows: (scores {label surface: raw score}, true label surface). Returns {"offsets",
    "right_raw", "right", "n", "passes", "at_grid_edge"}."""
    b = {lab: 0.0 for lab in labels}

    def key(vec):
        right = sum(top_label(sc, vec) == y for sc, y in rows)
        return (right, -sum(abs(v) for v in vec.values()), tuple(-vec[lab] for lab in labels))

    best = key(b)
    passes = 0
    while True:
        passes += 1
        changed = False
        for lab in labels[1:]:
            for v in GRID:
                trial = dict(b, **{lab: v})
                k = key(trial)
                if k > best:
                    best, b, changed = k, trial, True
        if not changed or passes >= 100:
            break
    return {"offsets": b, "right_raw": sum(top_label(sc, {}) == y for sc, y in rows), "right": best[0],
            "n": len(rows), "passes": passes, "at_grid_edge": [lab for lab in labels if abs(b[lab]) >= GRID[-1]]}


def offset_rows(notes: list[dict], encodings: dict, slot: str) -> list[tuple]:
    """Fit rows of one label slot: distinct notes whose TRUE type uses the slot (type: all)."""
    rows = []
    for n in notes:
        tr = n["truth"]
        if slot != "type" and slot not in used_slots(tr["type"], tr):
            continue
        sc = {s: x for s, c, x in encodings[n["key"]][slot]}
        label = [s for s, c, x in encodings[n["key"]][slot] if c == tr[slot]]
        rows.append((sc, label[0]))
    return rows


def apply_offsets(encoding: dict, offsets: dict | None) -> dict:
    """offsets: {slot: {label surface: b}} for label slots; other slots unchanged."""
    if not offsets:
        return encoding
    return {slot: [[s, c, x + offsets[slot][s]] if slot in offsets else [s, c, x] for s, c, x in rows]
            for slot, rows in encoding.items()}


def decide_note(encoding: dict, taus: dict) -> dict:
    """{"status": "ok" | "declined", "type", "fields", "reason", "decisions"}: the type
    first, then only the slots of the predicted type with their allowed candidates."""
    t, m, st = decide(_scored(encoding, "type", None), taus.get("type"))
    decisions = {"type": [t, m, st]}
    if st == "unknown":
        return {"status": "declined", "type": None, "fields": {}, "reason": "type uncertain", "decisions": decisions}
    fields = {}
    for slot in USES[t]:
        if slot not in used_slots(t, fields):          # a correction's unchanged field
            fields[slot] = KEEP
            continue
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
    """Per slot, (margin, correct) along the PREDICTED decision path (Astra, development
    decision review): the top-1 type selects the slots, the top-1 change selects value /
    since; a slot is right only if its top-1 equals the note's true value of that slot (a
    slot the true type does not have, or a "keep" field asked, counts as wrong). Earlier
    slots are followed by their top-1 choice, before any threshold."""
    out = {}
    for n in notes:
        enc = encodings[n["key"]]
        tr = n["truth"]
        t, m, _ = ranking(_scored(enc, "type", None))
        out.setdefault("type", []).append((m, t == tr["type"]))
        fields = {}
        for slot in USES[t]:
            if slot not in used_slots(t, fields):
                fields[slot] = KEEP
                continue
            v, m, _ = ranking(_scored(enc, slot, t))
            fields[slot] = v
            out.setdefault(slot, []).append((m, v is not None and v == tr.get(slot)))
    return out


def slot_report(notes: list[dict], encodings: dict, taus: dict) -> dict:
    """Per slot along the ACTUAL decisions (decide_note with tau): asked, accepted, wrong
    accepted, precision of accepted values (None if nothing accepted - never passes)."""
    out = {}
    for n in notes:
        d = decide_note(encodings[n["key"]], taus)
        tr = n["truth"]
        for slot, (v, m, st) in d["decisions"].items():
            r = out.setdefault(slot, {"asked": 0, "accepted": 0, "wrong": 0, "wrongly_skipped": 0})
            r["asked"] += 1
            if st in ("ok", "single"):
                r["accepted"] += 1
                r["wrong"] += v != tr.get(slot)
        ch = d["decisions"].get("change")
        if d["type"] == tr["type"] == "correction" and ch and ch[2] in ("ok", "single"):
            for slot in ("value", "valid_from"):       # a required field skipped by a wrong change
                if slot in used_slots(tr["type"], tr) and slot not in used_slots(d["type"], {"change": ch[0]}):
                    out.setdefault(slot, {"asked": 0, "accepted": 0, "wrong": 0, "wrongly_skipped": 0})
                    out[slot]["wrongly_skipped"] += 1
    for r in out.values():
        r["precision"] = None if r["accepted"] == 0 else round(1 - r["wrong"] / r["accepted"], 4)
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


def mark_critical(rows: list[dict]) -> None:
    """A question is CRITICAL if its gold answer differs between the worlds A and B of its
    pair at the same delay (same question position), under the round 4.0 hit definition."""
    from .r40_analysis import hit
    by = {}
    for r in rows:
        pos = r["qid"].rsplit("-", 1)[1]
        by.setdefault((r["pair"], r["delay"], pos), {})[r["world"]] = r
    for (_, _, _), ab in by.items():
        crit = len(ab) == 2 and not hit(ab["A"]["op"], ab["A"]["gold"], ab["B"]["gold"])
        for r in ab.values():
            r["critical"] = crit


def rule6(rows: list[dict], families, delays, pairs_per_family: int, questions_per_world: dict) -> dict:
    """Pass rule 6 (design v3 + Astra's late review): in EVERY family x delay cell
    (a) >= 90 % of all questions right, (b) >= 90 % of the critical questions right,
    (c) >= 90 % pair success, a pair counting only if both worlds answer ALL critical
    questions of that delay right; exact denominators, and an empty or unexpected
    denominator fails the cell."""
    cells, ok = {}, True
    for f in families:
        for d in delays:
            sel = [r for r in rows if r["family"] == f and r["delay"] == d]
            crit = [r for r in sel if r["critical"]]
            pairs = sorted({r["pair"] for r in sel})
            succ = [p for p in pairs if all(r["e2e"] for r in crit if r["pair"] == p)
                    and any(r["pair"] == p for r in crit)]
            n_exp = questions_per_world[f] * 2 * pairs_per_family
            c = {"all": [sum(r["e2e"] for r in sel), len(sel)], "critical": [sum(r["e2e"] for r in crit), len(crit)],
                 "pairs": [len(succ), len(pairs)],
                 "denominators_ok": len(sel) == n_exp and len(crit) > 0 and len(pairs) == pairs_per_family
                 and all(any(r["pair"] == p for r in crit) for p in pairs)}
            c["ok"] = c["denominators_ok"] and all(k * 10 >= 9 * n for k, n in (c["all"], c["critical"], c["pairs"]))
            cells[f"{f}|{d}"] = c
            ok &= c["ok"]
    return {"ok": ok, "cells": cells}
