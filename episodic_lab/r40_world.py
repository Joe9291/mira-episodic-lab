"""Round 4.0 generator (docs/ROUND_4_0.md sections 1, 3, 4): paired worlds A / B for the
phenomena P1-P9, irrelevant reports for the four delays, questions, the world truth,
interventions as valid counterfactual worlds (with removal cascades) and the generator
audit.

A pair's worlds differ ONLY in the content of one critical report (same id, same day);
everything else - other reports, their ids and days, the irrelevant reports, the
questions - is identical. Every random choice comes from HashRng, so worlds are
byte-identical everywhere.
"""
from __future__ import annotations

import hashlib
import json

from .r40_reference import _step
from .r40_schema import ANCHOR_ATTRIBUTE, ANCHOR_PREFIX, check_report, order_key
from .rng import HashRng
from .world import FIRST, LAST, OBJ_ADJ, OBJ_NOUN, PLACE_KIND, PLACE_STEM

GENERATOR_VERSION = "r40.g1"
FAMILIES = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9")
QUESTION_TABLE = {
    "P1": ("current", "valid_at", "believed_at", "history"),
    "P2": ("current", "valid_at", "believed_at", "why_changed"),
    "P3": ("valid_at", "believed_at", "why_changed", "history"),
    "P4": ("valid_at", "why_changed", "history"),
    "P5": ("current", "valid_at", "believed_at", "why_changed"),
    "P6": ("current", "valid_at", "why_changed"),
    "P7": ("current|valid_at", "conflicts", "history"),
    "P8": ("current", "conflicts", "why_changed"),
    "P9": ("before", "current"),
}
DELAYS = (0, 50, 200, 500)
PAIRS = {"dev": 10, "holdout": 40}
SEEDS = {"dev": "r40-dev-1", "holdout": "r40-holdout-1"}
PER_DAY = 5                      # irrelevant reports per day
INTERVENTIONS = {
    "remove_update": ("P1",), "remove_late_report": ("P2",), "remove_correction": ("P3",),
    "remove_retraction": ("P5",), "swap_ranks": ("P3", "P4", "P7", "P8"),
    "remove_conflict_resolver": ("P8",), "move_anchor": ("P9",), "remove_anchor": ("P9",),
    "remove_obs_before_anchor": ("P9",), "irrelevant_control": FAMILIES,
}


# ------------------------------------------------------------------ vocabulary
def vocabulary(rng: HashRng) -> dict:
    people = [f"{f} {l}" for f, l in zip(rng.shuffled(FIRST), rng.shuffled(LAST))]
    places = [f"{s} {k}" for s, k in zip(rng.shuffled(PLACE_STEM), rng.shuffled(PLACE_KIND))]
    objects = [f"the {a} {n}" for a, n in zip(rng.shuffled(OBJ_ADJ), rng.shuffled(OBJ_NOUN))]
    names = rng.shuffled(FIRST)
    sources = {"self": 3, names[0]: 2, names[1]: 2, names[2]: 1, names[3]: 1}
    return {"people": people, "places": places, "objects": objects, "ranks": sources,
            "trusted": [names[0], names[1]], "hearsay": [names[2], names[3]],
            "values": {"location": places, "holder": people}}


class _Builder:
    """Report specs with symbolic references; ids are assigned in total order."""

    def __init__(self):
        self.specs: list[dict] = []

    def add(self, day, source, kind, subject, attribute, value=None, vf=None, target=None,
            repeat_of=None) -> int:
        self.specs.append({"day": day, "source": source, "kind": kind, "subject": subject,
                           "attribute": attribute, "value": value, "vf": vf,
                           "target": target, "repeat_of": repeat_of})
        return len(self.specs) - 1


