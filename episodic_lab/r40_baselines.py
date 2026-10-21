"""Round 4.0 baselines S0-S4 (docs/ROUND_4_0.md section 3).

Every baseline gives an allowed output for every operator. Each also exposes the state
it can see for a question (`state`), which the audit compares between worlds A and B of
a pair (B-indistinguishable pairs). S3 and S4 are built from R's policy answers at
question time (R's history of the fact and of the anchor at `now`), truncated to what
the baseline may keep.
"""
from __future__ import annotations

from .r40_schema import ANCHOR_ATTRIBUTE, ANCHOR_PREFIX

SYSTEMS = ("S0", "S1", "S2", "S3", "S4")
VALUE_OPS = ("current", "valid_at", "believed_at", "before")


def _unknown(reason="no_version"):
    return {"status": "unknown", "reason": reason}


def _from_version(ver):
    if ver is None:
        return _unknown()
    if ver["status"] == "value":
        return {"status": "value", "value": ver["value"], "ids": list(ver["ids"])}
    return {"status": "conflict", "values": list(ver["values"]), "ids": list(ver["ids"])}


def _asserts(reports, fact, k):
    return [r for r in reports if r["kind"] == "assert" and r["report_day"] <= k
            and (r["subject"], r["attribute"]) == tuple(fact)]


def _fact(q):
    return (q["subject"], q["attribute"])


def _anchor_fact(q):
    return (ANCHOR_PREFIX + q["anchor"], ANCHOR_ATTRIBUTE)


# ----------------------------------------------------------------------- S0
def s0(reports, q, ctx):
    op = q["op"]
    if op == "before":
        return _unknown("anchor_not_found")
    if op in VALUE_OPS:
        return _unknown()
    if op == "why_changed":
        return "unknown"
    return []


# ----------------------------------------------------------------------- S1
def s1_state(reports, q, ctx):
    a = _asserts(reports, _fact(q), q["now"])
    return a[-1]["value"] if a else None


def s1(reports, q, ctx):
    val = s1_state(reports, q, ctx)
    op = q["op"]
    if op in VALUE_OPS:
        return _unknown() if val is None else {"status": "value", "value": val, "ids": []}
    if op == "why_changed":
        return "unchanged"
    if op == "conflicts":
        return []
    if val is None:
        return []
    return [{"valid_from": None, "valid_to": None, "status": "value", "value": val, "ids": []}]


# ----------------------------------------------------------------------- S2
def s2_state(reports, q, ctx):
    rows = tuple((r["report_day"], r["report_id"], r["valid_from"], r["value"])
                 for r in _asserts(reports, _fact(q), q["now"]))
    anchor = ()
    if q["op"] == "before":
        anchor = tuple((r["report_day"], r["report_id"], r["value"])
                       for r in _asserts(reports, _anchor_fact(q), q["now"]))
    return (rows, anchor)


def _s2_value(rows, v, k):
    hit = [r for r in rows if r["report_day"] <= k and r["valid_from"] <= v]
    if not hit:
        return _unknown()
    r = hit[-1]                      # the latest in the total order (report_day, report_id)
    return {"status": "value", "value": r["value"], "ids": [r["report_id"]]}


