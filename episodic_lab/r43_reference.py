"""Round 4.3 reference side (docs/ROUND_4_3.md sections 2, 3, 5, 6) - built ONLY on R's own
step function and claim table (episodic_lab/r40_reference.py, unchanged) and on the
original reports; no code of M, of the checkpoint or of H's digest is used here.

- reference_state(reports, times): the standing claims of ALL facts at each knowledge time,
  normalised as (subject, attribute, id, value, valid_from, rank, source, origin); the origin
  is taken from the report whose id the claim carries (an assert or an effective
  correction), looked up in the given reports;
- effectiveness(reports): per correct / retract report, whether R's step changed its table;
- reference_digest(reports, subject, attribute, k): the digest of section 3 from R's table;
- synthetic_reports(claims, c): claims written as assert reports of day c.
"""
from __future__ import annotations

import json

from .r40_reference import _decide, _eval, _history, _step

DIGEST_SCHEMA = "episodic_lab.r43_digest.v1"


def _ordered(reports):
    return sorted(reports, key=lambda r: (r["report_day"], r["report_id"]))


def _norm_rows(table, origin_of):
    return sorted((row["subject"], row["attribute"], row["id"], json.dumps(row["value"]), row["vf"], row["rank"],
                   row["source"], origin_of[row["id"]]) for row in table if row["alive"])


def reference_state(reports, times):
    """{k: sorted normalised tuples of all standing claims at knowledge time k} (the value
    is JSON-encoded inside the tuple so that values of different types sort)."""
    reps = _ordered(reports)
    origin_of = {r["report_id"]: r["origin"] for r in reps}
    table, out, i = [], {}, 0
    for k in sorted(set(times)):
        while i < len(reps) and reps[i]["report_day"] <= k:
            _step(table, reps[i])
            i += 1
        out[k] = _norm_rows(table, origin_of)
    return out


def effectiveness(reports):
    """{report id: True / False} for every correct / retract report: did R's step change the
    table (a row withdrawn or added)?"""
    table, out = [], {}
    for r in _ordered(reports):
        before = (len(table), sum(row["alive"] for row in table))
        _step(table, r)
        if r["kind"] != "assert":
            out[r["report_id"]] = (len(table), sum(row["alive"] for row in table)) != before
    return out


def table_at(reports, k):
    table = []
    for r in _ordered(reports):
        if r["report_day"] > k:
            break
        _step(table, r)
    return table


def _entry(row, origin_of):
    return {"id": row["id"], "value": row["value"], "valid_from": row["vf"], "source": row["source"],
            "rank": row["rank"], "origin": origin_of[row["id"]]}


def _vkey(v):
    return json.dumps(v, sort_keys=True)


def _groups(rows, origin_of):
    by = {}
    for row in rows:
        by.setdefault(_vkey(row["value"]), (row["value"], []))[1].append(_entry(row, origin_of))
    return [{"value": by[k][0], "claims": sorted(by[k][1], key=lambda e: e["id"])} for k in sorted(by)]


def reference_digest(reports, subject, attribute, k):
    """R's digest at knowledge time k: R's history merged into segments with support, agree,
    dissent and independent origins; written without M's or H's code."""
    origin_of = {r["report_id"]: r["origin"] for r in reports}
    table = table_at(reports, k)
    rows = [row for row in table if row["alive"] and row["subject"] == subject and row["attribute"] == attribute]
    days = sorted({row["vf"] for row in rows})
    versions = []
    for n, d in enumerate(days):
        at = [row for row in rows if row["vf"] == d]
        dec = _decide(at)
        top = max(row["rank"] for row in at)
        versions.append({"vf": d, "to": days[n + 1] - 1 if n + 1 < len(days) else None, "dec": dec,
                         "deciding": [row for row in at if row["rank"] == top],
                         "lower": [row for row in at if row["rank"] < top]})
    segments = []
    for ver in versions:
        vals = [ver["dec"]["value"]] if ver["dec"]["status"] == "value" else list(ver["dec"]["values"])
        key = (ver["dec"]["status"], tuple(_vkey(v) for v in vals))
        if segments and segments[-1]["_key"] == key:
            seg = segments[-1]
            seg["valid_to"] = ver["to"]
        else:
            seg = {"_key": key, "valid_from": ver["vf"], "valid_to": ver["to"], "status": ver["dec"]["status"],
                   "_vals": vals, "_support": [], "_agree": [], "_dissent": []}
            segments.append(seg)
        seg["_support"] += ver["deciding"]
        for row in ver["lower"]:
            (seg["_agree"] if _vkey(row["value"]) in {_vkey(v) for v in vals} else seg["_dissent"]).append(row)
    out = []
    for seg in segments:
        item = {"valid_from": seg["valid_from"], "valid_to": seg["valid_to"], "status": seg["status"],
                "support": _groups(seg["_support"], origin_of), "agree": _groups(seg["_agree"], origin_of),
                "dissent": sorted((_entry(r, origin_of) for r in seg["_dissent"]), key=lambda e: e["id"])}
        if seg["status"] == "value":
            item["value"] = seg["_vals"][0]
        else:
            item["values"] = sorted(seg["_vals"], key=_vkey)
        origins = {}
        for row in seg["_support"] + seg["_agree"]:
            origins.setdefault(_vkey(row["value"]), set()).add(origin_of[row["id"]])
        item["independent_origins"] = [{"value": json.loads(v), "n": len(origins[v])} for v in sorted(origins)]
        out.append(item)
    return {"schema": DIGEST_SCHEMA, "segments": out, "current": _eval(table, subject, attribute, k)}


def synthetic_reports(claims, c):
    """Claims {id, subject, attribute, value, valid_from, rank, source, origin} as assert
    reports of day c (section 2, the independent check by R)."""
    return [{"report_id": x["id"], "report_day": c, "source": x["source"], "rank": x["rank"], "origin": x["origin"],
             "subject": x["subject"], "attribute": x["attribute"], "kind": "assert", "value": x["value"],
             "valid_from": x["valid_from"], "target_report_id": None}
            for x in sorted(claims, key=lambda x: x["id"])]


def claims_at(reports, c, facts=None) -> list[dict]:
    """The standing claims at knowledge time c from R's table, as claim dicts (origin from
    the report whose id the claim carries); optionally only the given facts."""
    origin_of = {r["report_id"]: r["origin"] for r in reports}
    return [{"id": row["id"], "subject": row["subject"], "attribute": row["attribute"], "value": row["value"],
             "valid_from": row["vf"], "rank": row["rank"], "source": row["source"], "origin": origin_of[row["id"]]}
            for row in table_at(reports, c) if row["alive"]
            and (facts is None or (row["subject"], row["attribute"]) in facts)]


def control_claims(reports, c, kind) -> list[dict]:
    """The lossy control checkpoints of section 5, derived from R's table at c (so that the
    informative cases are known before any run of H): K1 the deciding claims of the current
    version (R's value_at(c, c)), K2 the deciding claims of every version (R's history), K3
    every standing claim with its id renamed rN -> r(99999 - N)."""
    table = table_at(reports, c)
    claims = claims_at(reports, c)
    if kind == "K3":
        return [dict(x, id=f"r{99999 - int(x['id'][1:]):05d}") for x in claims]
    keep = set()
    for f in sorted({(x["subject"], x["attribute"]) for x in claims}):
        if kind == "K1":
            keep |= set(_eval(table, f[0], f[1], c).get("ids", []))
        elif kind == "K2":
            keep |= {i for h in _history(table, f[0], f[1]) for i in h["ids"]}
        else:
            raise ValueError(kind)
    return [x for x in claims if x["id"] in keep]