def finalize(specs: list[dict], ranks: dict) -> tuple[list[dict], dict]:
    """Specs -> reports in total order with ids r00001...; returns (reports, sym -> id)."""
    order = sorted(range(len(specs)), key=lambda i: (specs[i]["day"], i))
    ids = {sym: f"r{n + 1:05d}" for n, sym in enumerate(order)}
    reports = []
    for sym in order:
        s = specs[sym]
        origin = ("o-" + ids[s["repeat_of"]]) if s["repeat_of"] is not None else ("o-" + ids[sym])
        reports.append({"report_id": ids[sym], "report_day": s["day"], "source": s["source"],
                        "rank": ranks[s["source"]], "origin": origin, "subject": s["subject"],
                        "attribute": s["attribute"], "kind": s["kind"], "value": s["value"],
                        "valid_from": s["vf"],
                        "target_report_id": ids[s["target"]] if s["target"] is not None else None})
    return reports, ids


def _g(rng, lo, hi):
    return lo + rng.below(hi - lo + 1)


# ------------------------------------------------------------------ families
def _family(fam: str, rng: HashRng, voc: dict, idx: int) -> dict:
    """One pair's relevant reports (as specs), the critical report and its B content,
    the questions, the truth of both worlds and the intervention targets."""
    b = _Builder()
    attribute = ("location", "holder")[rng.below(2)]
    subject = voc["objects"][0]
    pool = rng.shuffled(voc["values"][attribute])
    T1, T2 = voc["trusted"]
    H1, H2 = voc["hearsay"]
    A = lambda *a, **k: b.add(*a, subject=subject, attribute=attribute, **k)  # noqa: E731
    out = {"fact": [subject, attribute], "anchor": None, "anchor_day": None, "iv": {}}
    X, Y, Z, W, V, U = pool[:6]

    if fam == "P1":
        Q = (T1, T2)[rng.below(2)]
        d1 = _g(rng, 1, 3); vfc = d1 + _g(rng, 3, 6); d3 = vfc + _g(rng, 0, 2)
        r1 = A(d1, Q, "assert", value=X, vf=d1)
        if rng.below(2):
            A(d1 + 1, (H1, H2)[rng.below(2)], "assert", value=X, vf=d1, repeat_of=r1)
        c = A(d3, "self", "assert", value=Y, vf=vfc)
        d4 = vfc + _g(rng, 3, 5)        # a later change: the current version is the same in A and B
        A(max(d3, d4) + _g(rng, 1, 2), "self", "assert", value=W, vf=d4)
        out.update(crit=c, b_change={"vf": d1},
                   questions=[{"op": "current"}, {"op": "valid_at", "v": _g(rng, d1, vfc - 1)},
                              {"op": "believed_at", "t": _g(rng, d1, d3 - 1)}, {"op": "history"}],
                   truth={"A": [[d1, X], [vfc, Y], [d4, W]], "B": [[d1, Y], [d4, W]]})
        out["iv"]["remove_update"] = {"remove": c}

    elif fam == "P2":
        Q = (T1, T2)[rng.below(2)]
        d1 = _g(rng, 1, 3); d2 = d1 + _g(rng, 2, 5); d3 = d2 + _g(rng, 2, 6)
        A(d1, "self", "assert", value=X, vf=d1)
        c = A(d3, Q, "assert", value=Y, vf=d2)
        d4 = d3 + _g(rng, 2, 4)         # a later change: the current version is the same in A and B
        A(d4 + _g(rng, 0, 1), "self", "assert", value=W, vf=d4)
        out.update(crit=c, b_change={"vf": d3},
                   questions=[{"op": "current"}, {"op": "valid_at", "v": _g(rng, d2, d3 - 1)},
                              {"op": "believed_at", "t": _g(rng, d2, d3 - 1)},
                              {"op": "why_changed", "v": _g(rng, d2, d3 - 1), "k1": _g(rng, d2, d3 - 1)}],
                   truth={"A": [[d1, X], [d2, Y], [d4, W]], "B": [[d1, X], [d3, Y], [d4, W]]})
        out["iv"]["remove_late_report"] = {"remove": c}

    elif fam in ("P3", "P4"):
        Q = (T1, T2)[rng.below(2)]
        d0 = _g(rng, 1, 2); d2 = d0 + _g(rng, 2, 4); d1 = d2 + _g(rng, 0, 2)
        A(d0, "self", "assert", value=X, vf=d0)
        r1 = A(d1, Q, "assert", value=Y, vf=d2)
        d3 = d1 + _g(rng, 2, 4)
        variant = idx % 3
        new_vf = None if variant == 0 else d2 + _g(rng, 2, 3)
        new_val = None if variant == 1 else Z
        d4 = max(d2, new_vf or 0) + _g(rng, 3, 5)
        hi = (new_vf - 1) if new_vf else d4 - 1
        effective = (Q, (T2 if Q == T1 else T1), "self")[rng.below(3)]
        weak = (H1, H2)[rng.below(2)]
        a_src, b_src = (effective, weak) if fam == "P3" else (weak, effective)
        c = A(d3, a_src, "correct", value=new_val, vf=new_vf, target=r1)
        A(max(d3, d4) + _g(rng, 1, 2), "self", "assert", value=W, vf=d4)
        v = _g(rng, d2, hi)
        fixed = [[d0, X], [new_vf or d2, new_val or Y], [d4, W]]
        wrong = [[d0, X], [d2, Y], [d4, W]]
        qs = [{"op": "valid_at", "v": v}]
        if fam == "P3":
            qs.append({"op": "believed_at", "t": _g(rng, d1, d3 - 1)})
        qs += [{"op": "why_changed", "v": v, "k1": _g(rng, d1, d3 - 1)}, {"op": "history"}]
        out.update(crit=c, b_change={"source": b_src}, questions=qs,
                   truth={"A": fixed if fam == "P3" else wrong, "B": wrong if fam == "P3" else fixed})
        if fam == "P3":
            out["iv"]["remove_correction"] = {"remove": c}
        out["iv"]["swap_ranks"] = {"swap_with": Q}

    elif fam in ("P5", "P6"):
        Q = (T1, T2, H1, H2)[rng.below(4)]
        Q2 = {T1: T2, T2: T1, H1: H2, H2: H1}[Q]
        d0 = _g(rng, 1, 2); d2 = d0 + _g(rng, 2, 4); d1 = d2 + _g(rng, 0, 2)
        A(d0, "self", "assert", value=X, vf=d0)
        r1 = A(d1, Q, "assert", value=Y, vf=d2)
        chain = idx % 3 == 2
        if chain:          # the target is a correction claim: only its corrector may retract it
            target = A(d1 + 1, Q2, "correct", value=V, target=r1)
            own, other, last, shown = Q2, Q, d1 + 1, V
        else:
            target, own, other, last, shown = r1, Q, Q2, d1, Y
        d3 = last + _g(rng, 2, 4)
        a_src, b_src = (own, other) if fam == "P5" else (other, own)
        c = A(d3, a_src, "retract", target=target)
        d4 = d2 + _g(rng, 3, 6)
        A(max(d3, d4) + _g(rng, 1, 2), "self", "assert", value=W, vf=d4)
        v = _g(rng, d2, d4 - 1)
        gone = [[d0, X], [d4, W]]
        kept = [[d0, X], [d2, shown], [d4, W]]
        qs = [{"op": "current"}, {"op": "valid_at", "v": v}]
        if fam == "P5":
            qs.append({"op": "believed_at", "t": _g(rng, last, d3 - 1)})
        qs.append({"op": "why_changed", "v": v, "k1": _g(rng, last, d3 - 1)})
        out.update(crit=c, b_change={"source": b_src}, questions=qs,
                   truth={"A": gone if fam == "P5" else kept, "B": kept if fam == "P5" else gone})
        if fam == "P5":
            out["iv"]["remove_retraction"] = {"remove": c}

    elif fam == "P7":
        Q, Q2 = (T1, T2) if rng.below(2) else (T2, T1)
        H = (H1, H2)[rng.below(2)]
        d0 = _g(rng, 1, 2); d2 = d0 + _g(rng, 2, 4); d1 = d2 + _g(rng, 0, 2)
        A(d0, "self", "assert", value=X, vf=d0)
        A(d1, Q, "assert", value=Y, vf=d2)
        d3 = d1 + _g(rng, 1, 3)
        c = A(d3, Q2, "assert", value=Z, vf=d2)
        truth = [[d0, X], [d2, Y]]
        if idx % 2 == 0:   # fixed rule: even pairs - conflict on the newest version, ask current
            q0 = {"op": "current"}
        else:              # odd pairs - a later state change, ask valid_at inside the conflict
            d4 = d2 + _g(rng, 3, 5)
            A(max(d3, d4) + _g(rng, 1, 2), "self", "assert", value=W, vf=d4)
            q0 = {"op": "valid_at", "v": _g(rng, d2, d4 - 1)}
            truth = truth + [[d4, W]]
        out.update(crit=c, b_change={"source": H}, questions=[q0, {"op": "conflicts"}, {"op": "history"}],
                   truth={"A": truth, "B": truth})
        out["iv"]["swap_ranks"] = {"swap_with": Q}

    elif fam == "P8":
        Q, Q2 = (T1, T2) if rng.below(2) else (T2, T1)
        H = (H1, H2)[rng.below(2)]
        d0 = _g(rng, 1, 2); d2 = d0 + _g(rng, 2, 4)
        A(d0, "self", "assert", value=X, vf=d0)
        e1 = d2 + _g(rng, 0, 1); r1 = A(e1, Q, "assert", value=Y, vf=d2)
        e2 = e1 + _g(rng, 0, 1); A(e2, Q2, "assert", value=Z, vf=d2)
        last = e2
        variant = idx % 3
        if variant == 2:
            last = e2 + _g(rng, 0, 1)
            rl = A(last, H, "assert", value=U, vf=d2)
        d4 = last + _g(rng, 1, 3)
        if variant == 0:
            c = A(d4, "self", "assert", value=V, vf=d2)
        else:
            c = A(d4, "self", "correct", value=V, target=r1 if variant == 1 else rl)
        out.update(crit=c, b_change={"source": H},
                   questions=[{"op": "current"}, {"op": "conflicts"},
                              {"op": "why_changed", "v": _g(rng, d2, d4), "k1": _g(rng, last, d4 - 1)}],
                   truth={"A": [[d0, X], [d2, V]], "B": [[d0, X], [d2, V]]})
        out["iv"]["remove_conflict_resolver"] = {"remove": c}
        out["iv"]["swap_ranks"] = {"swap_with": Q}

    elif fam == "P9":
        n = _g(rng, 5, 8)
        vals = pool[:n]
        spare = [p for p in pool if p not in vals]
        vfs = [_g(rng, 1, 2)]
        for _ in range(n - 1):
            vfs.append(vfs[-1] + _g(rng, 3, 5))
        i = _g(rng, 1, n - 3)                      # 0-based: not first, previous or current
        syms = []
        for j in range(n):
            syms.append(A(vfs[j] + _g(rng, 0, 1), ("self", T1, T2)[rng.below(3)], "assert",
                          value=vals[j], vf=vfs[j]))
        dy = _g(rng, vfs[i] + 1, vfs[i + 1] - 1)
        content = f"met {voc['people'][1]} at {voc['places'][-1]}"
        anchor = b.add(dy + _g(rng, 0, 1), "self", "assert", ANCHOR_PREFIX + content,
                       ANCHOR_ATTRIBUTE, value=dy, vf=0)
        other = [j for j in range(n - 1) if j != i]
        j = other[rng.below(len(other))]
        moved = _g(rng, vfs[j] + 1, vfs[j + 1] - 1)
        truth_a = [[vfs[k], vals[k]] for k in range(n)]
        truth_b = [[vfs[k], spare[0] if k == i else vals[k]] for k in range(n)]
        out.update(crit=syms[i], b_change={"value": spare[0]}, anchor=content, anchor_day=dy,
                   questions=[{"op": "before", "anchor": content}, {"op": "current"}],
                   truth={"A": truth_a, "B": truth_b}, p9={"n": n, "i": i})
        out["iv"]["move_anchor"] = {"set_value": [anchor, moved]}
        out["iv"]["remove_anchor"] = {"remove": anchor}
        out["iv"]["remove_obs_before_anchor"] = {"remove": syms[i]}
    else:
        raise ValueError(fam)
    out["specs"] = b.specs
    out["last_day"] = max(s["day"] for s in b.specs)
    return out


