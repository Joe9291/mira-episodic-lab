#!/usr/bin/env python3
"""Round 4.3 run (docs/ROUND_4_3.md, design v3 approved): source-bound consolidation,
model-free. One job runs the families given; collect_round43.py merges the jobs.

  --phase audit   R only (no H): the bound counts, the id contract, the informative cases of
                  the lossy controls (R on the control claim sets vs R on the full reports)
  --phase run     everything: M / R gold, Mode A, every cut (composition, full state, R on
                  the synthetic checkpoint, Mode T, source binding, controls), tamper,
                  interrupted writes, persistence and a rebuild in a new process, measures;
                  for the holdout only if the request's freeze matches

usage: run_round43.py --phase audit|run --split dev|holdout --families P1,P2 --request config/round43.json --out DIR
       run_round43.py --verify-process MANIFEST   (internal: the second process)
"""
from __future__ import annotations

import argparse
import collections
import copy
import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from episodic_lab import r43_consolidate as X  # noqa: E402
from episodic_lab import r43_reference as RF  # noqa: E402
from episodic_lab import r43_world as W  # noqa: E402
from episodic_lab.r40_memory import Memory, StoreCorrupted  # noqa: E402
from episodic_lab.r40_reference import reference_answers  # noqa: E402
from episodic_lab.r40_schema import ANCHOR_ATTRIBUTE, ANCHOR_PREFIX  # noqa: E402

CODE_FILES = ("episodic_lab/r43_consolidate.py", "episodic_lab/r43_reference.py", "episodic_lab/r43_world.py",
              "episodic_lab/r40_memory.py", "episodic_lab/r40_reference.py", "episodic_lab/r40_schema.py",
              "episodic_lab/r40_world.py", "episodic_lab/r41_world.py", "episodic_lab/rng.py",
              "bench/m3/run_round43.py", "bench/m3/collect_round43.py", "config/round43_counts.json",
              "tests/fixtures/r40_conformance.json")
CONTROLS = ("K1", "K2", "K3")
DIGEST_OPS = ("digest", "digest_at")
MAX_VIOLATIONS = 200


def code_hashes() -> dict:
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE_FILES}


