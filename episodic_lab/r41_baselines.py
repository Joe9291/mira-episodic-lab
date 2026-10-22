"""Round 4.1 baseline S5, the naive updater (docs/ROUND_4_1.md section 4).

On the report prefix it receives, S5 applies EVERY correction and retraction to its
target regardless of rank and source; the latest standing claim in the total order wins
(rank, valid_from and conflicts ignored). Its exported state - the standing claims (id,
value) in total order - is exactly what its answer uses. The other baselines are those of
round 4.0 (r40_baselines.py), unchanged.
"""
from __future__ import annotations


def _standing(reports, fact, now):
    claims = {}                                   # report id -> value, in insertion order
    for r in sorted(reports, key=lambda r: (r["report_day"], r["report_id"])):
        if r["report_day"] > now or (r["subject"], r["attribute"]) != tuple(fact):
            continue
        if r["kind"] == "assert":
            claims[r["report_id"]] = r["value"]
            continue
        t = r["target_report_id"]
        if t not in claims:
            continue                              # no standing claim to act on
        old = claims.pop(t)
        if r["kind"] == "correct":
            claims[r["report_id"]] = old if r["value"] is None else r["value"]
    return list(claims.items())


def s5_state(reports, q, ctx=None):
    return tuple(_standing(reports, (q["subject"], q["attribute"]), q["now"]))


def s5(reports, q, ctx=None):
    if q["op"] != "current":
        raise ValueError("S5 is defined for current questions only (round 4.1)")
    st = _standing(reports, (q["subject"], q["attribute"]), q["now"])
    if not st:
        return {"status": "unknown", "reason": "no_version"}
    rid, value = st[-1]
    return {"status": "value", "value": value, "ids": [rid]}