def distractors(rng: HashRng, voc: dict, n: int, start_day: int, fact, anchor) -> list[dict]:
    """n irrelevant reports (same vocabulary, other facts), PER_DAY per day from
    start_day on: asserts (some late), corrections and retractions of earlier irrelevant
    asserts, repeats (same origin, same value) and other anchor events."""
    subject, attribute = fact
    facts = [(o, a) for o in voc["objects"][1:6] for a in ("location", "holder")]
    facts.append((subject, "holder" if attribute == "location" else "location"))
    sources = list(voc["ranks"])
    specs: list[dict] = []
    asserts: list[int] = []
    for k in range(n):
        day = start_day + k // PER_DAY
        roll = rng.below(100)
        if roll < 70 or len(asserts) < 3:
            s, a = facts[rng.below(len(facts))]
            vals = voc["values"][a]
            specs.append({"day": day, "source": sources[rng.below(5)], "kind": "assert",
                          "subject": s, "attribute": a, "value": vals[rng.below(len(vals))],
                          "vf": max(1, day - rng.below(7)), "target": None, "repeat_of": None})
            asserts.append(len(specs) - 1)
        elif roll < 80:
            t = asserts[rng.below(len(asserts))]
            vals = voc["values"][specs[t]["attribute"]]
            specs.append({"day": day, "source": sources[rng.below(5)], "kind": "correct",
                          "subject": specs[t]["subject"], "attribute": specs[t]["attribute"],
                          "value": vals[rng.below(len(vals))], "vf": None, "target": t,
                          "repeat_of": None})
        elif roll < 88:
            t = asserts[rng.below(len(asserts))]
            src = specs[t]["source"] if rng.below(2) else sources[rng.below(5)]
            specs.append({"day": day, "source": src, "kind": "retract",
                          "subject": specs[t]["subject"], "attribute": specs[t]["attribute"],
                          "value": None, "vf": None, "target": t, "repeat_of": None})
        elif roll < 95:
            t = asserts[rng.below(len(asserts))]
            specs.append({**specs[t], "day": day, "source": sources[rng.below(5)],
                          "repeat_of": t})
        else:
            while True:
                content = (f"met {voc['people'][2 + rng.below(len(voc['people']) - 2)]} at "
                           f"{voc['places'][rng.below(len(voc['places']))]}")
                if content != anchor:
                    break
            specs.append({"day": day, "source": sources[rng.below(5)], "kind": "assert",
                          "subject": ANCHOR_PREFIX + content, "attribute": ANCHOR_ATTRIBUTE,
                          "value": max(1, day - rng.below(5)), "vf": 0, "target": None,
                          "repeat_of": None})
    return specs


