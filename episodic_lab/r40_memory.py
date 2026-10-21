"""Round 4.0 memory M (docs/ROUND_4_0.md section 2): an append-only, hash-chained store of
immutable reports and a two-time resolver over it.

Everything except the stored reports is a pure function of the reports with
report_day <= known_time. Claims: one per assert and per effective correction, keyed by
the report id that created it. After every effective report the value of each valid_from
day is decided again by rank from the claims standing then.

Answer format (shared by convention with R and the baselines, not by code):
  {"status": "value", "value": x, "ids": [...]}
  {"status": "conflict", "values": [...], "ids": [...]}
  {"status": "unknown", "reason": "no_version" | "anchor_not_found" | "anchor_ambiguous"
                                  | "no_version_before"}
why_changed -> "unchanged" or the ordered list of report ids; conflicts -> list of
{"valid_from", "values", "ids"}; history -> list of {"valid_from", "valid_to", "status",
"value" | "values", "ids"}.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .r40_schema import ANCHOR_ATTRIBUTE, ANCHOR_PREFIX, REPORT_SCHEMA, check_report, order_key

STORE_SCHEMA = "episodic_lab.r40_store.v1"
GENESIS = "0" * 64


class StoreCorrupted(RuntimeError):
    pass


def _digest(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ReportStore:
    """Append-only JSON-lines store of reports, chained by SHA-256; a changed, removed or
    reordered record is detected on load; `expect` (a seal kept outside the chain) also
    detects a cut-off tail."""

    def __init__(self, path=None, expect: dict | None = None):
        self.path = Path(path) if path is not None else None
        self._records: list[dict] = []
        if self.path is not None and self.path.exists():
            prev = GENESIS
            for n, line in enumerate(self.path.read_text(encoding="utf-8").splitlines()):
                rec = json.loads(line)
                if rec.get("prev") != prev or rec.get("seq") != n or _digest(rec) != rec.get("hash") \
                        or rec.get("schema") != STORE_SCHEMA:
                    raise StoreCorrupted(f"record {n}")
                check_report(rec["report"])
                prev = rec["hash"]
                self._records.append(rec)
        if expect is not None and self.seal() != expect:
            raise StoreCorrupted(f"seal mismatch: {self.seal()} != {expect}")

    def seal(self) -> dict:
        return {"count": len(self._records),
                "head": self._records[-1]["hash"] if self._records else GENESIS}

    @property
    def reports(self) -> list[dict]:
        return [dict(rec["report"]) for rec in self._records]

    def extend(self, reports) -> None:
        """Append reports in arrival (= total) order; one write and one fsync."""
        lines = []
        for r in reports:
            check_report(r)
            if self._records and order_key(r) <= order_key(self._records[-1]["report"]):
                raise ValueError(f"{r['report_id']} breaks the total order")
            prev = self._records[-1]["hash"] if self._records else GENESIS
            rec = {"schema": STORE_SCHEMA, "report_schema": REPORT_SCHEMA,
                   "seq": len(self._records), "report": dict(r), "prev": prev}
            rec["hash"] = _digest(rec)
            self._records.append(rec)
            lines.append(json.dumps(rec, sort_keys=True) + "\n")
        if self.path is not None and lines:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write("".join(lines))
                fh.flush()
                os.fsync(fh.fileno())


class _Claim:
    __slots__ = ("cid", "value", "vf", "rank", "source", "origin", "standing")

    def __init__(self, cid, value, vf, rank, source, origin):
        self.cid, self.value, self.vf, self.rank = cid, value, vf, rank
        self.source, self.origin, self.standing = source, origin, True


def _apply(claims: dict, rep: dict) -> bool:
    """Transition rules (section 2). Returns True if the report was effective."""
    kind = rep["kind"]
    if kind == "assert":
        claims[rep["report_id"]] = _Claim(rep["report_id"], rep["value"], rep["valid_from"],
                                          rep["rank"], rep["source"], rep["origin"])
        return True
    tgt = claims.get(rep["target_report_id"])
    # missing target, a retract report, a claimless correction report, a withdrawn claim
    if tgt is None or not tgt.standing:
        return False
    if kind == "correct":
        if rep["rank"] < tgt.rank:
            return False
        tgt.standing = False
        claims[rep["report_id"]] = _Claim(
            rep["report_id"],
            rep["value"] if rep["value"] is not None else tgt.value,
            rep["valid_from"] if rep["valid_from"] is not None else tgt.vf,
            rep["rank"], rep["source"], rep["origin"])
        return True
    if rep["source"] != tgt.source:
        return False
    tgt.standing = False
    return True


def _versions(claims: dict) -> list[dict]:
    by_day: dict[int, list[_Claim]] = {}
    for c in claims.values():
        if c.standing:
            by_day.setdefault(c.vf, []).append(c)
    days = sorted(by_day)
    out = []
    for i, d in enumerate(days):
        top = max(c.rank for c in by_day[d])
        tops = [c for c in by_day[d] if c.rank == top]
        values = sorted({c.value for c in tops})
        ids = sorted(c.cid for c in tops)
        v = {"valid_from": d, "valid_to": days[i + 1] - 1 if i + 1 < len(days) else None}
        if len(values) == 1:
            v.update(status="value", value=values[0], ids=ids)
        else:
            v.update(status="conflict", values=values, ids=ids)
        out.append(v)
    return out


def _answer_of(version: dict | None, reason: str = "no_version") -> dict:
    if version is None:
        return {"status": "unknown", "reason": reason}
    if version["status"] == "value":
        return {"status": "value", "value": version["value"], "ids": list(version["ids"])}
    return {"status": "conflict", "values": list(version["values"]), "ids": list(version["ids"])}


def _key(ans: dict) -> tuple:
    """What counts as a change for why_changed: status and value(s), not report ids."""
    if ans["status"] == "value":
        return ("value", ans["value"])
    if ans["status"] == "conflict":
        return ("conflict", tuple(ans["values"]))
    return ("unknown",)


class Memory:
    """M: indexes the store by fact and replays the fact's reports per question."""

    def __init__(self, reports):
        reports = list(reports)
        for r in reports:
            check_report(r)
        if [order_key(r) for r in reports] != sorted(order_key(r) for r in reports):
            raise ValueError("reports are not in total order")
        if len({r["report_id"] for r in reports}) != len(reports):
            raise ValueError("duplicate report ids")
        self._by_fact: dict[tuple, list[dict]] = {}
        for r in reports:
            self._by_fact.setdefault((r["subject"], r["attribute"]), []).append(r)
        self._cache: dict = {}

    def _claims_at(self, fact, k) -> dict:
        claims: dict = {}
        for r in self._by_fact.get(fact, ()):
            if r["report_day"] > k:
                break
            _apply(claims, r)
        return claims

    def versions(self, fact, k) -> list[dict]:
        key = (fact, k)
        if key not in self._cache:
            self._cache[key] = _versions(self._claims_at(fact, k))
        return [dict(v) for v in self._cache[key]]

    def value_at(self, fact, v, k) -> dict:
        found = None
        for ver in self.versions(fact, k):
            if ver["valid_from"] <= v:
                found = ver
            else:
                break
        return _answer_of(found)

    def why_changed(self, fact, v, k1, k2):
        if _key(self.value_at(fact, v, k1)) == _key(self.value_at(fact, v, k2)):
            return "unchanged"
        claims = self._claims_at(fact, k1)
        ids, before = [], _key(self._value_from(claims, v))
        for r in self._by_fact.get(fact, ()):
            if r["report_day"] <= k1:
                continue
            if r["report_day"] > k2:
                break
            _apply(claims, r)
            after = _key(self._value_from(claims, v))
            if after != before:
                ids.append(r["report_id"])
            before = after
        return ids

    @staticmethod
    def _value_from(claims, v) -> dict:
        found = None
        for ver in _versions(claims):
            if ver["valid_from"] <= v:
                found = ver
        return _answer_of(found)

    def before(self, fact, anchor: str, now: int) -> dict:
        a = self.value_at((ANCHOR_PREFIX + anchor, ANCHOR_ATTRIBUTE), 0, now)
        if a["status"] == "unknown":
            return {"status": "unknown", "reason": "anchor_not_found"}
        if a["status"] == "conflict":
            return {"status": "unknown", "reason": "anchor_ambiguous"}
        ans = self.value_at(fact, a["value"] - 1, now)
        if ans["status"] == "unknown":
            return {"status": "unknown", "reason": "no_version_before"}
        return ans

    def answer(self, q: dict):
        fact, now, op = (q["subject"], q["attribute"]), q["now"], q["op"]
        if op == "current":
            return self.value_at(fact, now, now)
        if op == "valid_at":
            return self.value_at(fact, q["v"], now)
        if op == "believed_at":
            return self.value_at(fact, q["t"], q["t"])
        if op == "why_changed":
            return self.why_changed(fact, q["v"], q["k1"], q["k2"])
        if op == "conflicts":
            return [{"valid_from": x["valid_from"], "values": x["values"], "ids": x["ids"]}
                    for x in self.versions(fact, now) if x["status"] == "conflict"]
        if op == "history":
            return self.versions(fact, now)
        if op == "before":
            return self.before(fact, q["anchor"], now)
        raise ValueError(f"unknown operator {op}")
