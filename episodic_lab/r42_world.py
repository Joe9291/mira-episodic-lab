"""Round 4.2 worlds (docs/ROUND_4_2.md section 4): the round 4.0 families P1-P9 with
their own seeds, delays 0 and 20, every report rendered as a note (r42_wordings).

Phase B needs references that can be resolved from (source, day, subject, attribute):
the irrelevant reports of a delay are drawn again (deterministically, attempt k = 0, 1,
...) until every correction, retraction and repeat in both worlds of the pair has exactly
one earlier report with that key. The relevant reports of the families never need it
(checked by the same rule).
"""
from __future__ import annotations

from . import r40_world as W40
from . import r42_wordings as WD
from .rng import HashRng

GENERATOR_VERSION = "r42.g1"
FAMILIES = W40.FAMILIES
DELAYS = (0, 20)
PAIRS = {"dev": 10, "cal": 30, "audit": 5, "holdout": 40}
SEEDS = {"dev": "r42-dev-1", "cal": "r42-cal-1", "audit": "r42-audit-1", "holdout": "r42-holdout-1"}
MAX_ATTEMPTS = 50


def reference_of(report: dict, by_id: dict):
    t, _ = WD.note_type(report, by_id)
    if t in ("correction", "retraction"):
        return by_id[report["target_report_id"]]
    if t == "repeat":
        return by_id[report["origin"][2:]]
    return None


def ambiguous_references(reports: list[dict]) -> list[str]:
    by_id = {r["report_id"]: r for r in reports}
    bad = []
    for pos, r in enumerate(reports):
        ref = reference_of(r, by_id)
        if ref is None:
            continue
        key = (ref["source"], ref["report_day"], ref["subject"], ref["attribute"])
        hits = [x for x in reports[:pos] if (x["source"], x["report_day"], x["subject"], x["attribute"]) == key]
        if len(hits) != 1:
            bad.append(r["report_id"])
    return bad


def notes_of(reports: list[dict], split: str, pair_seed: str) -> list[dict]:
    by_id = {r["report_id"]: r for r in reports}
    out = []
    for pos, r in enumerate(reports):
        frame = WD.choose_frame(split, pair_seed, pos)
        t, sub = WD.note_type(r, by_id)
        out.append({"note_id": r["report_id"], "header": WD.header(r), "author": r["source"],
                    "report_day": r["report_day"], "text": WD.render(r, by_id, frame, f"{pair_seed}|{pos}"),
                    "frame": frame, "gold_type": t, "gold_subtype": sub})
    return out


def iter_pairs(split: str):
    seed = SEEDS[split]
    for fam in FAMILIES:
        for idx in range(PAIRS[split]):
            pair_seed = f"{seed}|{fam}|{idx}"
            voc = W40.vocabulary(HashRng(pair_seed))
            spec = W40._family(fam, HashRng(f"{pair_seed}|family"), voc, idx)
            pair = {"pair": f"{split}-{fam}-{idx:02d}", "family": fam, "index": idx, "fact": spec["fact"],
                    "anchor": spec["anchor"], "anchor_day": spec["anchor_day"], "ranks": voc["ranks"],
                    "truth": spec["truth"], "sources": sorted(voc["ranks"]), "instances": []}
            for delay in DELAYS:
                start = spec["last_day"] + 1
                for attempt in range(MAX_ATTEMPTS):
                    extra = W40.distractors(HashRng(f"{pair_seed}|delay|{delay}|{attempt}"), voc, delay, start,
                                            tuple(spec["fact"]), spec["anchor"])
                    base = list(spec["specs"]) + W40._with_offset(extra, len(spec["specs"]))
                    worlds = {}
                    for world in ("A", "B"):
                        specs = [dict(s) for s in base]
                        if world == "B":
                            specs[spec["crit"]].update(spec["b_change"])
                        worlds[world] = W40.finalize(specs, voc["ranks"])
                    if not any(ambiguous_references(worlds[w][0]) for w in worlds):
                        break
                else:
                    raise RuntimeError(f"{pair['pair']} d{delay}: no unambiguous irrelevant set")
                now = (start + (delay - 1) // W40.PER_DAY + 1) if delay else start
                inst = {"delay": delay, "now": now, "attempt": attempt}
                for world in ("A", "B"):
                    reports, ids = worlds[world]
                    qs = []
                    for n, q in enumerate(spec["questions"]):
                        q = dict(q, qid=f"{pair['pair']}-{world}-{delay}-q{n}", now=now,
                                 subject=spec["fact"][0], attribute=spec["fact"][1])
                        if q["op"] == "why_changed":
                            q["k2"] = now
                        qs.append(q)
                    inst[world] = {"reports": reports, "questions": qs,
                                   "notes": notes_of(reports, split, pair_seed)}
                    if world == "A":
                        inst["crit_id"] = ids[spec["crit"]]
                        inst["n_relevant"] = len(spec["specs"])
                pair["instances"].append(inst)
            yield pair


def generate_split(split):
    return list(iter_pairs(split))
