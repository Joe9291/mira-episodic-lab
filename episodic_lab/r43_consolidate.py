"""Round 4.3 source-bound consolidation (docs/ROUND_4_3.md, design v3 approved
2026-10-24 - reviews/2026-10-24_r43v3_astra.txt).

- checkpoints C(c): the claims standing at a complete cut c, per fact, with a header that
  binds them to the archive prefix and to the parent checkpoint; built from scratch or
  incrementally; canonical JSON; own hash over the object without its hash field;
- the hot memory H: M (episodic_lab/r40_memory.py, unchanged) whose claim replay starts
  from a checkpoint instead of from the first report - Mode A (archive kept, checkpoints
  every D days, each question from the latest checkpoint <= its needed knowledge time) and
  Mode T (one checkpoint + the tail; a question that needs an earlier knowledge time is
  answered "compacted");
- H's digest (section 3) from H's own standing claims (M's version function);
- the lossy controls K1 - K3 (claim sets from the reference side), loadable ONLY through
  `control_memory` (a test path that skips every integrity check, unused by Modes A / T);
- disk layout and loading with the trust record (integrity, tamper and interrupted-write
  rules of section 6 (4)).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from . import r40_memory as M40
from .r40_memory import GENESIS, STORE_SCHEMA, Memory, ReportStore, StoreCorrupted, _apply, _Claim, _digest, _versions
from .r40_schema import REPORT_SCHEMA, check_report

CHECKPOINT_SCHEMA = "episodic_lab.r43_checkpoint.v1"
TRUST_SCHEMA = "episodic_lab.r43_trust.v1"
DIGEST_SCHEMA = "episodic_lab.r43_digest.v1"
GENESIS_CHECKPOINT = "0" * 64
D_MODE_A = 5
COMPACTED = {"status": "unknown", "reason": "compacted"}
RESOLVER_SHA256 = hashlib.sha256(Path(M40.__file__).read_bytes()).hexdigest()


class CheckpointRefused(RuntimeError):
    pass


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha(obj) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def _vkey(v):
    return json.dumps(v, sort_keys=True)


def needed_time(q) -> int:
    return {"believed_at": lambda: q["t"], "digest_at": lambda: q["t"],
            "why_changed": lambda: q["k1"]}.get(q["op"], lambda: q["now"])()


# ------------------------------------------------------------------ chain helpers
def chain_records(reports):
    """The ReportStore records (seq, prev, hash) of all reports, in total order."""
    store = ReportStore()
    store.extend(reports)
    return store._records


def prefix_len(reports, c) -> int:
    n = 0
    while n < len(reports) and reports[n]["report_day"] <= c:
        n += 1
    return n


def seal_of(records, n) -> dict:
    return {"count": n, "head": records[n - 1]["hash"] if n else GENESIS}


# ------------------------------------------------------------------ checkpoints
def _claims_to_payload(by_fact: dict) -> list:
    facts = []
    for (s, a) in sorted(by_fact):
        claims = sorted(({"id": c.cid, "value": c.value, "valid_from": c.vf, "rank": c.rank, "source": c.source,
                          "origin": c.origin} for c in by_fact[(s, a)].values() if c.standing), key=lambda x: x["id"])
        if claims:
            facts.append({"subject": s, "attribute": a, "claims": claims})
    return facts


def _replay(by_fact: dict, reports) -> None:
    for r in reports:
        _apply(by_fact.setdefault((r["subject"], r["attribute"]), {}), r)


def _from_payload(facts) -> dict:
    by_fact = {}
    for f in facts:
        d = by_fact.setdefault((f["subject"], f["attribute"]), {})
        for x in f["claims"]:
            d[x["id"]] = _Claim(x["id"], x["value"], x["valid_from"], x["rank"], x["source"], x["origin"])
    return by_fact


def _seal_checkpoint(cp: dict) -> dict:
    cp = {k: v for k, v in cp.items() if k != "hash"}
    cp["hash"] = sha(cp)
    return cp


def build_checkpoint(reports, records, c, parent_hash=GENESIS_CHECKPOINT) -> dict:
    """C(c) from scratch: replay of the archive prefix (all reports with report_day <= c)."""
    n = prefix_len(reports, c)
    by_fact = {}
    _replay(by_fact, reports[:n])
    return _header(c, records, n, reports, parent_hash, _claims_to_payload(by_fact))


def extend_checkpoint(parent: dict, reports, records, c2) -> dict:
    """C(c2) incrementally: the parent's standing claims plus the segment (c1, c2]."""
    c1 = parent["cut"]
    if c2 < c1:
        raise ValueError("cut before the parent's cut")
    by_fact = _from_payload(parent["facts"])
    n1, n2 = prefix_len(reports, c1), prefix_len(reports, c2)
    _replay(by_fact, reports[n1:n2])
    return _header(c2, records, n2, reports, parent["hash"], _claims_to_payload(by_fact))


