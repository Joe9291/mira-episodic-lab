#!/usr/bin/env python3
"""Round 4.0 phase A run (docs/ROUND_4_0.md): structured reports, model-free.

Pass 1 generates the split and lets the independent reference R compute every expected
answer (original worlds and every counterfactual world); for the holdout these and the
code are compared with the freeze in the request BEFORE M runs. Pass 2 regenerates the
split and runs M, the baselines S0-S4, the generator audit, the pair conditions, the
B-indistinguishability marks, the interventions and the persistence test (a separate
process reloads every store). The conformance set runs on M and R. Writes results.json,
rows.jsonl, interventions.jsonl, indist_log.jsonl, SUMMARY.md and VERDICT.

usage: run_round40.py --split dev|holdout --request config/round40.json --out DIR
       run_round40.py --persist-check MANIFEST   (internal: the reload process)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from episodic_lab import r40_analysis as A  # noqa: E402
from episodic_lab import r40_baselines as B  # noqa: E402
from episodic_lab import r40_world as W  # noqa: E402
from episodic_lab.r40_memory import Memory, ReportStore  # noqa: E402
from episodic_lab.r40_reference import reference_answers  # noqa: E402
from episodic_lab.r40_schema import ANCHOR_ATTRIBUTE, ANCHOR_PREFIX  # noqa: E402

CODE_FILES = ("episodic_lab/r40_schema.py", "episodic_lab/r40_memory.py",
              "episodic_lab/r40_reference.py", "episodic_lab/r40_baselines.py",
              "episodic_lab/r40_world.py", "episodic_lab/r40_analysis.py", "episodic_lab/rng.py",
              "episodic_lab/world.py", "bench/m3/run_round40.py",
              "tests/fixtures/r40_conformance.json")
RESULT_SCHEMA = "episodic_lab.round40_result.v1"
SYSTEMS = ("M",) + B.SYSTEMS


def code_hashes() -> dict:
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE_FILES}


def dumps(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


class Phase:
    """Wall time and the largest additional traced memory of one kind of work."""

    def __init__(self):
        self.seconds = 0.0
        self.peak = 0

    def run(self, fn, *a, **k):
        base = tracemalloc.get_traced_memory()[0]
        tracemalloc.reset_peak()
        t = time.perf_counter()
        out = fn(*a, **k)
        self.seconds += time.perf_counter() - t
        self.peak = max(self.peak, tracemalloc.get_traced_memory()[1] - base)
        return out

    def report(self):
        return {"seconds": round(self.seconds, 2), "peak_extra_mb": round(self.peak / 2**20, 2)}


def helper_questions(fact, anchor, now):
    hq = [{"qid": "__hist", "op": "history", "subject": fact[0], "attribute": fact[1], "now": now}]
    if anchor is not None:
        hq.append({"qid": "__ahist", "op": "history", "subject": ANCHOR_PREFIX + anchor,
                   "attribute": ANCHOR_ATTRIBUTE, "now": now})
    return hq


def run_reference(reports, qs, fact, anchor, now):
    gold, aux, past = reference_answers(reports, qs + helper_questions(fact, anchor, now),
                                        track_current=[tuple(fact)])
    return gold, aux, past[tuple(fact)]


def applicable(fam):
    return [k for k, fams in W.INTERVENTIONS.items() if fam in fams]


# ------------------------------------------------------------------ pass 1: R
def pass_reference(split, phases):
    h = {k: hashlib.sha256() for k in ("worlds", "questions", "gold", "interventions")}
    store = {}
    for pair in W.iter_pairs(split):
        for inst in pair["instances"]:
            for world in ("A", "B"):
                w = inst[world]
                h["worlds"].update(dumps([pair["pair"], inst["delay"], world, pair["ranks"], w["reports"]]))
                h["questions"].update(dumps(w["questions"]))
                gold, aux, past = phases["R"].run(run_reference, w["reports"], w["questions"],
                                                  pair["fact"], pair["anchor"], inst["now"])
                h["gold"].update(dumps([pair["pair"], inst["delay"], world, gold]))
                store[(pair["pair"], inst["delay"], world)] = (gold, aux, past)
            for kind in applicable(pair["family"]):
                cf = W.counterfactual(pair, inst, kind)
                if cf is None:
                    continue
                gold, _, _ = phases["R_interventions"].run(
                    run_reference, cf["reports"], inst["A"]["questions"], pair["fact"],
                    pair["anchor"], inst["now"])
                h["interventions"].update(dumps([pair["pair"], inst["delay"], kind, cf, gold]))
                store[(pair["pair"], inst["delay"], kind)] = (gold, None, None)
    return store, {k: v.hexdigest() for k, v in h.items()}


# ------------------------------------------------------------------ conformance
def conformance():
    path = ROOT / "tests/fixtures/r40_conformance.json"
    d = json.loads(path.read_text())
    fields = ("report_id", "report_day", "source", "rank", "subject", "attribute", "kind",
              "value", "valid_from", "target_report_id")
    results = []
    for name, w in d["worlds"].items():
        reps = sorted((dict(zip(fields, row), origin="o-" + row[0]) for row in w["reports"]),
                      key=lambda r: (r["report_day"], r["report_id"]))
        by_id = {r["report_id"]: r for r in reps}
        m = Memory(reps)
        qs = [dict(c[1], qid=c[0], subject="key", attribute="loc") for c in w["checks"]]
        r_gold = reference_answers(reps, qs)[0]
        for c, q in zip(w["checks"], qs):
            got_m = m.answer(q)
            ok = got_m == c[2] and r_gold[q["qid"]] == c[2]
            if len(c) > 3:
                prov = [[i, by_id[i]["source"], by_id[i]["rank"]] for i in got_m.get("ids", [])]
                ok = ok and prov == c[3]
            results.append({"case": c[0], "world": name, "ok": ok, "M": got_m, "R": r_gold[q["qid"]]})
        for c in w.get("interventions", []):
            cf, removed = W.remove_with_cascade(reps, c[1]["remove"])
            q = dict(c[3], qid=c[0], subject="key", attribute="loc")
            got_m, got_r = Memory(cf).answer(q), reference_answers(cf, [q])[0][c[0]]
            ok = removed == c[2] and got_m == c[4] and got_r == c[4]
            results.append({"case": c[0], "world": name, "ok": ok, "M": got_m, "R": got_r,
                            "removed": removed})
    return results


# ------------------------------------------------------------------ persistence
def persist_check(manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    out = {}
    for item in manifest:
        store = ReportStore(item["path"], expect=item["seal"])
        m = Memory(store.reports)
        out[item["path"]] = hashlib.sha256(dumps([m.answer(q) for q in item["questions"]])).hexdigest()
    print(json.dumps(out))


# ------------------------------------------------------------------ pass 2
def evaluate(split, store, phases, tmpdir):
    rows, iv_rows, indist_log, violations, persist = [], [], [], [], []
    indist = {(s, f): set() for s in B.SYSTEMS for f in W.FAMILIES}
    state_breaks = []
    for pair in W.iter_pairs(split):
        fam, pid = pair["family"], pair["pair"]
        for inst in pair["instances"]:
            delay, now = inst["delay"], inst["now"]
            per_world = {}
            for world in ("A", "B"):
                w = inst[world]
                gold, aux, past = store[(pid, delay, world)]
                ctx = {"hist": gold["__hist"], "anchor_hist": gold.get("__ahist", [])}
                mem = phases["M"].run(Memory, w["reports"])
                m_ans = phases["M"].run(lambda: {q["qid"]: mem.answer(q) for q in w["questions"]})
                b_ans, b_state = phases["baselines"].run(lambda: (
                    {s: {q["qid"]: B.ANSWER[s](w["reports"], q, ctx) for q in w["questions"]} for s in B.SYSTEMS},
                    {s: {q["qid"]: B.STATE[s](w["reports"], q, ctx) for q in w["questions"]} for s in B.SYSTEMS}))
                for v in phases["audit"].run(W.audit_world, w["reports"], pair["ranks"], pair["anchor"],
                                             pair["fact"], True):
                    violations.append(f"{pid} d{delay} {world}: {v}")
                truth = pair["truth"][world]
                for q in w["questions"]:
                    g = gold[q["qid"]]
                    row = {"qid": q["qid"], "pair": pid, "family": fam, "op": q["op"],
                           "delay": delay, "world": world, "gold": g, "M": m_ans[q["qid"]],
                           "M_equals_R": m_ans[q["qid"]] == g}
                    for s in SYSTEMS:
                        ans = m_ans[q["qid"]] if s == "M" else b_ans[s][q["qid"]]
                        row[f"hit_{s}"] = A.hit(q["op"], g, ans)
                    if q["op"] in A.VALUE_OPS:
                        row["false_conflict_den"] = g["status"] != "conflict"
                        for s in SYSTEMS:
                            ans = m_ans[q["qid"]] if s == "M" else b_ans[s][q["qid"]]
                            row[f"conflict_out_{s}"] = isinstance(ans, dict) and ans.get("status") == "conflict"
                        ca = A.clean_and_agree(q, g, aux.get(q["qid"]), truth, pair["anchor_day"])
                        row["clean"], row["truth_agree"] = ca
                    if q["op"] == "current":
                        old = A.outdated_values(past, g)
                        row["stale_den"] = bool(old)
                        for s in SYSTEMS:
                            ans = m_ans[q["qid"]] if s == "M" else b_ans[s][q["qid"]]
                            row[f"stale_{s}"] = bool(old) and isinstance(ans, dict) \
                                and ans.get("status") == "value" and ans.get("value") in old
                    rows.append(row)
                per_world[world] = (gold, b_ans, b_state)
                path = Path(tmpdir) / f"{pid}_{delay}_{world}.jsonl"
                st = ReportStore(path)
                phases["persist_write"].run(st.extend, w["reports"])
                persist.append({"path": str(path), "seal": st.seal(), "questions": w["questions"],
                                "expect": hashlib.sha256(dumps([m_ans[q["qid"]] for q in w["questions"]])).hexdigest()})
            # pair controls and phenomenon conditions
            ra, rb = inst["A"]["reports"], inst["B"]["reports"]
            diff = [x["report_id"] for x, y in zip(ra, rb) if x != y]
            if len(ra) != len(rb) or [x["report_day"] for x in ra] != [y["report_day"] for y in rb] \
                    or [x["report_id"] for x in ra] != [y["report_id"] for y in rb] or diff != [inst["crit_id"]]:
                violations.append(f"{pid} d{delay}: pair control (only the critical report may differ): {diff}")
            qa = [{k: v for k, v in q.items() if k != "qid"} for q in inst["A"]["questions"]]
            qb = [{k: v for k, v in q.items() if k != "qid"} for q in inst["B"]["questions"]]
            if qa != qb:
                violations.append(f"{pid} d{delay}: questions differ between A and B")
            gA, gB = per_world["A"][0], per_world["B"][0]
            crit_a = next(r for r in ra if r["report_id"] == inst["crit_id"])
            crit_b = next(r for r in rb if r["report_id"] == inst["crit_id"])
            for v in A.pair_conditions(fam, gA, gB, inst["A"]["questions"], crit_a, crit_b,
                                       gA["__hist"], gB["__hist"]):
                violations.append(f"{pid} d{delay}: {v}")
            # B-indistinguishable pairs
            for s in B.SYSTEMS:
                for qA, qB in zip(inst["A"]["questions"], inst["B"]["questions"]):
                    stA, stB = per_world["A"][2][s][qA["qid"]], per_world["B"][2][s][qB["qid"]]
                    if stA != stB:
                        continue
                    ansA, ansB = per_world["A"][1][s][qA["qid"]], per_world["B"][1][s][qB["qid"]]
                    if ansA != ansB:
                        state_breaks.append(f"{s} {qA['qid']}: equal state, different answers")
                    if not A.hit(qA["op"], gA[qA["qid"]], gB[qB["qid"]]):
                        if pid not in indist[(s, fam)]:
                            indist_log.append({"system": s, "pair": pid, "delay": delay, "question": qA,
                                               "state": repr(stA), "gold_A": gA[qA["qid"]],
                                               "gold_B": gB[qB["qid"]]})
                        indist[(s, fam)].add(pid)
            # interventions
            for kind in applicable(fam):
                cf = W.counterfactual(pair, inst, kind)
                if cf is None:
                    continue
                for v in W.audit_world(cf["reports"], cf["ranks"], pair["anchor"], pair["fact"], False):
                    violations.append(f"{pid} d{delay} {kind}: {v}")
                cf_gold = store[(pid, delay, kind)][0]
                mem = phases["M_interventions"].run(Memory, cf["reports"])
                m_cf = {q["qid"]: mem.answer(q) for q in inst["A"]["questions"]}
                qs = inst["A"]["questions"]
                informative = any(not A.hit(q["op"], gA[q["qid"]], cf_gold[q["qid"]]) for q in qs)
                unchanged = all(gA[q["qid"]] == cf_gold[q["qid"]] for q in qs)
                iv_rows.append({"pair": pid, "family": fam, "delay": delay, "kind": kind,
                                "note": cf["note"], "removed": cf["removed"],
                                "informative": informative, "unchanged": unchanged,
                                "M_equals_R": all(m_cf[q["qid"]] == cf_gold[q["qid"]] for q in qs),
                                "R": {q["qid"]: cf_gold[q["qid"]] for q in qs},
                                "M": {q["qid"]: m_cf[q["qid"]] for q in qs}})
    return rows, iv_rows, indist, indist_log, violations, persist, state_breaks


def run_persistence(persist, tmpdir, phases):
    manifest = Path(tmpdir) / "manifest.json"
    manifest.write_text(json.dumps([{k: v for k, v in p.items() if k != "expect"} for p in persist]))
    t = time.perf_counter()
    proc = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--persist-check",
                           str(manifest)], capture_output=True, text=True, timeout=3600)
    phases["persist_reload"].seconds += time.perf_counter() - t
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr[-2000:], "stores": len(persist)}
    got = json.loads(proc.stdout)
    bad = [p["path"] for p in persist if got.get(p["path"]) != p["expect"]]
    return {"ok": not bad and len(got) == len(persist), "stores": len(persist), "mismatches": bad[:20]}


# ------------------------------------------------------------------ summary
def summarize(split, rows, iv_rows, indist, violations, persist_res, conf, state_breaks):
    def rate(sel, key):
        sel = list(sel)
        return {"right": sum(1 for r in sel if r[key]), "n": len(sel)}
    out = {"systems": {}, "cells": {}, "pairs": {}}
    for s in SYSTEMS:
        out["systems"][s] = {
            "answers": rate(rows, f"hit_{s}"),
            "stale": {"stale": sum(1 for r in rows if r.get(f"stale_{s}")),
                      "denominator": sum(1 for r in rows if r.get("stale_den"))},
            "false_conflicts": {"conflict_outputs": sum(1 for r in rows if r.get("false_conflict_den") and r.get(f"conflict_out_{s}")),
                                "denominator": sum(1 for r in rows if r.get("false_conflict_den"))},
        }
        fams = {}
        for f in W.FAMILIES:
            pids = sorted({r["pair"] for r in rows if r["family"] == f})
            ok = [p for p in pids if all(r[f"hit_{s}"] for r in rows if r["pair"] == p)]
            fams[f] = {"pairs_right": len(ok), "pairs": len(pids)}
        out["pairs"][s] = fams
    for r in rows:
        key = f"{r['family']}|{r['op']}|{r['delay']}"
        c = out["cells"].setdefault(key, {"n": 0, **{s: 0 for s in SYSTEMS}})
        c["n"] += 1
        for s in SYSTEMS:
            c[s] += int(r[f"hit_{s}"])
    out["value_outputs"] = {who: {k: sum(1 for r in rows if r["op"] in A.VALUE_OPS and r[who]["status"] == k)
                                  for k in ("value", "conflict", "unknown")} for who in ("gold", "M")}
    clean = [r for r in rows if r.get("clean")]
    out["truth_measure"] = {"clean_questions": len(clean),
                            "policy_agrees_with_truth": sum(1 for r in clean if r["truth_agree"]),
                            "value_questions": sum(1 for r in rows if "clean" in r)}
    need = A.min_pairs(split)
    out["indistinguishable"] = {f"{s}|{f}": len(v) for (s, f), v in sorted(indist.items())}
    out["required_cells"] = {f"{s}|{f}": {"pairs": len(indist[(s, f)]), "required": need,
                                          "ok": len(indist[(s, f)]) >= need}
                             for s, fams in A.REQUIRED_CELLS.items() for f in fams}
    ivs = {}
    for kind in W.INTERVENTIONS:
        sel = [r for r in iv_rows if r["kind"] == kind]
        d0 = [r for r in sel if r["delay"] == 0]
        ivs[kind] = {"cases": len(sel), "pairs_at_delay_0": len(d0),
                     "informative_pairs_at_delay_0": sum(1 for r in d0 if r["informative"]),
                     "M_equals_R": sum(1 for r in sel if r["M_equals_R"]),
                     "unchanged": sum(1 for r in sel if r["unchanged"]),
                     "removed_more_than_one": sum(1 for r in sel if len(r["removed"]) > 1)}
    out["interventions"] = ivs
    m_errors = [r["qid"] for r in rows if not r["hit_M"]]
    m_vs_r = [r["qid"] for r in rows if not r["M_equals_R"]]
    criteria = {
        "M_zero_errors": not m_errors,
        "conformance_100": all(c["ok"] for c in conf),
        "M_equals_R_everywhere": not m_vs_r and all(r["M_equals_R"] for r in iv_rows),
        "interventions_as_predicted": all(r["M_equals_R"] for r in iv_rows)
            and all(v["informative_pairs_at_delay_0"] >= need for k, v in ivs.items() if k != "irrelevant_control")
            and ivs["irrelevant_control"]["unchanged"] == ivs["irrelevant_control"]["cases"] > 0,
        "persistence": persist_res["ok"],
        "audit_clean": not violations and not state_breaks,
        "required_cells_filled": all(v["ok"] for v in out["required_cells"].values()),
    }
    out.update(criteria=criteria, M_errors=m_errors[:50], M_vs_R=m_vs_r[:50],
               violations=violations[:50], n_violations=len(violations), state_breaks=state_breaks[:20],
               conformance={"cases": len(conf), "ok": sum(1 for c in conf if c["ok"]),
                            "failed": [c for c in conf if not c["ok"]][:10]},
               persistence=persist_res, min_pairs=need)
    return out


def write_summary(path, res):
    s = res["summary"]
    lines = [f"# Round 4.0 phase A - {res['split']} (attempt {res['attempt']}{', repeat' if res['repeat_of'] else ''})", "",
             f"Verdict: **{res['verdict']}**", "", "| criterion | ok |", "|---|---|"]
    lines += [f"| {k} | {'yes' if v else 'NO'} |" for k, v in s["criteria"].items()]
    lines += ["", "| system | answers right | stale / den. | false conflicts / den. |", "|---|---|---|---|"]
    for k, v in s["systems"].items():
        lines.append(f"| {k} | {v['answers']['right']}/{v['answers']['n']} | {v['stale']['stale']}/{v['stale']['denominator']} | "
                     f"{v['false_conflicts']['conflict_outputs']}/{v['false_conflicts']['denominator']} |")
    lines += ["", "Pairs right (all answers of both worlds at all four delays):", "",
              "| system | " + " | ".join(W.FAMILIES) + " |", "|---|" + "---|" * len(W.FAMILIES)]
    for k, fams in s["pairs"].items():
        lines.append(f"| {k} | " + " | ".join(f"{fams[f]['pairs_right']}/{fams[f]['pairs']}" for f in W.FAMILIES) + " |")
    lines += ["", f"Required B-indistinguishable cells (min {s['min_pairs']} pairs):", ""]
    lines += [f"- {k}: {v['pairs']}" + ("" if v["ok"] else " (TOO FEW)") for k, v in s["required_cells"].items()]
    lines += ["", "| intervention | cases | informative pairs (delay 0) | M = R | unchanged | cascades |", "|---|---|---|---|---|---|"]
    for k, v in s["interventions"].items():
        lines.append(f"| {k} | {v['cases']} | {v['informative_pairs_at_delay_0']}/{v['pairs_at_delay_0']} | {v['M_equals_R']} | {v['unchanged']} | {v['removed_more_than_one']} |")
    tm = s["truth_measure"]
    lines += ["", f"Truth (measurement only): clean report state in {tm['clean_questions']} of {tm['value_questions']} value questions; "
              f"policy answer = world truth in {tm['policy_agrees_with_truth']} of them.",
              f"Conformance: {s['conformance']['ok']}/{s['conformance']['cases']}. Persistence: {s['persistence']['stores']} stores, ok = {s['persistence']['ok']}. "
              f"Audit violations: {s['n_violations']}.", "", "Resources:", ""]
    lines += [f"- {k}: {v['seconds']} s, peak +{v['peak_extra_mb']} MB" for k, v in res["resources"].items()]
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("dev", "holdout"))
    ap.add_argument("--request")
    ap.add_argument("--out")
    ap.add_argument("--persist-check")
    a = ap.parse_args()
    if a.persist_check:
        persist_check(a.persist_check)
        return 0
    req = json.loads(Path(a.request).read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tracemalloc.start()
    phases = {k: Phase() for k in ("R", "R_interventions", "M", "M_interventions", "baselines", "audit",
                                   "persist_write", "persist_reload")}
    t0 = time.perf_counter()
    store, digests = pass_reference(a.split, phases)
    code = code_hashes()
    freeze_now = {"generator": W.GENERATOR_VERSION, "digests": digests, "code": code}
    res = {"schema": RESULT_SCHEMA, "split": a.split, "attempt": req.get("attempt", 1),
           "repeat_of": req.get("repeat_of"), "freeze_now": freeze_now,
           "commit": os.environ.get("GITHUB_SHA", "")}
    if a.split == "holdout":
        frozen = req.get("freeze")
        if frozen != freeze_now:
            res["verdict"] = "FREEZE_MISMATCH"
            res["frozen"] = frozen
            (out / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True))
            (out / "VERDICT").write_text("FREEZE_MISMATCH\n")
            print("FREEZE_MISMATCH")
            return 1
    conf = conformance()
    with tempfile.TemporaryDirectory() as tmp:
        rows, iv_rows, indist, indist_log, violations, persist, state_breaks = evaluate(a.split, store, phases, tmp)
        persist_res = run_persistence(persist, tmp, phases)
    summary = summarize(a.split, rows, iv_rows, indist, violations, persist_res, conf, state_breaks)
    passed = all(summary["criteria"].values())
    res.update(summary=summary, resources={k: v.report() for k, v in phases.items()},
               total_seconds=round(time.perf_counter() - t0, 1),
               verdict=("PASS" if passed else "FAIL") if a.split == "holdout" else ("DEV_OK" if passed else "DEV_PROBLEMS"))
    (out / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    with open(out / "rows.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    with open(out / "interventions.jsonl", "w") as fh:
        for r in iv_rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    with open(out / "indist_log.jsonl", "w") as fh:
        for r in indist_log:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    write_summary(out / "SUMMARY.md", res)
    (out / "VERDICT").write_text(res["verdict"] + "\n")
    print(res["verdict"], json.dumps(summary["criteria"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
