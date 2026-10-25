"""Round 4.3 worlds, cuts and questions (docs/ROUND_4_3.md section 4) - model-free.

The worlds are those of the round 4.0 generator (P1-P9) and the round 4.1 generator
(T1-T5), rebuilt here with the round 4.3 seeds by the generators' own functions (their
files are not changed). Per world: the family's questions (unchanged) plus the
consolidation questions about the asked fact, and the cut grid.
"""
from __future__ import annotations

from . import r40_world as W40
from . import r41_world as W41
from .rng import HashRng

GENERATOR_VERSION = "r43.g1"
FAMILIES = W40.FAMILIES + W41.FAMILIES
DELAYS = W40.DELAYS
PAIRS = {"dev": 10, "holdout": 40}
SEEDS = {"dev": "r43-dev-1", "holdout": "r43-holdout-1"}


def _instances(seed, fam, idx, spec, voc, start, fact, anchor):
    out = []
    for delay in DELAYS:
        d_rng = HashRng(f"{seed}|{fam}|{idx}|delay|{delay}")
        extra = W40.distractors(d_rng, voc, delay, start, tuple(fact), anchor)
        base = list(spec["specs"]) + W40._with_offset(extra, len(spec["specs"]))
        now = (start + (delay - 1) // W40.PER_DAY + 1) if delay else start
        inst = {"delay": delay, "now": now, "n_relevant": len(spec["specs"])}
        for world in ("A", "B"):
            specs = [dict(s) for s in base]
            if world == "B":
                specs[spec["crit"]].update(spec["b_change"])
            reports, ids = W40.finalize(specs, voc["ranks"])
            relevant = {ids[i] for i in range(len(spec["specs"]))}
            inst[world] = {"reports": reports, "relevant_ids": sorted(relevant)}
        out.append(inst)
    return out


def iter_pairs(split: str):
    seed = SEEDS[split]
    for fam in FAMILIES:
        for idx in range(PAIRS[split]):
            voc = W40.vocabulary(HashRng(f"{seed}|{fam}|{idx}"))
            fam_rng = HashRng(f"{seed}|{fam}|{idx}|family")
            if fam.startswith("P"):
                spec = W40._family(fam, fam_rng, voc, idx)
                start, anchor, fam_qs = spec["last_day"] + 1, spec["anchor"], spec["questions"]
            else:
                spec = W41._family(fam, fam_rng, voc, idx)
                start, anchor, fam_qs = spec["d3"] + 1, None, [{"op": "current"}]
            pair = {"pair": f"{split}-{fam}-{idx:02d}", "family": fam, "index": idx, "fact": spec["fact"],
                    "anchor": anchor, "ranks": voc["ranks"], "family_questions": fam_qs,
                    "instances": _instances(seed, fam, idx, spec, voc, start, spec["fact"], anchor)}
            for inst in pair["instances"]:
                for world in ("A", "B"):
                    w = inst[world]
                    w["cuts"] = cuts(w["reports"], w["relevant_ids"], start, inst["now"])
                    w["questions"] = questions(pair, inst, world)
            yield pair


def cuts(reports, relevant_ids, tail_start, now):
    """0 (genesis), every day from the first to the last relevant report day + 1, the days
    at 1/4, 1/2, 3/4 of the irrelevant tail, and now. A cut c covers ALL reports with
    report_day <= c."""
    rel_days = [r["report_day"] for r in reports if r["report_id"] in set(relevant_ids)]
    out = {0, now}
    out.update(range(min(rel_days), max(rel_days) + 2))
    if now > tail_start:
        out.update(tail_start + (now - tail_start) * q // 4 for q in (1, 2, 3))
    return sorted(c for c in out if c <= now)


def questions(pair, inst, world):
    """The family's questions plus the consolidation questions about the asked fact."""
    w = inst[world]
    now = inst["now"]
    subj, attr = pair["fact"]
    rel = [r for r in w["reports"] if r["report_id"] in set(w["relevant_ids"])
           and (r["subject"], r["attribute"]) == (subj, attr)]
    vfs = sorted({r["valid_from"] for r in rel if r["valid_from"] is not None})
    days = sorted({r["report_day"] for r in rel})
    qs = [dict(q, role="family") for q in pair["family_questions"]]
    qs += [{"op": op, "role": "consolidation"} for op in ("current", "history", "conflicts", "digest")]
    qs += [{"op": "valid_at", "v": v, "role": "consolidation"} for v in vfs]
    qs += [{"op": "believed_at", "t": t, "role": "consolidation"} for t in days]
    qs += [{"op": "digest_at", "t": t, "role": "consolidation"} for t in days]
    qs += [{"op": "why_changed", "v": v, "k1": t, "role": "consolidation"} for v in vfs for t in days if t < now]
    out = []
    for n, q in enumerate(qs):
        q = dict(q, qid=f"{pair['pair']}-{world}-{inst['delay']}-q{n}", now=now, subject=subj, attribute=attr)
        if q["op"] == "why_changed":
            q["k2"] = now
        out.append(q)
    return out


def needed_time(q) -> int:
    """The smallest knowledge time a question needs."""
    return {"believed_at": lambda: q["t"], "digest_at": lambda: q["t"],
            "why_changed": lambda: q["k1"]}.get(q["op"], lambda: q["now"])()


def ids_monotonic(reports) -> bool:
    """Input contract of round 4.3: report ids strictly increase in total order."""
    ids = [int(r["report_id"][1:]) for r in reports]
    return all(a < b for a, b in zip(ids, ids[1:]))


def question_times(qs) -> set:
    """Every knowledge time an operator of these questions reads."""
    ts = set()
    for q in qs:
        ts.add(needed_time(q))
        ts.add(q["now"])
        if q["op"] == "why_changed":
            ts.add(q["k2"])
    return ts


def instance_counts(w) -> dict:
    """The model-free expected numbers of one world-delay instance (bound in
    config/round43_counts.json): cuts, questions, Mode T evaluations, full-state comparisons
    (checkpoints, Mode A times, Mode T times) and digest partition checks (Mode A, Mode T)."""
    qs, cuts = w["questions"], w["cuts"]
    times = question_times(qs)
    dig = [q for q in qs if q["op"] in ("digest", "digest_at")]
    return {"cuts": len(cuts), "questions": len(qs), "mode_t_evaluations": len(cuts) * len(qs),
            "state_checks_cut": len(cuts), "state_checks_mode_a": len(times),
            "state_checks_mode_t": sum(1 for c in cuts for k in times if k >= c),
            "digest_checks_mode_a": len(dig),
            "digest_checks_mode_t": sum(1 for c in cuts for q in dig if needed_time(q) >= c)}


COUNT_KEYS = ("cuts", "questions", "mode_t_evaluations", "state_checks_cut", "state_checks_mode_a",
              "state_checks_mode_t", "digest_checks_mode_a", "digest_checks_mode_t")


def family_counts(split) -> dict:
    out = {}
    for pair in iter_pairs(split):
        f = out.setdefault(pair["family"], dict({k: 0 for k in COUNT_KEYS}, pairs=0, instances=0, by_operator={}))
        f["pairs"] += 1
        for inst in pair["instances"]:
            for world in ("A", "B"):
                f["instances"] += 1
                for k, v in instance_counts(inst[world]).items():
                    f[k] += v
                for q in inst[world]["questions"]:
                    f["by_operator"][q["op"]] = f["by_operator"].get(q["op"], 0) + 1
    for f in out.values():
        f["by_operator"] = dict(sorted(f["by_operator"].items()))
    return out