def _header(c, records, n, reports, parent_hash, facts) -> dict:
    return _seal_checkpoint({"schema": CHECKPOINT_SCHEMA, "cut": c, "archive_seal": seal_of(records, n),
                             "highest_id": reports[n - 1]["report_id"] if n else None, "parent": parent_hash,
                             "resolver_sha256": RESOLVER_SHA256, "facts": facts})


def checkpoint_claims(cp) -> list[dict]:
    return [dict(x, subject=f["subject"], attribute=f["attribute"]) for f in cp["facts"] for x in f["claims"]]


def normalised(claims) -> list:
    """The normalised claim set of pass rule (8): (subject, attribute, id, value, valid_from,
    rank, source, origin), the value JSON-encoded."""
    return sorted((x["subject"], x["attribute"], x["id"], json.dumps(x["value"]), x["valid_from"], x["rank"],
                   x["source"], x["origin"]) for x in claims)


def check_checkpoint(cp: dict, trust: dict | None = None) -> None:
    """Integrity of a regular checkpoint: schema, own hash, sorted canonical payload, resolver
    hash; and, with a trust record, the expected hash and archive seal."""
    if cp.get("schema") != CHECKPOINT_SCHEMA:
        raise CheckpointRefused("schema")
    if cp.get("hash") != sha({k: v for k, v in cp.items() if k != "hash"}):
        raise CheckpointRefused("own hash")
    if cp["resolver_sha256"] != RESOLVER_SHA256:
        raise CheckpointRefused("resolver differs")
    keys = [(f["subject"], f["attribute"]) for f in cp["facts"]]
    if keys != sorted(keys) or len(set(keys)) != len(keys) or any(not f["claims"] for f in cp["facts"]):
        raise CheckpointRefused("facts not canonical")
    for f in cp["facts"]:
        ids = [x["id"] for x in f["claims"]]
        if ids != sorted(ids) or len(set(ids)) != len(ids):
            raise CheckpointRefused("claims not canonical")
        for x in f["claims"]:
            if cp["highest_id"] is None or x["id"] > cp["highest_id"]:
                raise CheckpointRefused("claim id above the highest prefix id")
    if trust is not None:
        if trust.get("schema") != TRUST_SCHEMA or trust["checkpoint_hash"] != cp["hash"]:
            raise CheckpointRefused("checkpoint does not match the trust record")
        if trust["archive_seal_at_cut"] != cp["archive_seal"] or not trust.get("verified"):
            raise CheckpointRefused("archive seal / verification not in the trust record")


def trust_record(cp, tail_seal) -> dict:
    return {"schema": TRUST_SCHEMA, "checkpoint_hash": cp["hash"], "archive_seal_at_cut": cp["archive_seal"],
            "tail_seal": tail_seal, "verified": True}


def verify_against_archive(cp, reports, records) -> bool:
    """Mode T, before the deletion: the checkpoint rebuilt from scratch (same parent) has the
    same bytes. The R check of section 2 is run by the caller (bench)."""
    return canonical(build_checkpoint(reports, records, cp["cut"], cp["parent"])) == canonical(cp)