def s2(reports, q, ctx):
    op, now = q["op"], q["now"]
    rows = _asserts(reports, _fact(q), now)
    if op == "current":
        return _s2_value(rows, now, now)
    if op == "valid_at":
        return _s2_value(rows, q["v"], now)
    if op == "believed_at":
        return _s2_value(rows, q["t"], q["t"])
    if op == "before":
        anchors = _asserts(reports, _anchor_fact(q), now)
        if not anchors:
            return _unknown("anchor_not_found")
        ans = _s2_value(rows, anchors[-1]["value"] - 1, now)
        return _unknown("no_version_before") if ans["status"] == "unknown" else ans
    if op == "why_changed":
        key = lambda a: (a["status"], a.get("value"))  # noqa: E731
        start = _s2_value(rows, q["v"], q["k1"])
        if key(start) == key(_s2_value(rows, q["v"], q["k2"])):
            return "unchanged"
        ids, last = [], key(start)
        for r in rows:
            if q["k1"] < r["report_day"] <= q["k2"]:
                cur = key(_s2_value([x for x in rows if (x["report_day"], x["report_id"])
                                     <= (r["report_day"], r["report_id"])], q["v"], q["k2"]))
                if cur != last:
                    ids.append(r["report_id"])
                    last = cur
        return ids
    if op == "conflicts":
        return []
    days = sorted({r["valid_from"] for r in rows})
    out = []
    for n, d in enumerate(days):
        r = [x for x in rows if x["valid_from"] == d][-1]
        out.append({"valid_from": d, "valid_to": days[n + 1] - 1 if n + 1 < len(days) else None,
                    "status": "value", "value": r["value"], "ids": [r["report_id"]]})
    return out


# ----------------------------------------------------------------------- S3
def _stored(hist):
    if len(hist) <= 2:
        return [dict(h) for h in hist]
    return [dict(hist[0]), dict(hist[-2]), dict(hist[-1])]


def s3_state(reports, q, ctx):
    stored = tuple(tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in h.items()
                                if k != "valid_to")) for h in _stored(ctx["hist"]))
    anchor = None
    if q["op"] == "before":
        ah = ctx["anchor_hist"]
        anchor = None if not ah else tuple(sorted(
            (k, tuple(v) if isinstance(v, list) else v) for k, v in ah[-1].items() if k != "valid_to"))
    return (stored, anchor)


def _s3_value(stored, v):
    found = None
    for h in stored:
        if h["valid_from"] <= v:
            found = h
    return _from_version(found)


def s3(reports, q, ctx):
    stored = _stored(ctx["hist"])
    op = q["op"]
    if op == "current":
        return _s3_value(stored, q["now"])
    if op == "valid_at":
        return _s3_value(stored, q["v"])
    if op == "believed_at":
        return _s3_value(stored, q["t"])
    if op == "before":
        ah = ctx["anchor_hist"]
        if not ah:
            return _unknown("anchor_not_found")
        if ah[-1]["status"] == "conflict":
            return _unknown("anchor_ambiguous")
        ans = _s3_value(stored, ah[-1]["value"] - 1)
        return _unknown("no_version_before") if ans["status"] == "unknown" else ans
    if op == "why_changed":
        return "unchanged"
    if op == "conflicts":
        return []
    out = []
    for n, h in enumerate(stored):
        h = dict(h)
        h["valid_to"] = stored[n + 1]["valid_from"] - 1 if n + 1 < len(stored) else None
        out.append(h)
    return out


# ----------------------------------------------------------------------- S4
def _current_version(ctx, now):
    found = None
    for h in ctx["hist"]:
        if h["valid_from"] <= now:
            found = h
    return found


def s4_state(reports, q, ctx):
    ver = _current_version(ctx, q["now"])
    return None if ver is None else tuple(sorted(
        (k, tuple(v) if isinstance(v, list) else v) for k, v in ver.items() if k != "valid_to"))


def s4(reports, q, ctx):
    ver = _current_version(ctx, q["now"])
    op = q["op"]
    if op in VALUE_OPS:
        return _from_version(ver)
    if op == "why_changed":
        return "unchanged"
    if op == "conflicts":
        if ver is None or ver["status"] != "conflict":
            return []
        return [{"valid_from": ver["valid_from"], "values": list(ver["values"]), "ids": list(ver["ids"])}]
    if ver is None:
        return []
    return [dict(ver, valid_to=None)]


ANSWER = {"S0": s0, "S1": s1, "S2": s2, "S3": s3, "S4": s4}
STATE = {"S0": lambda reports, q, ctx: None, "S1": s1_state, "S2": s2_state, "S3": s3_state,
         "S4": s4_state}
