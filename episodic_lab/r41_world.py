"""Round 4.1 generator (docs/ROUND_4_1.md): the five families T1-T5 of the targeted
stale-answer test. Uses the round 4.0 building blocks (vocabulary, report specs, ids,
irrelevant reports) unchanged.

Every world: own observation X (valid from d0; missing in every second T2 pair), a
trusted report Q making Y current (valid from d1), in T3 a second trusted report Z for d1
(open conflict) and in its third variant a hearsay claim U for d1, then the critical
report c on day d3; all preparatory relevant reports lie on days <= d3 - 1; no relevant
report after c; the irrelevant reports of the delay follow c. In A, c changes the current
policy answer; in B it does not.
"""
from __future__ import annotations

from . import r40_world as W40
from .rng import HashRng

GENERATOR_VERSION = "r41.g1"
FAMILIES = ("T1", "T2", "T3", "T4", "T5")
DELAYS = W40.DELAYS
PAIRS = {"dev": 10, "holdout": 40}
SEEDS = {"dev": "r41-dev-1", "holdout": "r41-holdout-1"}
_g = W40._g


def _family(fam, rng, voc, idx):
    b = W40._Builder()
    attribute = ("location", "holder")[rng.below(2)]
    subject = voc["objects"][0]
    pool = rng.shuffled(voc["values"][attribute])
    X, Y, Z, V, U = pool[:5]
    T1, T2 = voc["trusted"]
    H1, H2 = voc["hearsay"]
    Q, Q2 = (T1, T2) if rng.below(2) else (T2, T1)
    H = (H1, H2)[rng.below(2)]
    A = lambda *a, **k: b.add(*a, subject=subject, attribute=attribute, **k)  # noqa: E731
    d0 = _g(rng, 1, 2)
    with_x = not (fam == "T2" and idx % 2 == 1)
    if with_x:
        A(d0, "self", "assert", value=X, vf=d0)
    d1 = d0 + _g(rng, 2, 4)
    last = d1 + _g(rng, 0, 1)
    r1 = A(last, Q, "assert", value=Y, vf=d1)
    variant = None
    if fam == "T3":
        last = last + _g(rng, 0, 1)
        A(last, Q2, "assert", value=Z, vf=d1)
        variant = idx % 3
        if variant == 2:
            last = last + _g(rng, 0, 1)
            rl = A(last, H, "assert", value=U, vf=d1)
    d3 = last + _g(rng, 1, 3)
    if fam == "T1":
        a_src = (Q, Q2, "self")[rng.below(3)]
        c = A(d3, a_src, "correct", value=Z, target=r1)
        b_src = H
    elif fam == "T2":
        c = A(d3, Q, "retract", target=r1)
        b_src = Q2
    elif fam == "T3":
        if variant == 0:
            c = A(d3, "self", "assert", value=V, vf=d1)
        else:
            c = A(d3, "self", "correct", value=V, target=r1 if variant == 1 else rl)
        b_src = H
    elif fam == "T4":
        c = A(d3, Q2, "assert", value=Z, vf=d1)
        b_src = H
    elif fam == "T5":
        c = A(d3, "self", "assert", value=Z, vf=d1)
        b_src = H
    else:
        raise ValueError(fam)
    return {"fact": [subject, attribute], "specs": b.specs, "crit": c, "b_change": {"source": b_src},
            "d3": d3, "variant": variant, "with_x": with_x}


def iter_pairs(split: str):
    """Pairs of a split, one at a time. Each pair has a BEFORE world per side (reports with
    day <= d3 - 1, question day d3 - 1) and an AFTER world per side and delay."""
    seed = SEEDS[split]
    for fam in FAMILIES:
        for idx in range(PAIRS[split]):
            voc = W40.vocabulary(HashRng(f"{seed}|{fam}|{idx}"))
            spec = _family(fam, HashRng(f"{seed}|{fam}|{idx}|family"), voc, idx)
            pid = f"{split}-{fam}-{idx:02d}"
            fact = spec["fact"]
            pair = {"pair": pid, "family": fam, "index": idx, "fact": fact, "anchor": None,
                    "ranks": voc["ranks"], "variant": spec["variant"], "with_x": spec["with_x"],
                    "d3": spec["d3"], "before": {}, "instances": []}
            for delay in DELAYS:
                d_rng = HashRng(f"{seed}|{fam}|{idx}|delay|{delay}")
                start = spec["d3"] + 1
                extra = W40.distractors(d_rng, voc, delay, start, tuple(fact), None)
                base = list(spec["specs"]) + W40._with_offset(extra, len(spec["specs"]))
                now = (start + (delay - 1) // W40.PER_DAY + 1) if delay else start
                inst = {"delay": delay, "now": now}
                for world in ("A", "B"):
                    specs = [dict(s) for s in base]
                    if world == "B":
                        specs[spec["crit"]].update(spec["b_change"])
                    reports, ids = W40.finalize(specs, voc["ranks"])
                    q = {"qid": f"{pid}-{world}-{delay}-after", "op": "current", "now": now,
                         "subject": fact[0], "attribute": fact[1]}
                    inst[world] = {"reports": reports, "questions": [q]}
                    if world == "A":
                        inst["crit_id"] = ids[spec["crit"]]
                        inst["n_relevant"] = len(spec["specs"])
                        inst["distractor_ids"] = sorted(ids[len(spec["specs"]) + k] for k in range(len(extra)))
                        inst["iv"] = {"remove_change": {"remove": ids[spec["crit"]]}}
                    if delay == 0:
                        prefix = [r for r in reports if r["report_day"] <= spec["d3"] - 1]
                        pair["before"][world] = {
                            "reports": prefix,
                            "questions": [{"qid": f"{pid}-{world}-before", "op": "current",
                                           "now": spec["d3"] - 1, "subject": fact[0], "attribute": fact[1]}]}
                pair["instances"].append(inst)
            yield pair


def generate_split(split):
    return list(iter_pairs(split))