# ------------------------------------------------------------------ hot memory
class Hot(Memory):
    """M with a claim replay that starts from checkpoints. `checkpoints`: {cut: checkpoint};
    `reports`: the reports H holds (Mode A: the whole archive; Mode T: the tail); `floor`:
    Mode T's cut (questions that need an earlier knowledge time are compacted), None in
    Mode A."""

    def __init__(self, checkpoints: dict, reports, floor=None, highest_id=None):
        super().__init__(reports)
        if highest_id is not None and any(r["report_id"] <= highest_id for r in reports):
            raise StoreCorrupted("tail report id at or below the checkpoint's highest id")
        self._cps = {c: _from_payload(cp["facts"]) for c, cp in checkpoints.items()}
        self._cuts = sorted(self._cps)
        self.floor = floor
        self.reads = []                          # (claims loaded, reports replayed) per replay

    def _base(self, k):
        cut = max(c for c in self._cuts if c <= k)      # raises if no checkpoint <= k
        return cut, self._cps[cut]

    def _claims_at(self, fact, k) -> dict:
        if self.floor is not None and k < self.floor:
            raise _Compacted()
        cut, cps = self._base(k)
        claims = {cid: _Claim(c.cid, c.value, c.vf, c.rank, c.source, c.origin)
                  for cid, c in cps.get(fact, {}).items()}
        loaded, n = len(claims), 0
        for r in self._by_fact.get(fact, ()):
            if r["report_day"] <= cut:
                continue
            if r["report_day"] > k:
                break
            _apply(claims, r)
            n += 1
        self.reads.append((loaded, n))
        return claims

    def state_at(self, k) -> list:
        """The standing claims H has propagated at k, over ALL facts it knows (pass rule 8)."""
        facts = set(self._by_fact) | {f for c in self._cuts if c <= k for f in self._cps[c]}
        out = []
        for f in sorted(facts):
            for c in self._claims_at(f, k).values():
                if c.standing:
                    out.append({"subject": f[0], "attribute": f[1], "id": c.cid, "value": c.value,
                                "valid_from": c.vf, "rank": c.rank, "source": c.source, "origin": c.origin})
        return out

    def effectiveness(self) -> dict:
        """Per correct / retract report H holds after its checkpoint: effective under H?"""
        cut, cps = self._base(self.floor if self.floor is not None else 0)
        by_fact = {f: {cid: _Claim(c.cid, c.value, c.vf, c.rank, c.source, c.origin) for cid, c in d.items()}
                   for f, d in cps.items()}
        out = {}
        for f, reps in self._by_fact.items():
            claims = by_fact.setdefault(f, {})
            for r in reps:
                if r["report_day"] <= cut:
                    continue
                eff = _apply(claims, r)
                if r["kind"] != "assert":
                    out[r["report_id"]] = eff
        return out

    def digest(self, fact, k) -> dict:
        claims = [c for c in self._claims_at(fact, k).values() if c.standing]
        return digest_from_claims(claims, _versions({c.cid: c for c in claims}), self.value_at(fact, k, k))

    def answer(self, q):
        if self.floor is not None and needed_time(q) < self.floor:
            return "compacted" if q["op"] == "why_changed" else dict(COMPACTED)
        fact = (q["subject"], q["attribute"])
        if q["op"] == "digest":
            return self.digest(fact, q["now"])
        if q["op"] == "digest_at":
            return self.digest(fact, q["t"])
        return super().answer(q)


class _Compacted(Exception):
    pass


def full_digest(memory: Memory, fact, k) -> dict:
    """The digest computed from the full store (M), with H's digest function."""
    claims = [c for c in memory._claims_at(fact, k).values() if c.standing]
    return digest_from_claims(claims, _versions({c.cid: c for c in claims}), memory.value_at(fact, k, k))


# ------------------------------------------------------------------ digest (H side)
def _claim_entry(c) -> dict:
    return {"id": c.cid, "value": c.value, "valid_from": c.vf, "source": c.source, "rank": c.rank, "origin": c.origin}


