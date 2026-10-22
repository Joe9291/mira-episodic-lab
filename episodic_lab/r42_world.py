"""Round 4.2 worlds (docs/ROUND_4_2.md section 4): the round 4.0 families P1-P9 with
their own seeds, delays 0 and 20, every report rendered as a note (r42_wordings).

Phase B needs references that can be resolved from (source, day, subject, attribute):
the irrelevant reports of a delay are drawn again (deterministically, attempt k = 0, 1,
...) until every correction, retraction and repeat in both worlds of the pair has exactly
one earlier report with that key, and no repeat is written by the speaker it repeats.
The relevant reports of the families never need it (checked by the same rules).
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


def self_repeats(reports: list[dict]) -> list[str]:
    """Repeats whose author is the original speaker - a person "repeating" their own
    statement has no sensible wording ("As Ilsen told me ..." in Ilsen's own note), so
    phase B worlds contain none."""
    by_id = {r["report_id"]: r for r in reports}
    return [r["report_id"] for r in reports if WD.note_type(r, by_id)[0] == "repeat"
            and by_id[r["origin"][2:]]["source"] == r["source"]]


def future_days(reports: list[dict]) -> list[str]:
    """Reports that name a day after their own report day (e.g. a correction "from day 9"
    written on day 8) - no sensible wording, so phase B worlds contain none."""
    return [r["report_id"] for r in reports
            if (r["valid_from"] is not None and r["valid_from"] > r["report_day"])
            or (r["subject"].startswith("event:") and isinstance(r["value"], int) and r["value"] > r["report_day"])]


def phase_b_vocabulary(rng_seed: str) -> dict:
    """The round 4.0 vocabulary, but the four sources get the four first names that no
    person of the world carries, so an author's name never appears inside a person's
    name ("note from Brenna" next to "Brenna Lunsey")."""
    voc = W40.vocabulary(HashRng(rng_seed))
    used = {p.split()[0] for p in voc["people"]}
    free = [n for n in sorted(W40.FIRST) if n not in used]
    old = voc["trusted"] + voc["hearsay"]
    new = dict(zip(old, free[:4]))
    voc = dict(voc, trusted=[new[n] for n in voc["trusted"]], hearsay=[new[n] for n in voc["hearsay"]])
    voc["ranks"] = {new.get(k, k): v for k, v in voc["ranks"].items()}
    return voc


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
            voc = phase_b_vocabulary(pair_seed)
            for fam_attempt in range(MAX_ATTEMPTS):
                spec = W40._family(fam, HashRng(f"{pair_seed}|family|{fam_attempt}"), voc, idx)
                probe, _ = W40.finalize([dict(s) for s in spec["specs"]], voc["ranks"])
                b_specs = [dict(s) for s in spec["specs"]]
                b_specs[spec["crit"]].update(spec["b_change"])
                probe_b, _ = W40.finalize(b_specs, voc["ranks"])
                if not future_days(probe) and not future_days(probe_b):
                    break
            else:
                raise RuntimeError(f"{fam} {idx}: no family draw without future days")
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
                    if not any(ambiguous_references(worlds[w][0]) or self_repeats(worlds[w][0])
                               or future_days(worlds[w][0]) for w in worlds):
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