# ------------------------------------------------------------------ pairs and worlds
def _with_offset(specs, offset):
    out = []
    for s in specs:
        s = dict(s)
        for f in ("target", "repeat_of"):
            if s[f] is not None:
                s[f] += offset
        out.append(s)
    return out


def generate_split(split: str) -> list[dict]:
    return list(iter_pairs(split))


def iter_pairs(split: str):
    """All pairs of a split, one at a time: per family PAIRS[split] pairs, each with
    worlds A and B at the four delays."""
    seed = SEEDS[split]
    for fam in FAMILIES:
        for idx in range(PAIRS[split]):
            rng = HashRng(f"{seed}|{fam}|{idx}")
            voc = vocabulary(rng)
            fam_rng = HashRng(f"{seed}|{fam}|{idx}|family")
            spec = _family(fam, fam_rng, voc, idx)
            pair = {"pair": f"{split}-{fam}-{idx:02d}", "family": fam, "index": idx,
                    "fact": spec["fact"], "anchor": spec["anchor"], "anchor_day": spec["anchor_day"],
                    "ranks": voc["ranks"], "truth": spec["truth"], "instances": [],
                    "q_ops": [q["op"] for q in spec["questions"]], "p9": spec.get("p9")}
            for delay in DELAYS:
                d_rng = HashRng(f"{seed}|{fam}|{idx}|delay|{delay}")
                start = spec["last_day"] + 1
                extra = distractors(d_rng, voc, delay, start, tuple(spec["fact"]), spec["anchor"])
                base = list(spec["specs"]) + _with_offset(extra, len(spec["specs"]))
                now = (start + (delay - 1) // PER_DAY + 1) if delay else start
                inst = {"delay": delay, "now": now}
                for world in ("A", "B"):
                    specs = [dict(s) for s in base]
                    if world == "B":
                        specs[spec["crit"]].update(spec["b_change"])
                    reports, ids = finalize(specs, voc["ranks"])
                    qs = []
                    for n, q in enumerate(spec["questions"]):
                        q = dict(q, qid=f"{pair['pair']}-{world}-{delay}-q{n}", now=now,
                                 subject=spec["fact"][0], attribute=spec["fact"][1])
                        if q["op"] == "why_changed":
                            q["k2"] = now
                        qs.append(q)
                    inst[world] = {"reports": reports, "questions": qs}
                    if world == "A":
                        inst["crit_id"] = ids[spec["crit"]]
                        inst["iv"] = _resolve_iv(spec["iv"], ids)
                        inst["n_relevant"] = len(spec["specs"])
                        inst["distractor_ids"] = sorted(ids[len(spec["specs"]) + k]
                                                        for k in range(len(extra)))
                pair["instances"].append(inst)
            yield pair


def _resolve_iv(iv, ids):
    out = {}
    for name, op in iv.items():
        op = dict(op)
        if "remove" in op:
            op["remove"] = ids[op["remove"]]
        if "set_value" in op:
            op["set_value"] = [ids[op["set_value"][0]], op["set_value"][1]]
        out[name] = op
    return out


# ------------------------------------------------------------------ interventions
def remove_with_cascade(reports: list[dict], rid: str) -> tuple[list[dict], list[str]]:
    """Remove a report and, transitively, every report that refers to a removed one."""
    removed = {rid}
    changed = True
    while changed:
        changed = False
        for r in reports:
            if r["target_report_id"] in removed and r["report_id"] not in removed:
                removed.add(r["report_id"])
                changed = True
    return [dict(r) for r in reports if r["report_id"] not in removed], sorted(removed)


def swap_ranks(reports, ranks, s1, s2):
    new = dict(ranks)
    new[s1], new[s2] = ranks[s2], ranks[s1]
    return [dict(r, rank=new[r["source"]]) for r in reports], new


def counterfactual(pair: dict, inst: dict, kind: str) -> dict | None:
    """The counterfactual world of intervention `kind` on world A of one instance:
    {"reports", "ranks", "removed", "note"} or None if it does not apply."""
    reports = [dict(r) for r in inst["A"]["reports"]]
    ranks = dict(pair["ranks"])
    if kind == "irrelevant_control":
        if pair["index"] % 2 == 1 and inst["distractor_ids"]:
            pick = inst["distractor_ids"][pair["index"] % len(inst["distractor_ids"])]
            reports, removed = remove_with_cascade(reports, pick)
            return {"reports": reports, "ranks": ranks, "removed": removed, "note": "remove irrelevant"}
        rid = f"r{len(reports) + 1:05d}"
        day = inst["now"] - 1
        reports.append({"report_id": rid, "report_day": day, "source": "self", "rank": ranks["self"],
                        "origin": "o-" + rid, "subject": "the added parcel", "attribute": "location",
                        "kind": "assert", "value": "nowhere", "valid_from": day,
                        "target_report_id": None})
        return {"reports": reports, "ranks": ranks, "removed": [], "note": f"add irrelevant {rid}"}
    op = inst["iv"].get(kind)
    if op is None:
        return None
    if "remove" in op:
        reports, removed = remove_with_cascade(reports, op["remove"])
        return {"reports": reports, "ranks": ranks, "removed": removed, "note": f"remove {op['remove']}"}
    if "set_value" in op:
        rid, value = op["set_value"]
        reports = [dict(r, value=value) if r["report_id"] == rid else r for r in reports]
        return {"reports": reports, "ranks": ranks, "removed": [], "note": f"{rid} value -> {value}"}
    if "swap_with" in op:
        crit = next(r for r in reports if r["report_id"] == inst["crit_id"])
        s1, s2 = crit["source"], op["swap_with"]
        if ranks[s1] == ranks[s2]:
            s2 = "self" if s1 != "self" else s2
        if s1 == s2 or ranks[s1] == ranks[s2]:
            return None
        reports, ranks = swap_ranks(reports, ranks, s1, s2)
        return {"reports": reports, "ranks": ranks, "removed": [], "note": f"swap ranks {s1}<->{s2}"}
    raise ValueError(op)


# ------------------------------------------------------------------ audit
def _effective_fields(reports):
    """(subject, attribute, valid_from, value) a claim-creating report would carry,
    following correction chains for missing fields (static, independent of ranks)."""
    by_id = {r["report_id"]: r for r in reports}
    out = {}
    for r in reports:
        if r["kind"] == "retract":
            continue
        vf, val, cur = r["valid_from"], r["value"], r
        while (vf is None or val is None) and cur["kind"] == "correct":
            cur = by_id.get(cur["target_report_id"])
            if cur is None or cur["kind"] == "retract":
                break
            vf = cur["valid_from"] if vf is None else vf
            val = cur["value"] if val is None else val
        out[r["report_id"]] = (r["subject"], r["attribute"], vf, val)
    return out


def audit_world(reports: list[dict], ranks: dict, anchor: str | None, fact,
                original: bool) -> list[str]:
    """General generator audit (section 3); returns the list of violations."""
    bad = []
    seen = set()
    for r in reports:
        try:
            check_report(r)
        except ValueError as e:
            bad.append(str(e))
        if r["report_id"] in seen:
            bad.append(f"duplicate id {r['report_id']}")
        seen.add(r["report_id"])
        if ranks.get(r["source"]) != r["rank"]:
            bad.append(f"{r['report_id']}: rank does not match the world's rank table")
    keys = [order_key(r) for r in reports]
    if keys != sorted(keys):
        bad.append("reports not in total order")
    pos = {r["report_id"]: n for n, r in enumerate(reports)}
    by_id = {r["report_id"]: r for r in reports}
    table: list = []
    for n, r in enumerate(reports):
        t = r["target_report_id"]
        if t is not None:
            if t not in by_id:
                bad.append(f"{r['report_id']}: dangling reference {t}")
            elif pos[t] >= n:
                bad.append(f"{r['report_id']}: target {t} is not earlier")
            elif by_id[t]["kind"] == "retract":
                bad.append(f"{r['report_id']}: target {t} is a retract report")
            elif (by_id[t]["subject"], by_id[t]["attribute"]) != (r["subject"], r["attribute"]):
                bad.append(f"{r['report_id']}: target {t} is about another fact")
            elif original and by_id[t]["kind"] == "correct" \
                    and not any(row["id"] == t for row in table):
                bad.append(f"{r['report_id']}: target {t} never created a claim (original world)")
        if r["subject"].startswith(ANCHOR_PREFIX):
            if r["kind"] == "assert" and r["valid_from"] != 0:
                bad.append(f"{r['report_id']}: anchor report needs valid_from 0")
            if r["kind"] == "correct" and r["valid_from"] is not None:
                bad.append(f"{r['report_id']}: anchor correction may not set valid_from")
        _step(table, r)
    eff = _effective_fields(reports)
    groups: dict = {}
    for rid, (s, a, vf, val) in eff.items():
        r = by_id[rid]
        groups.setdefault((s, a, vf, r["rank"], r["origin"]), set()).add(val)
    for key, vals in groups.items():
        if len(vals) > 1:
            bad.append(f"equal-rank same-origin claims with different values {key}")
    if anchor is not None:
        days = {val for rid, (s, a, vf, val) in eff.items()
                if s == ANCHOR_PREFIX + anchor and a == ANCHOR_ATTRIBUTE}
        vfs = {vf for rid, (s, a, vf, val) in eff.items() if (s, a) == tuple(fact)}
        if days & vfs:
            bad.append(f"a change of the fact lies on an anchor day {sorted(days & vfs)}")
    return bad


def world_digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