def _group(claims) -> list:
    by = {}
    for c in claims:
        by.setdefault(_vkey(c.value), []).append(_claim_entry(c))
    return [{"value": json.loads(k), "claims": sorted(v, key=lambda e: e["id"])} for k, v in sorted(by.items())]


def digest_from_claims(claims, versions, current) -> dict:
    by_day = {}
    for c in claims:
        by_day.setdefault(c.vf, []).append(c)
    segs = []
    for ver in versions:
        vals = [ver["value"]] if ver["status"] == "value" else list(ver["values"])
        vk = {_vkey(v) for v in vals}
        at = by_day[ver["valid_from"]]
        deciding = [c for c in at if c.cid in set(ver["ids"])]
        lower = [c for c in at if c.cid not in set(ver["ids"])]
        key = (ver["status"], tuple(sorted(vk)))
        if not segs or segs[-1]["key"] != key:
            segs.append({"key": key, "valid_from": ver["valid_from"], "status": ver["status"], "vals": vals,
                         "support": [], "agree": [], "dissent": []})
        seg = segs[-1]
        seg["valid_to"] = ver["valid_to"]
        seg["support"] += deciding
        for c in lower:
            seg["agree" if _vkey(c.value) in vk else "dissent"].append(c)
    out = []
    for s in segs:
        item = {"valid_from": s["valid_from"], "valid_to": s["valid_to"], "status": s["status"],
                "support": _group(s["support"]), "agree": _group(s["agree"]),
                "dissent": sorted((_claim_entry(c) for c in s["dissent"]), key=lambda e: e["id"])}
        if s["status"] == "value":
            item["value"] = s["vals"][0]
        else:
            item["values"] = sorted(s["vals"], key=_vkey)
        origins = {}
        for c in s["support"] + s["agree"]:
            origins.setdefault(_vkey(c.value), set()).add(c.origin)
        item["independent_origins"] = [{"value": json.loads(k), "n": len(v)} for k, v in sorted(origins.items())]
        out.append(item)
    return {"schema": DIGEST_SCHEMA, "segments": out, "current": current}


def digest_entries(dg) -> list:
    """All claim entries of a digest (support, agree, dissent) - the partition check."""
    out = []
    for s in dg["segments"]:
        for g in s["support"] + s["agree"]:
            out += g["claims"]
        out += s["dissent"]
    return out


# ------------------------------------------------------------------ the two modes
def mode_a(reports, records, d=D_MODE_A):
    """Mode A: checkpoints at 0, d, 2d, ... up to the last report day, chained; H over the
    whole archive."""
    last = reports[-1]["report_day"] if reports else 0
    cps, parent = {}, None
    for c in range(0, last + 1, d):
        cp = build_checkpoint(reports, records, c) if parent is None else extend_checkpoint(parent, reports, records, c)
        cps[c] = parent = cp
    return Hot(cps, reports), cps


def mode_t(cp, reports, records, trust):
    """Mode T: the checkpoint (checked, also against the trust record) and the tail only."""
    check_checkpoint(cp, trust)
    n = prefix_len(reports, cp["cut"])
    tail = reports[n:]
    if trust["tail_seal"] != seal_of(records, len(reports)):
        raise CheckpointRefused("tail seal")
    return Hot({cp["cut"]: cp}, tail, floor=cp["cut"], highest_id=cp["highest_id"])


# ------------------------------------------------------------------ lossy controls (test path only)
def control_memory(claims, cut, reports):
    """TEST PATH: H from a control claim set (episodic_lab/r43_reference.control_claims),
    without any integrity check. Not used by Modes A / T."""
    by_fact = {}
    for x in claims:
        by_fact.setdefault((x["subject"], x["attribute"]), []).append(
            {k: x[k] for k in ("id", "value", "valid_from", "rank", "source", "origin")})
    pseudo = {"facts": [{"subject": f[0], "attribute": f[1], "claims": sorted(v, key=lambda y: y["id"])}
                        for f, v in sorted(by_fact.items())]}
    n = prefix_len(reports, cut)
    return Hot({cut: pseudo}, reports[n:], floor=cut)