def dumps(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def facts_of(pair):
    out = {tuple(pair["fact"])}
    if pair["anchor"] is not None:
        out.add((ANCHOR_PREFIX + pair["anchor"], ANCHOR_ATTRIBUTE))
    return out


def only(reports, facts):
    return [r for r in reports if (r["subject"], r["attribute"]) in facts]


def digest_time(q):
    return q["now"] if q["op"] == "digest" else q["t"]


def r_answers(reports, qs):
    """R's answers: the operators of round 4.0 through R's reference_answers, the digest
    through the reference digest (both on the reports given)."""
    plain = [q for q in qs if q["op"] not in DIGEST_OPS]
    out = reference_answers(reports, plain)[0] if plain else {}
    for q in qs:
        if q["op"] in DIGEST_OPS:
            out[q["qid"]] = RF.reference_digest(reports, q["subject"], q["attribute"], digest_time(q))
    return out


def h_answers(h, qs):
    return {q["qid"]: h.answer(q) for q in qs}


question_times = W.question_times


class Log:
    def __init__(self):
        self.count = collections.Counter()
        self.items = []

    def bad(self, rule, what):
        self.count[rule] += 1
        if len(self.items) < MAX_VIOLATIONS:
            self.items.append(f"{rule}: {what}")


# ------------------------------------------------------------------ source binding
def cited_value_ids(ans):
    """(id, digest entry or None) of every claim an answer cites as value evidence."""
    out = []
    if isinstance(ans, dict) and "segments" in ans:
        for s in ans["segments"]:
            for g in s["support"] + s["agree"]:
                out += [(e["id"], e) for e in g["claims"]]
            out += [(e["id"], e) for e in s["dissent"]]
        ans = ans["current"]
    if isinstance(ans, dict):
        out += [(i, None) for i in ans.get("ids", [])]
    elif isinstance(ans, list):
        for item in ans:
            if isinstance(item, dict):
                out += [(i, None) for i in item.get("ids", [])]
    return out


def check_partition(log, meas, where, q, ans, ref_at):
    """Design section 3: the claim entries of a digest (support, agree, dissent) are exactly
    the standing claims of the fact at the digest's knowledge time - complete, with equal
    fields, without duplicates (Astra's implementation review v1: checked in the full run)."""
    k = X.needed_time(q) if q["op"] == "digest_at" else q["now"]
    meas["digest_partition_checks"] += 1
    got = sorted((q["subject"], q["attribute"], e["id"], json.dumps(e["value"]), e["valid_from"], e["rank"],
                  e["source"], e["origin"]) for e in X.digest_entries(ans))
    want = [t for t in ref_at[k] if (t[0], t[1]) == (q["subject"], q["attribute"])]
    if got != want:
        log.bad("r5_digest_partition", f"{where} {q['qid']}")


def check_binding(log, where, q, ans, ref_at, tail_ids_days):
    k = X.needed_time(q) if q["op"] in ("believed_at", "digest_at") else q["now"]
    if q["op"] == "why_changed":
        if isinstance(ans, list):
            for i in ans:
                day = tail_ids_days.get(i)
                if day is None or not (q["k1"] < day <= q["k2"]):
                    log.bad("r5_binding", f"{where} {q['qid']} change evidence {i}")
        return
    ref = {t[2]: t for t in ref_at[k]}
    for i, entry in cited_value_ids(ans):
        t = ref.get(i)
        if t is None:
            log.bad("r5_binding", f"{where} {q['qid']} {i} not standing at {k}")
        elif entry is not None and (json.dumps(entry["value"]), entry["valid_from"], entry["rank"], entry["source"],
                                    entry["origin"]) != t[3:]:
            log.bad("r5_binding", f"{where} {q['qid']} {i} fields differ")


# ------------------------------------------------------------------ tamper and interrupted writes
def _rehash(cp):
    return X._seal_checkpoint(cp)


def tamper_cases(cp, tail, cp0, tail0, tmp):
    """Each case writes a correct state, alters it, and loads with the TRUSTED record (kept
    outside the directory). Claim cases use a checkpoint with claims (cp, tail); tail cases
    use the genesis checkpoint and the whole world as its tail (cp0, tail0: >= 2 reports
    in every world). Returns {case: detected?}."""
    out = {}

    def cp_file(d, c, trust):
        return d / f"checkpoint_{c['hash']}.json"

    def tail_file(d, c, trust):
        return d / X._tail_name(c["hash"], trust["tail_seal"])

    def attempt(name, mutate, base=None):
        c, t = base or (cp, tail)
        d = Path(tmp) / name
        trust = X.write_state(d, c, t)
        mutate(d, c, trust)
        try:
            X.load_state(d, trust=trust)
            out[name] = False
        except (X.CheckpointRefused, StoreCorrupted, json.JSONDecodeError, FileNotFoundError, KeyError):
            out[name] = True

    def edit_cp(fn, rehash):
        def m(d, base, trust):
            c = json.loads(cp_file(d, base, trust).read_text())
            fn(c)
            if rehash:
                c = _rehash(c)
            cp_file(d, base, trust).write_bytes(X.canonical(c))
        return m

    def first_claim(c):
        return c["facts"][0]["claims"][0]

    attempt("claim_value_changed", edit_cp(lambda c: first_claim(c).update(value="TAMPERED"), False))
    attempt("claim_value_changed_rehashed", edit_cp(lambda c: first_claim(c).update(value="TAMPERED"), True))
    attempt("claim_rank_changed_rehashed", edit_cp(lambda c: first_claim(c).update(rank=1 if first_claim(c)["rank"] != 1 else 3), True))
    attempt("claim_removed_rehashed", edit_cp(lambda c: c["facts"][0]["claims"].pop(), True))
    attempt("claim_added_rehashed", edit_cp(lambda c: c["facts"][0]["claims"].insert(0, dict(first_claim(c), id="r00000")), True))
    attempt("archive_seal_changed_rehashed", edit_cp(lambda c: c["archive_seal"].update(count=c["archive_seal"]["count"] + 1), True))
    attempt("parent_changed_rehashed", edit_cp(lambda c: c.update(parent="f" * 64), True))

    def edit_tail(fn):
        def m(d, base, trust):
            lines = tail_file(d, base, trust).read_text().splitlines()
            tail_file(d, base, trust).write_text("".join(x + "\n" for x in fn(lines)))
        return m

    def changed(lines):
        rec = json.loads(lines[0])
        rec["report"]["source"] = "tampered"
        return [json.dumps(rec, sort_keys=True)] + lines[1:]

    attempt("tail_record_changed", edit_tail(changed), (cp0, tail0))
    attempt("tail_record_removed", edit_tail(lambda ls: ls[:1] + ls[2:]), (cp0, tail0))
    attempt("tail_reordered", edit_tail(lambda ls: [ls[1], ls[0]] + ls[2:]), (cp0, tail0))
    attempt("tail_cut_off_at_end", edit_tail(lambda ls: ls[:-1]), (cp0, tail0))
    # a tail report id at or below the highest prefix id, written as a VALID chain with a
    # trust record that matches it: only the id rule can refuse it
    d = Path(tmp) / "tail_id_at_or_below_highest"
    bad_tail = [dict(tail[0], report_id=cp["highest_id"])] + tail[1:] if cp["highest_id"] else tail
    trust = X.write_state(d, cp, bad_tail)
    try:
        X.load_state(d, trust=trust)
        out["tail_id_at_or_below_highest"] = False
    except (X.CheckpointRefused, StoreCorrupted):
        out["tail_id_at_or_below_highest"] = True
    return out


def lost_fact_detected(cp, asked, ref_c):
    """Pass rule (8) negative test: drop the claims of one fact no question asks about,
    recompute the hash (internally consistent); the full-state comparison must find it.
    None if the checkpoint has no such fact."""
    others = [f for f in cp["facts"] if (f["subject"], f["attribute"]) not in asked]
    if not others:
        return None
    bad = copy.deepcopy(cp)
    bad["facts"] = [f for f in bad["facts"]
                    if (f["subject"], f["attribute"]) != (others[0]["subject"], others[0]["attribute"])]
    bad = _rehash(bad)
    X.check_checkpoint(bad, X.trust_record(bad, {"count": 0, "head": ""}))   # passes integrity
    return X.normalised(X.checkpoint_claims(bad)) != ref_c


def interrupted_writes(cp_a, tail_a, cp_b, tail_b, tmp):
    """Restart after an interrupted second write, through the EXTERNAL trusted record (the
    regular restart path; Astra's implementation review v1). Two scenarios: a new checkpoint
    (cp_b, tail_b), and the SAME checkpoint with a grown tail (cp_a, tail_a[:-1] -> tail_a).
    Per scenario: a crash after step 1 / 2 / 3 of write_state (the external record not yet
    committed) restarts on the old state; after the external commit, before and after
    finish_state, the restart gives the new state. 10 cases."""
    out = {}
    scenarios = {"new_checkpoint": ((cp_a, tail_a), (cp_b, tail_b)),
                 "same_checkpoint_grown_tail": ((cp_a, tail_a[:-1]), (cp_a, tail_a))}
    for name, ((c_old, t_old), (c_new, t_new)) in scenarios.items():
        for crash in (1, 2, 3, "committed", "finished"):
            d = Path(tmp) / f"{name}_{crash}"
            external = X.write_state(d, c_old, t_old)            # old state, committed externally
            X.finish_state(d, external)
            new = X.write_state(d, c_new, t_new, crash_after=crash if crash in (1, 2) else None)
            if crash in ("committed", "finished"):
                external = new                                  # the external commit
                if crash == "finished":
                    X.finish_state(d, external)
            try:
                cp, tail = X.load_state(d, trust=external)
            except (X.CheckpointRefused, StoreCorrupted, FileNotFoundError) as exc:  # noqa: F841
                out[f"{name}_crash_{crash}"] = False
                continue
            want = (c_old, t_old) if crash in (1, 2, 3) else (c_new, t_new)
            out[f"{name}_crash_{crash}"] = cp["hash"] == want[0]["hash"] and tail == want[1]
    return out


# ------------------------------------------------------------------ one world
def world_digest_update(h, pair, inst, world):
    w = inst[world]
    h.update(dumps([pair["pair"], inst["delay"], world, pair["ranks"], w["reports"], w["questions"], w["cuts"]]))


def gold_digest(split, families):
    """R's answers on every world of the families (for the freeze): {family: sha256}."""
    hs = {}
    for pair in W.iter_pairs(split):
        if pair["family"] not in families:
            continue
        h = hs.setdefault(pair["family"], {"worlds": hashlib.sha256(), "gold": hashlib.sha256()})
        for inst in pair["instances"]:
            for world in ("A", "B"):
                world_digest_update(h["worlds"], pair, inst, world)
                w = inst[world]
                h["gold"].update(dumps([pair["pair"], inst["delay"], world,
                                        r_answers(only(w["reports"], facts_of(pair)), w["questions"])]))
    return {f: {k: v.hexdigest() for k, v in d.items()} for f, d in hs.items()}


def run_instance(pair, inst, world, log, ctl, meas, persist_dir, manifest, digests):
    w = inst[world]
    reps, qs, cuts = w["reports"], w["questions"], w["cuts"]
    where0 = f"{pair['pair']} d{inst['delay']} {world}"
    asked = facts_of(pair)
    recs = X.chain_records(reps)
    m = Memory(reps)
    gold = {}
    for q in qs:
        fact = (q["subject"], q["attribute"])
        gold[q["qid"]] = X.full_digest(m, fact, digest_time(q)) if q["op"] in DIGEST_OPS else m.answer(q)
    r_full = r_answers(only(reps, asked), qs)
    world_digest_update(digests["worlds"], pair, inst, world)
    digests["gold"].update(dumps([pair["pair"], inst["delay"], world, r_full]))
    for q in qs:
        if r_full[q["qid"]] != gold[q["qid"]]:
            log.bad("r1_M_vs_R", f"{where0} {q['qid']}")
    times = question_times(qs)
    ref = RF.reference_state(reps, times | set(cuts))
    r_eff = RF.effectiveness(reps)
    # Mode A
    h_a, cps_a = X.mode_a(reps, recs)
    all_days = {r["report_id"]: r["report_day"] for r in reps}
    for q in qs:
        got = h_a.answer(q)
        if got != gold[q["qid"]]:
            log.bad("r1_modeA", f"{where0} {q['qid']}")
        check_binding(log, f"{where0} A", q, got, ref, all_days)
        if q["op"] in DIGEST_OPS:
            meas["digest_partition_checks_mode_a"] += 1
            check_partition(log, meas, f"{where0} A", q, got, ref)
    for loaded, applied, scanned in h_a.reads:
        meas["mode_a_claims_loaded"] += loaded
        meas["mode_a_reports_applied"] += applied
        meas["mode_a_reports_scanned"] += scanned
    for k in times:
        meas["state_checks_mode_a"] += 1
        if X.normalised(h_a.state_at(k)) != ref[k]:
            log.bad("r8_state", f"{where0} A k={k}")
    if h_a.effectiveness() != r_eff:
        log.bad("r5_binding", f"{where0} A effectiveness")
    # cuts
    parent, hashes = None, []
    for c in cuts:
        where = f"{where0} c={c}"
        cp = X.build_checkpoint(reps, recs, c) if parent is None else X.extend_checkpoint(parent, reps, recs, c)
        if X.canonical(X.build_checkpoint(reps, recs, c, cp["parent"])) != X.canonical(cp):
            log.bad("r3_composition", f"{where} incremental != scratch")
        if X.build_checkpoint(reps, recs, c)["facts"] != cp["facts"]:
            log.bad("r3_composition", f"{where} payload depends on the chain")
        meas["composition"] += parent is not None
        hashes.append(cp["hash"])
        parent = cp
        meas["state_checks_cut"] += 1
        if X.normalised(X.checkpoint_claims(cp)) != ref[c]:
            log.bad("r8_state", f"{where} checkpoint")
        if not X.verify_against_archive(cp, reps, recs):
            log.bad("r4_integrity", f"{where} verification")
        n = X.prefix_len(reps, c)
        tail = reps[n:]
        inscope = [q for q in qs if X.needed_time(q) >= c]
        # R on the checkpoint written as synthetic reports + the tail
        syn = RF.synthetic_reports([x for x in X.checkpoint_claims(cp) if (x["subject"], x["attribute"]) in asked], c)
        r_syn = r_answers(syn + only(tail, asked), inscope)
        for q in inscope:
            if r_syn[q["qid"]] != r_full[q["qid"]]:
                log.bad("r1_R_synthetic", f"{where} {q['qid']}")
        # Mode T
        h_t = X.mode_t(cp, reps, recs, X.trust_record(cp, X.seal_of(recs, len(reps))))
        tail_days = {r["report_id"]: r["report_day"] for r in tail}
        for q in qs:
            meas["mode_t_evaluations"] += 1
            got = h_t.answer(q)
            if X.needed_time(q) < c:
                if got != ("compacted" if q["op"] == "why_changed" else X.COMPACTED):
                    log.bad("r2_modeT", f"{where} {q['qid']} not compacted")
            else:
                if got != gold[q["qid"]]:
                    log.bad("r2_modeT", f"{where} {q['qid']}")
                check_binding(log, f"{where} T", q, got, ref, tail_days)
                if q["op"] in DIGEST_OPS:
                    meas["digest_partition_checks_mode_t"] += 1
                    check_partition(log, meas, f"{where} T", q, got, ref)
        for k in times:
            if k >= c:
                meas["state_checks_mode_t"] += 1
                if X.normalised(h_t.state_at(k)) != ref[k]:
                    log.bad("r8_state", f"{where} T k={k}")
        eff_t = h_t.effectiveness()
        if eff_t != {r["report_id"]: r_eff[r["report_id"]] for r in tail if r["kind"] != "assert"}:
            log.bad("r5_binding", f"{where} T effectiveness")
        cp_ids = {x["id"] for x in X.checkpoint_claims(cp)} | {r["report_id"] for r in tail}
        for r in tail:
            if r["kind"] != "assert" and eff_t.get(r["report_id"]) and r["target_report_id"] not in cp_ids:
                log.bad("r5_binding", f"{where} effective target outside C and tail")
        # lossy controls (test path)
        for kind in CONTROLS:
            claims = [x for x in RF.control_claims(reps, c, kind) if (x["subject"], x["attribute"]) in asked]
            r_k = r_answers(RF.synthetic_reports(claims, c) + only(tail, asked), inscope)
            h_k = X.control_memory(claims, c, reps)
            for q in inscope:
                got = h_k.answer(q)
                if got != r_k[q["qid"]]:
                    log.bad("r6_controls", f"{where} {kind} {q['qid']} H != R")
                if r_k[q["qid"]] != gold[q["qid"]]:
                    ctl[kind].append((pair["pair"], pair["family"], q["op"]))
        # measures
        meas["claims"] += sum(len(f["claims"]) for f in cp["facts"])
        meas["prefix_reports"] += n
        meas["checkpoint_bytes"] += len(X.canonical(cp))
        meas["prefix_bytes"] += len(dumps(reps[:n]))
        meas["checkpoint_gzip"] += len(gzip.compress(X.canonical(cp), mtime=0))
        meas["prefix_gzip"] += len(gzip.compress(dumps(reps[:n]), mtime=0))
    # integrity, interrupted writes, persistence at the first cut with claims and a tail
    usable = [c for c in cuts if c > 0 and len(reps) - X.prefix_len(reps, c) >= 1]
    chosen = None
    for c in usable:
        cp = X.build_checkpoint(reps, recs, c)
        if cp["facts"]:
            chosen = cp
            break
    if chosen is None:
        log.bad("r4_integrity", f"{where0} no cut usable for the tamper cases")
        return hashes
    tail = reps[X.prefix_len(reps, chosen["cut"]):]
    with tempfile.TemporaryDirectory() as tmp:
        for name, ok in tamper_cases(chosen, tail, X.build_checkpoint(reps, recs, 0), reps, tmp).items():
            meas["tamper_cases"] += 1
            if not ok:
                log.bad("r4_integrity", f"{where0} tamper {name} not detected")
        later = [c for c in cuts if c > chosen["cut"]]
        cp_b = X.extend_checkpoint(chosen, reps, recs, later[0]) if later else chosen
        tail_b = reps[X.prefix_len(reps, cp_b["cut"]):]
        for name, ok in interrupted_writes(chosen, tail, cp_b, tail_b, tmp).items():
            meas["interrupted_cases"] += 1
            if not ok:
                log.bad("r4_interrupted", f"{where0} {name}")
    cp_now = X.build_checkpoint(reps, recs, cuts[-1])                 # the cut "now": distractors present
    lost = lost_fact_detected(cp_now, asked, ref[cuts[-1]])
    if lost is not None:
        meas["lost_fact_tests"] += 1
        if not lost:
            log.bad("r8_state", f"{where0} lost unasked fact not detected")
    d = Path(persist_dir) / f"{pair['pair']}_{inst['delay']}_{world}"
    trust = X.write_state(d, chosen, tail)
    h = X.Hot({chosen["cut"]: chosen}, tail, floor=chosen["cut"], highest_id=chosen["highest_id"])
    manifest.append({"pair": pair["pair"], "delay": inst["delay"], "world": world, "dir": str(d), "trust": trust,
                     "questions": qs, "answers_sha256": hashlib.sha256(dumps([h.answer(q) for q in qs])).hexdigest(),
                     "chain_hashes": hashes})
    return hashes


# ------------------------------------------------------------------ the second process
def verify_process(manifest_path):
    """Reload every persisted state (trust copy from the manifest), answer, and rebuild every
    checkpoint chain from the regenerated worlds."""
    man = json.loads(Path(manifest_path).read_text())
    out = {"answers": {}, "chains": {}}
    want = {(x["pair"], x["delay"], x["world"]) for x in man["items"]}
    for item in man["items"]:
        cp, tail = X.load_state(item["dir"], trust=item["trust"])
        h = X.Hot({cp["cut"]: cp}, tail, floor=cp["cut"], highest_id=cp["highest_id"])
        out["answers"][f"{item['pair']}|{item['delay']}|{item['world']}"] = \
            hashlib.sha256(dumps([h.answer(q) for q in item["questions"]])).hexdigest()
    fams = set(man["families"])
    for pair in W.iter_pairs(man["split"]):
        if pair["family"] not in fams:
            continue
        for inst in pair["instances"]:
            for world in ("A", "B"):
                if (pair["pair"], inst["delay"], world) not in want:
                    continue
                reps = inst[world]["reports"]
                recs = X.chain_records(reps)
                parent, hs = None, []
                for c in inst[world]["cuts"]:
                    parent = X.build_checkpoint(reps, recs, c) if parent is None else \
                        X.extend_checkpoint(parent, reps, recs, c)
                    hs.append(parent["hash"])
                out["chains"][f"{pair['pair']}|{inst['delay']}|{world}"] = hs
    print(json.dumps(out))


# ------------------------------------------------------------------ conformance
def conformance(log):
    d = json.loads((ROOT / "tests/fixtures/r40_conformance.json").read_text())
    fields = ("report_id", "report_day", "source", "rank", "subject", "attribute", "kind", "value", "valid_from",
              "target_report_id")
    n = 0
    for name, w in d["worlds"].items():
        reps = sorted((dict(zip(fields, row), origin="o-" + row[0]) for row in w["reports"]),
                      key=lambda r: (r["report_day"], r["report_id"]))
        recs = X.chain_records(reps)
        qs = [dict(c[1], qid=c[0], subject="key", attribute="loc") for c in w["checks"]]
        exp = {c[0]: c[2] for c in w["checks"]}
        h_a, _ = X.mode_a(reps, recs)
        for q in qs:
            n += 1
            if h_a.answer(q) != exp[q["qid"]]:
                log.bad("r7_conformance", f"{name} {q['qid']} A")
        last = max(r["report_day"] for r in reps)
        parent = None
        for c in range(0, last + 2):
            parent = X.build_checkpoint(reps, recs, c) if parent is None else X.extend_checkpoint(parent, reps, recs, c)
            h_t = X.mode_t(parent, reps, recs, X.trust_record(parent, X.seal_of(recs, len(reps))))
            for q in qs:
                n += 1
                got = h_t.answer(q)
                want = exp[q["qid"]] if X.needed_time(q) >= c else ("compacted" if q["op"] == "why_changed"
                                                                    else X.COMPACTED)
                if got != want:
                    log.bad("r7_conformance", f"{name} {q['qid']} T c={c}")
    return n


# ------------------------------------------------------------------ audit (R only)
def audit(split, families):
    counts = {}
    ctl = {k: [] for k in CONTROLS}
    contract, collisions, cross = 0, 0, 0
    ids_all = set()
    for pair in W.iter_pairs(split):
        if pair["family"] not in families:
            continue
        f = counts.setdefault(pair["family"], dict({k: 0 for k in W.COUNT_KEYS}, pairs=0, instances=0,
                                                   by_operator=collections.Counter()))
        f["pairs"] += 1
        asked = facts_of(pair)
        for inst in pair["instances"]:
            for world in ("A", "B"):
                w = inst[world]
                reps, qs = w["reports"], w["questions"]
                f["instances"] += 1
                for k, v in W.instance_counts(w).items():
                    f[k] += v
                for q in qs:
                    f["by_operator"][q["op"]] += 1
                contract += not W.ids_monotonic(reps)
                fact_of = {r["report_id"]: (r["subject"], r["attribute"]) for r in reps}
                cross += sum(1 for r in reps if r["target_report_id"] and r["target_report_id"] in fact_of
                             and fact_of[r["target_report_id"]] != (r["subject"], r["attribute"]))
                ids = {r["report_id"] for r in reps}
                ids_all |= ids
                collisions += any(f"r{99999 - int(i[1:]):05d}" in ids for i in ids)
                r_full = r_answers(only(reps, asked), qs)
                for c in w["cuts"]:
                    tail = reps[X.prefix_len(reps, c):]
                    inscope = [q for q in qs if X.needed_time(q) >= c]
                    for kind in CONTROLS:
                        claims = [x for x in RF.control_claims(reps, c, kind) if (x["subject"], x["attribute"]) in asked]
                        r_k = r_answers(RF.synthetic_reports(claims, c) + only(tail, asked), inscope)
                        ctl[kind] += [(pair["pair"], pair["family"], q["op"]) for q in inscope
                                      if r_k[q["qid"]] != r_full[q["qid"]]]
    for f in counts.values():
        f["by_operator"] = dict(sorted(f["by_operator"].items()))
    return {"counts": counts, "id_contract_violations": contract, "k3_collisions": collisions,
            "cross_fact_targets": cross,
            "controls": summarize_controls(ctl)}


def summarize_controls(ctl):
    return {k: {"informative": len(v), "pairs": len({x[0] for x in v}), "families": sorted({x[1] for x in v}),
                "operators": dict(collections.Counter(x[2] for x in v))} for k, v in ctl.items()}


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("audit", "run"))
    ap.add_argument("--split", choices=("dev", "holdout"))
    ap.add_argument("--families", default=",".join(W.FAMILIES))
    ap.add_argument("--request", default="config/round43.json")
    ap.add_argument("--conformance", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--verify-process")
    a = ap.parse_args()
    if a.verify_process:
        verify_process(a.verify_process)
        return 0
    fams = [f for f in a.families.split(",") if f]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    res = {"schema": "episodic_lab.round43_job.v1", "phase": a.phase, "split": a.split, "families": fams,
           "generator": W.GENERATOR_VERSION, "code": code_hashes(), "status": "ERROR"}
    try:
        if a.phase == "audit":
            res.update(audit(a.split, set(fams)))
        else:
            req = json.loads(Path(a.request).read_text())
            if a.split == "holdout":
                fr = req.get("freeze") or {}
                if fr.get("code") != res["code"]:
                    raise RuntimeError("holdout refused: the code differs from the freeze in the request")
                pre = {}
                for pair in W.iter_pairs(a.split):           # worlds checked BEFORE any run of H
                    if pair["family"] in fams:
                        h = pre.setdefault(pair["family"], hashlib.sha256())
                        for inst in pair["instances"]:
                            for world in ("A", "B"):
                                world_digest_update(h, pair, inst, world)
                if {f: h.hexdigest() for f, h in pre.items()} != {f: fr["families"][f]["worlds"] for f in fams}:
                    raise RuntimeError("holdout refused: the worlds differ from the freeze")
            log, ctl = Log(), {k: [] for k in CONTROLS}
            meas = collections.Counter()
            manifest = []
            persist = Path(tempfile.mkdtemp(prefix="r43_persist_"))
            counts, digests = {}, {}
            for pair in W.iter_pairs(a.split):
                if pair["family"] not in fams:
                    continue
                dg = digests.setdefault(pair["family"], {"worlds": hashlib.sha256(), "gold": hashlib.sha256()})
                f = counts.setdefault(pair["family"], dict({k: 0 for k in W.COUNT_KEYS}, pairs=0, instances=0,
                                                           by_operator=collections.Counter()))
                f["pairs"] += 1
                for inst in pair["instances"]:
                    for world in ("A", "B"):
                        w = inst[world]
                        f["instances"] += 1
                        for k, v in W.instance_counts(w).items():
                            f[k] += v
                        for q in w["questions"]:
                            f["by_operator"][q["op"]] += 1
                        meas["mode_a_answers"] += len(w["questions"])
                        run_instance(pair, inst, world, log, ctl, meas, persist, manifest, dg)
            for f in counts.values():
                f["by_operator"] = dict(sorted(f["by_operator"].items()))
            mpath = persist / "manifest.json"
            mpath.write_text(json.dumps({"split": a.split, "families": fams, "items": manifest}))
            proc = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--verify-process", str(mpath)],
                                  capture_output=True, text=True, check=True)
            second = json.loads(proc.stdout)
            import shutil
            shutil.rmtree(persist, ignore_errors=True)
            for item in manifest:
                key = f"{item['pair']}|{item['delay']}|{item['world']}"
                meas["persistence_checks"] += 1
                if second["answers"].get(key) != item["answers_sha256"]:
                    log.bad("r4_persistence", f"{key} answers after reload")
                if second["chains"].get(key) != item["chain_hashes"]:
                    log.bad("r3_composition", f"{key} chain rebuilt in a new process")
            conf_n = conformance(log) if a.conformance else 0
            res.update(digests={f: {k: v.hexdigest() for k, v in d.items()} for f, d in digests.items()},
                       counts=counts, violations=dict(log.count), violation_items=log.items,
                       controls=summarize_controls(ctl), measures=dict(meas), conformance_checks=conf_n)
        res["status"] = "OK"
    except Exception as exc:  # noqa: BLE001
        import traceback
        res["error"] = f"{type(exc).__name__}: {exc}"
        res["traceback"] = traceback.format_exc()[-4000:]
    res["seconds"] = round(time.perf_counter() - t0, 1)
    name = f"r43_{a.phase}_{a.split}_{'-'.join(fams)}.json"
    (out / name).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: res.get(k) for k in ("status", "error", "violations", "controls", "measures", "seconds")},
                     indent=1, default=str)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
