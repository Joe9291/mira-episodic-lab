"""Round 4.0 independent reference resolver R (docs/ROUND_4_0.md section 3).

Deliberately simple and written separately from M (r40_memory.py); the two share only
the report schema (r40_schema.py). R walks one world's reports ONCE in total order over
a flat table of claim rows (no per-fact index), takes the answers of every question at
the knowledge times it needs on the way, and follows why_changed questions report by
report between k1 and k2. It keeps no state copies, only the answers.
"""
from __future__ import annotations

from .r40_schema import ANCHOR_ATTRIBUTE, ANCHOR_PREFIX


def _rows_of(table, subject, attribute):
    return [row for row in table if row["alive"] and row["subject"] == subject
            and row["attribute"] == attribute]


def _decide(rows):
    """rows: alive claim rows of one fact with the same valid_from."""
    best = max(row["rank"] for row in rows)
    top = [row for row in rows if row["rank"] == best]
    values = sorted(set(row["value"] for row in top))
    ids = sorted(row["id"] for row in top)
    if len(values) == 1:
        return {"status": "value", "value": values[0], "ids": ids}
    return {"status": "conflict", "values": values, "ids": ids}


def _eval(table, subject, attribute, v):
    rows = [row for row in _rows_of(table, subject, attribute) if row["vf"] <= v]
    if not rows:
        return {"status": "unknown", "reason": "no_version"}
    last = max(row["vf"] for row in rows)
    return _decide([row for row in rows if row["vf"] == last])


def _history(table, subject, attribute):
    rows = _rows_of(table, subject, attribute)
    days = sorted(set(row["vf"] for row in rows))
    out = []
    for n, d in enumerate(days):
        item = {"valid_from": d, "valid_to": (days[n + 1] - 1) if n + 1 < len(days) else None}
        item.update(_decide([row for row in rows if row["vf"] == d]))
        out.append(item)
    return out


def _change_key(ans):
    if ans["status"] == "value":
        return ("value", ans["value"])
    if ans["status"] == "conflict":
        return ("conflict", tuple(ans["values"]))
    return ("unknown",)


def _step(table, rep):
    """Apply one report to the flat claim table."""
    if rep["kind"] == "assert":
        table.append({"id": rep["report_id"], "subject": rep["subject"],
                      "attribute": rep["attribute"], "value": rep["value"],
                      "vf": rep["valid_from"], "rank": rep["rank"], "source": rep["source"],
                      "alive": True})
        return
    hits = [row for row in table if row["id"] == rep["target_report_id"]]
    if len(hits) != 1 or not hits[0]["alive"]:
        return                                    # no claim to act on: ineffective
    target = hits[0]
    if rep["kind"] == "retract":
        if rep["source"] == target["source"]:
            target["alive"] = False
        return
    if rep["rank"] >= target["rank"]:
        target["alive"] = False
        table.append({"id": rep["report_id"], "subject": target["subject"],
                      "attribute": target["attribute"],
                      "value": target["value"] if rep["value"] is None else rep["value"],
                      "vf": target["vf"] if rep["valid_from"] is None else rep["valid_from"],
                      "rank": rep["rank"], "source": rep["source"], "alive": True})


def _before(table, subject, attribute, anchor):
    a = _eval(table, ANCHOR_PREFIX + anchor, ANCHOR_ATTRIBUTE, 0)
    if a["status"] == "unknown":
        return {"status": "unknown", "reason": "anchor_not_found"}
    if a["status"] == "conflict":
        return {"status": "unknown", "reason": "anchor_ambiguous"}
    ans = _eval(table, subject, attribute, a["value"] - 1)
    if ans["status"] == "unknown":
        return {"status": "unknown", "reason": "no_version_before"}
    return ans


def _standing(table, subject, attribute):
    return sorted([row["vf"], row["value"]] for row in _rows_of(table, subject, attribute))


def _snapshot(table, q, K, results, aux):
    """Answer every part of question q that needs knowledge time K."""
    s, a, op = q["subject"], q["attribute"], q["op"]
    if op == "why_changed":
        st = aux.setdefault(q["qid"], {})
        if K == q["k1"]:
            st["start"] = _change_key(_eval(table, s, a, q["v"]))
            st["last"], st["ids"] = st["start"], []
        if K == q["k2"]:
            end = _change_key(_eval(table, s, a, q["v"]))
            results[q["qid"]] = "unchanged" if end == st["start"] else list(st["ids"])
        return
    if op == "current":
        results[q["qid"]] = _eval(table, s, a, K)
    elif op == "valid_at":
        results[q["qid"]] = _eval(table, s, a, q["v"])
    elif op == "believed_at":
        results[q["qid"]] = _eval(table, s, a, K)
    elif op == "conflicts":
        results[q["qid"]] = [{"valid_from": h["valid_from"], "values": h["values"], "ids": h["ids"]}
                             for h in _history(table, s, a) if h["status"] == "conflict"]
    elif op == "history":
        results[q["qid"]] = _history(table, s, a)
    elif op == "before":
        results[q["qid"]] = _before(table, s, a, q["anchor"])
    else:
        raise ValueError(op)
    hist = _history(table, s, a)
    info = {"standing": _standing(table, s, a),
            "open_conflict": any(h["status"] == "conflict" for h in hist)}
    if op == "before":
        info["anchor_standing"] = _standing(table, ANCHOR_PREFIX + q["anchor"], ANCHOR_ATTRIBUTE)
    aux[q["qid"]] = info


def _times(q):
    op = q["op"]
    if op == "believed_at":
        return [q["t"]]
    if op == "why_changed":
        return [q["k1"], q["k2"]]
    return [q["now"]]


def reference_answers(reports, questions, track_current=()):
    """One pass over the world. Returns (answers by qid, aux by qid, past current answers).
    `track_current`: facts (subject, attribute) whose current answer value_at(d, d) is
    recorded at the end of every day d with a report about them (for the stale measure)."""
    reps = sorted(reports, key=lambda r: (r["report_day"], r["report_id"]))
    need: dict[int, list] = {}
    for q in questions:
        for K in _times(q):
            need.setdefault(K, []).append(q)
    watch = [q for q in questions if q["op"] == "why_changed"]
    track = {tuple(f): [] for f in track_current}
    table, results, aux, today = [], {}, {}, set()
    pending = sorted(need)
    i = 0
    while pending or i < len(reps):
        next_day = reps[i]["report_day"] if i < len(reps) else None
        if pending and (next_day is None or pending[0] < next_day):
            K = pending.pop(0)
            for q in need[K]:
                _snapshot(table, q, K, results, aux)
            continue
        if next_day is None:
            break
        rep = reps[i]
        i += 1
        _step(table, rep)
        for q in watch:
            st = aux.get(q["qid"])
            if st is not None and "start" in st and q["k1"] < rep["report_day"] <= q["k2"]:
                key = _change_key(_eval(table, q["subject"], q["attribute"], q["v"]))
                if key != st["last"]:
                    st["ids"].append(rep["report_id"])
                    st["last"] = key
        today.add((rep["subject"], rep["attribute"]))
        if i >= len(reps) or reps[i]["report_day"] != rep["report_day"]:
            for f, seen in track.items():
                if f in today:
                    seen.append(_eval(table, f[0], f[1], rep["report_day"]))
            today = set()
    missing = [q["qid"] for q in questions if q["qid"] not in results]
    if missing:
        raise RuntimeError(f"R answered no result for {missing[:5]}")
    why_aux = {q["qid"] for q in watch}
    aux = {k: v for k, v in aux.items() if k not in why_aux}
    return results, aux, {f: seen for f, seen in track.items()}