# ------------------------------------------------------------------ disk (persistence, integrity)
def tail_records(tail_reports, start_seal) -> list[dict]:
    """The tail as a chain SEGMENT of the archive: seq continues the archive count, the first
    prev is the archive head at the cut (records in ReportStore's format)."""
    out, prev, seq = [], start_seal["head"], start_seal["count"]
    for r in tail_reports:
        check_report(r)
        rec = {"schema": STORE_SCHEMA, "report_schema": REPORT_SCHEMA, "seq": seq, "report": dict(r), "prev": prev}
        rec["hash"] = _digest(rec)
        out.append(rec)
        prev, seq = rec["hash"], seq + 1
    return out


def read_tail(path, start_seal) -> tuple[list[dict], dict]:
    """Reads and verifies a tail segment; returns (reports, seal of the whole chain)."""
    prev, seq, reps = start_seal["head"], start_seal["count"], []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec.get("prev") != prev or rec.get("seq") != seq or _digest(rec) != rec.get("hash") \
                or rec.get("schema") != STORE_SCHEMA:
            raise StoreCorrupted(f"tail record {seq}")
        check_report(rec["report"])
        reps.append(rec["report"])
        prev, seq = rec["hash"], seq + 1
    return reps, {"count": seq, "head": prev}


def write_state(directory, cp, tail_reports, crash_after=None) -> dict:
    """Write protocol: (1) checkpoint file by hash, (2) tail segment file by checkpoint hash,
    (3) trust record atomically (temp + rename), (4) delete files of older states.
    `crash_after` in {1, 2, 3} stops after that step (interrupted-write tests). Returns the
    trust record (the caller keeps a trusted copy outside the directory)."""
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"checkpoint_{cp['hash']}.json").write_bytes(canonical(cp))
    recs = tail_records(tail_reports, cp["archive_seal"])
    trust = trust_record(cp, {"count": cp["archive_seal"]["count"] + len(recs),
                              "head": recs[-1]["hash"] if recs else cp["archive_seal"]["head"]})
    if crash_after == 1:
        return trust
    (d / f"tail_{cp['hash']}.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs),
                                                 encoding="utf-8")
    if crash_after == 2:
        return trust
    tmp = d / "trust.json.tmp"
    tmp.write_bytes(canonical(trust))
    os.replace(tmp, d / "trust.json")
    if crash_after == 3:
        return trust
    for p in d.iterdir():
        if p.name.startswith(("checkpoint_", "tail_")) and cp["hash"] not in p.name:
            p.unlink()
    return trust


def load_state(directory, trust: dict | None = None):
    """Load (checkpoint, tail reports) of the state the trust record names. The record is
    read from the directory unless a trusted copy is given (the trust anchor kept outside
    the checked data). Every check of section 6 (4) refuses with CheckpointRefused or
    StoreCorrupted."""
    d = Path(directory)
    if trust is None:
        trust = json.loads((d / "trust.json").read_text())
    cp_path = d / f"checkpoint_{trust['checkpoint_hash']}.json"
    raw = cp_path.read_bytes()
    cp = json.loads(raw)
    check_checkpoint(cp, trust)
    if canonical(cp) != raw:
        raise CheckpointRefused("checkpoint file not canonical")
    tail, seal = read_tail(d / f"tail_{cp['hash']}.jsonl", cp["archive_seal"])
    if seal != trust["tail_seal"]:
        raise CheckpointRefused("tail seal differs from the trust record")
    if tail and tail[0]["report_day"] <= cp["cut"]:
        raise CheckpointRefused("tail starts inside the cut")
    if any(r["report_id"] <= (cp["highest_id"] or "") for r in tail):
        raise CheckpointRefused("tail report id at or below the checkpoint's highest id")
    return cp, tail
