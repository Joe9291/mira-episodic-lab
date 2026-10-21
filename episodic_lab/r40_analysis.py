"""Round 4.0 scoring, measures, pair conditions and the pass rule (docs/ROUND_4_0.md
sections 4-5)."""
from __future__ import annotations

import math

VALUE_OPS = ("current", "valid_at", "believed_at", "before")
REQUIRED_CELLS = {"S1": ("P1", "P2", "P3", "P5", "P9"), "S2": ("P3", "P5", "P7", "P8"),
                  "S3": ("P9",), "S4": ("P1", "P2", "P3", "P5", "P9")}
MIN_PAIRS = {"holdout": 30, "dev": 8}          # dev: ceil(0.75 x 10)


def hit(op: str, gold, ans) -> bool:
    """Hit definitions (section 5): value operators by status and value / value set /
    reason (report ids do not count); why_changed, conflicts and history exactly."""
    if op in VALUE_OPS:
        if not isinstance(ans, dict) or ans.get("status") != gold["status"]:
            return False
        if gold["status"] == "value":
            return ans.get("value") == gold["value"]
        if gold["status"] == "conflict":
            return sorted(ans.get("values") or []) == sorted(gold["values"])
        return ans.get("reason") == gold["reason"]
    return ans == gold


def truth_at(truth, day):
    val = None
    for vf, v in truth:
        if vf <= day:
            val = v
    return val


def clean_and_agree(q, gold, aux, truth, anchor_day):
    """(clean report state?, agreement of the policy answer with the truth) for a value
    question; measurement only."""
    if q["op"] not in VALUE_OPS or aux is None:
        return None
    false = any(truth_at(truth, vf) != val for vf, val in aux["standing"])
    clean = not false and not aux["open_conflict"]
    if q["op"] == "before":
        clean = clean and all(val == anchor_day for _, val in aux.get("anchor_standing", [])) \
            and bool(aux.get("anchor_standing"))
        day = anchor_day - 1
    else:
        day = {"current": q["now"], "valid_at": q.get("v"), "believed_at": q.get("t")}[q["op"]]
    agree = gold.get("status") == "value" and gold.get("value") == truth_at(truth, day)
    return clean, agree


def outdated_values(past, gold):
    if gold["status"] == "value":
        now_vals = {gold["value"]}
    elif gold["status"] == "conflict":
        now_vals = set(gold["values"])
    else:
        now_vals = set()
    return sorted({a["value"] for a in past if a["status"] == "value" and a["value"] not in now_vals})


def pair_conditions(fam, gA, gB, qsA, crit_A, crit_B, histA, histB):
    """Phenomenon conditions on one instance of an original pair (R's gold). Returns a
    list of violations."""
    bad = []
    if not any(not hit(q["op"], gA[q["qid"]], gB[qb["qid"]]) for q, qb in zip(qsA, _twin(qsA, "B"))):
        bad.append("no question separates A and B")
    by_op = {q["op"]: q for q in qsA}

    def g(world, op):
        q = by_op[op]
        return (gA if world == "A" else gB)[q["qid"] if world == "A" else _bq(q["qid"])]
    cid = crit_A["report_id"]
    if fam == "P2" and not (crit_A["valid_from"] < crit_A["report_day"] == crit_B["valid_from"]):
        bad.append("P2: critical report is not late in A / timely in B")
    if fam in ("P3", "P5"):
        if g("A", "why_changed") != [cid] or g("B", "why_changed") != "unchanged":
            bad.append(f"{fam}: why_changed A must be [crit], B unchanged")
    if fam in ("P4", "P6"):
        if g("A", "why_changed") != "unchanged" or g("B", "why_changed") != [cid]:
            bad.append(f"{fam}: why_changed A must be unchanged, B [crit]")
    if fam == "P7":
        op = "current" if "current" in by_op else "valid_at"
        if g("A", op)["status"] != "conflict" or g("B", op)["status"] != "value":
            bad.append("P7: A must answer conflict, B a value")
    if fam == "P8":
        if g("A", "current")["status"] != "value" or g("B", "current")["status"] != "conflict" \
                or g("A", "conflicts") != [] or not g("B", "conflicts"):
            bad.append("P8: A resolved, B open conflict")
    if fam == "P1":
        if not (g("A", "valid_at")["status"] == g("B", "valid_at")["status"] == "value"):
            bad.append("P1: valid_at must be a value in both worlds")
    if fam == "P9":
        for world, hist in (("A", histA), ("B", histB)):
            ans = g(world, "before")
            held = {hist[0].get("value"), hist[-2].get("value"), hist[-1].get("value")} if len(hist) >= 3 else set()
            if len(hist) < 5 or ans["status"] != "value" or ans["value"] in held:
                bad.append(f"P9 {world}: before must be an intermediate value held by none of first/previous/current")
    return bad


def _bq(qid):
    parts = qid.split("-")
    parts[-3] = "B"
    return "-".join(parts)


def _twin(qs, world):
    return [dict(q, qid=_bq(q["qid"])) for q in qs]


def min_pairs(split):
    return MIN_PAIRS[split]


def ceil_frac(n, f):
    return math.ceil(n * f)
