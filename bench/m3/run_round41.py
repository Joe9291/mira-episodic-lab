#!/usr/bin/env python3
"""Round 4.1 targeted stale-answer test (docs/ROUND_4_1.md), model-free.

M, R, the round 4.0 baselines, the audit, the persistence check and the 4.0 conformance
set are used unchanged. Pass 1: R computes every expected answer (BEFORE and AFTER worlds,
counterfactual worlds); for the holdout these and the code are compared with the freeze
before M runs. Pass 2: M, S0-S5, failure classes, stale rate, over-update flag, S4
positive control, audit, pair conditions, B-indistinguishability, interventions,
persistence; every table of SUMMARY.md is generated from the rows.

usage: run_round41.py --split dev|holdout --request config/round41.json --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_round40 as R40  # noqa: E402
from episodic_lab import r40_analysis as A  # noqa: E402
from episodic_lab import r40_baselines as B  # noqa: E402
from episodic_lab import r40_world as W40  # noqa: E402
from episodic_lab import r41_world as W  # noqa: E402
from episodic_lab.r40_memory import Memory, ReportStore  # noqa: E402
from episodic_lab.r40_reference import reference_answers  # noqa: E402
from episodic_lab.r41_baselines import s5, s5_state  # noqa: E402

CODE_FILES = R40.CODE_FILES + ("episodic_lab/r41_world.py", "episodic_lab/r41_baselines.py",
                               "bench/m3/run_round41.py", "tests/fixtures/r41_conformance.json")
RESULT_SCHEMA = "episodic_lab.round41_result.v1"
BASELINES = B.SYSTEMS + ("S5",)
SYSTEMS = ("M",) + BASELINES
REQUIRED = {"S1": W.FAMILIES, "S2": W.FAMILIES, "S5": W.FAMILIES}
KINDS = ("remove_change", "irrelevant_control")
CLASSES = ("right", "stale", "conflict", "abstain", "other")


def code_hashes():
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE_FILES}


def answer(system, reports, q, ctx):
    if system == "S5":
        return s5(reports, q, ctx)
    return B.ANSWER[system](reports, q, ctx)


def state(system, reports, q, ctx):
    if system == "S5":
        return s5_state(reports, q, ctx)
    return B.STATE[system](reports, q, ctx)


def classify(gold, ans, prev):
    """Priority: right, stale, wrong conflict output, wrong abstention, other wrong value."""
    if A.hit("current", gold, ans):
        return "right"
    if prev is not None and A.hit("current", prev, ans):
        return "stale"
    status = ans.get("status") if isinstance(ans, dict) else None
    if status == "conflict":
        return "conflict"
    if status == "unknown":
        return "abstain"
    return "other"


def units(pair):
    """(key, side, delay, reports, question, now) for every evaluated question of a pair."""
    for world in ("A", "B"):
        w = pair["before"][world]
        yield ("before", world, None), w["reports"], w["questions"][0], w["questions"][0]["now"]
    for inst in pair["instances"]:
        for world in ("A", "B"):
            w = inst[world]
            yield ("after", world, inst["delay"]), w["reports"], w["questions"][0], inst["now"]


def shim_counterfactual(pair, inst, kind):
    return W40.counterfactual(pair, inst, kind)


# ------------------------------------------------------------------ pass 1
def pass_reference(split, phases):
    h = {k: hashlib.sha256() for k in ("worlds", "questions", "gold", "interventions")}
    store = {}
    for pair in W.iter_pairs(split):
        for key, reports, q, now in units(pair):
            h["worlds"].update(R40.dumps([pair["pair"], key, pair["ranks"], reports]))
            h["questions"].update(R40.dumps(q))
            gold, aux, past = phases["R"].run(R40.run_reference, reports, [q], pair["fact"], None, now)
            h["gold"].update(R40.dumps([pair["pair"], key, gold]))
            store[(pair["pair"],) + key] = gold
        for inst in pair["instances"]:
            for kind in KINDS:
                cf = W40.counterfactual(pair, inst, kind)
                gold, _, _ = phases["R_interventions"].run(R40.run_reference, cf["reports"], inst["A"]["questions"],
                                                           pair["fact"], None, inst["now"])
                h["interventions"].update(R40.dumps([pair["pair"], inst["delay"], kind, cf, gold]))
                store[(pair["pair"], kind, inst["delay"])] = gold
    return store, {k: v.hexdigest() for k, v in h.items()}


# ------------------------------------------------------------------ conformance
def conformance41():
    d = json.loads((ROOT / "tests/fixtures/r41_conformance.json").read_text())
    fields = ("report_id", "report_day", "source", "rank", "subject", "attribute", "kind", "value",
              "valid_from", "target_report_id")
    out = []
    for name, w in d["worlds"].items():
        reps = sorted((dict(zip(fields, row), origin="o-" + row[0]) for row in w["reports"]),
                      key=lambda r: (r["report_day"], r["report_id"]))
        for cid, last, now, exp, exp5 in w["checks"]:
            pre = [r for r in reps if r["report_day"] <= last]
            q = {"qid": cid, "op": "current", "now": now, "subject": "key", "attribute": "loc"}
            got = {"M": Memory(pre).answer(q), "R": reference_answers(pre, [q])[0][cid], "S5": s5(pre, q)}
            ok = got["M"] == exp and got["R"] == exp and got["S5"] == exp5
            out.append({"case": cid, "world": name, "ok": ok, **got})
    return out


# ------------------------------------------------------------------ pass 2
def evaluate(split, store, phases, tmpdir):
    rows, iv_rows, violations, persist, state_breaks, indist_log = [], [], [], [], [], []
    indist = {(s, f): set() for s in BASELINES for f in W.FAMILIES}
    for pair in W.iter_pairs(split):
        pid, fam = pair["pair"], pair["family"]
        before_gold = {w: store[(pid, "before", w, None)][pair["before"][w]["questions"][0]["qid"]] for w in "AB"}
        if before_gold["A"] != before_gold["B"]:
            violations.append(f"{pid}: BEFORE gold differs between A and B")
        before_ans = {}
        after = {}
        for key, reports, q, now in units(pair):
            side, world, delay = key
            gold_all = store[(pid,) + key]
            g = gold_all[q["qid"]]
            ctx = {"hist": gold_all["__hist"], "anchor_hist": []}

            def run_m():
                return Memory(reports).answer(q)
            m = phases["M"].run(run_m)
            ans = phases["baselines"].run(lambda: {s: answer(s, reports, q, ctx) for s in BASELINES})
            ans["M"] = m
            prev = before_gold[world] if side == "after" else None
            row = {"qid": q["qid"], "pair": pid, "family": fam, "variant": pair["variant"], "side": side,
                   "world": world, "delay": delay, "gold": g, "previously_accepted": prev, "M": m,
                   "M_equals_R": m == g, "stale_den": side == "after" and prev is not None and not A.hit("current", g, prev)}
            for s in SYSTEMS:
                row[f"class_{s}"] = classify(g, ans[s], prev if side == "after" else None)
                row[f"hit_{s}"] = row[f"class_{s}"] == "right"
            if side == "before":
                before_ans[world] = ans
            else:
                for s in SYSTEMS:
                    if world == "B":
                        row[f"overupdate_den_{s}"] = A.hit("current", before_gold["B"], before_ans["B"][s])
                        row[f"overupdate_{s}"] = row[f"overupdate_den_{s}"] and not row[f"hit_{s}"]
                after[(world, delay)] = (g, {s: state(s, reports, q, ctx) for s in BASELINES}, ans, q)
                for v in phases["audit"].run(W40.audit_world, reports, pair["ranks"], None, pair["fact"], True):
                    violations.append(f"{pid} d{delay} {world}: {v}")
                path = Path(tmpdir) / f"{pid}_{delay}_{world}.jsonl"
                st = ReportStore(path)
                phases["persist_write"].run(st.extend, reports)
                persist.append({"path": str(path), "seal": st.seal(), "questions": [q],
                                "expect": hashlib.sha256(R40.dumps([m])).hexdigest()})
            rows.append(row)
        for inst in pair["instances"]:
            delay = inst["delay"]
            gA, gB = after[("A", delay)][0], after[("B", delay)][0]
            if A.hit("current", gA, before_gold["A"]):
                violations.append(f"{pid} d{delay}: c does not change the answer in A")
            if not A.hit("current", gB, before_gold["B"]):
                violations.append(f"{pid} d{delay}: c changes the answer in B")
            ra, rb = inst["A"]["reports"], inst["B"]["reports"]
            diff = [x["report_id"] for x, y in zip(ra, rb) if x != y]
            if len(ra) != len(rb) or [x["report_day"] for x in ra] != [y["report_day"] for y in rb] \
                    or diff != [inst["crit_id"]]:
                violations.append(f"{pid} d{delay}: pair control {diff}")
            if any(r["report_day"] > pair["d3"] for r in ra[:inst["n_relevant"]] if r["report_id"] != inst["crit_id"]):
                violations.append(f"{pid}: a relevant report after c")
            for s in BASELINES:
                stA, stB = after[("A", delay)][1][s], after[("B", delay)][1][s]
                ansA, ansB = after[("A", delay)][2][s], after[("B", delay)][2][s]
                if stA == stB:
                    if ansA != ansB:
                        state_breaks.append(f"{s} {pid} d{delay}: equal state, different answers")
                    if not A.hit("current", gA, gB):
                        if pid not in indist[(s, fam)]:
                            indist_log.append({"system": s, "pair": pid, "delay": delay, "state": repr(stA),
                                               "gold_A": gA, "gold_B": gB})
                        indist[(s, fam)].add(pid)
            for kind in KINDS:
                cf = W40.counterfactual(pair, inst, kind)
                for v in W40.audit_world(cf["reports"], cf["ranks"], None, pair["fact"], False):
                    violations.append(f"{pid} d{delay} {kind}: {v}")
                q = inst["A"]["questions"][0]
                cf_gold = store[(pid, kind, delay)][q["qid"]]
                m_cf = phases["M_interventions"].run(lambda: Memory(cf["reports"]).answer(q))
                iv_rows.append({"pair": pid, "family": fam, "delay": delay, "kind": kind, "note": cf["note"],
                                "removed": cf["removed"], "changed": not A.hit("current", gA, cf_gold),
                                "unchanged": cf_gold == gA, "M_equals_R": m_cf == cf_gold,
                                "returns_to_previous": A.hit("current", before_gold["A"], cf_gold),
                                "R": cf_gold, "M": m_cf})
    return rows, iv_rows, indist, indist_log, violations, persist, state_breaks


# ------------------------------------------------------------------ summary (tables from rows)
def summarize(split, rows, iv_rows, indist, violations, persist_res, conf40, conf41, state_breaks):
    need = A.min_pairs(split)
    out = {"min_pairs": need}
    out["answers"] = {s: {side: {"right": sum(r[f"hit_{s}"] for r in rows if r["side"] == side),
                                 "n": sum(1 for r in rows if r["side"] == side)} for side in ("before", "after")}
                      for s in SYSTEMS}
    out["classes_after"] = {s: {f"{f}|{w}": {c: sum(1 for r in rows if r["side"] == "after" and r["family"] == f
                                                     and r["world"] == w and r[f"class_{s}"] == c) for c in CLASSES}
                                for f in W.FAMILIES for w in "AB"} for s in SYSTEMS}
    out["stale"] = {s: {"stale": sum(1 for r in rows if r["stale_den"] and r[f"class_{s}"] == "stale"),
                        "denominator": sum(1 for r in rows if r["stale_den"])} for s in SYSTEMS}
    out["over_update"] = {s: {f: (lambda den, num: {"flagged": num, "denominator": den} if den else "not evaluable")(
        sum(1 for r in rows if r["side"] == "after" and r["world"] == "B" and r["family"] == f and r[f"overupdate_den_{s}"]),
        sum(1 for r in rows if r["side"] == "after" and r["world"] == "B" and r["family"] == f and r[f"overupdate_{s}"]))
        for f in W.FAMILIES} for s in SYSTEMS}
    out["pairs_right"] = {s: {f: {"right": sum(1 for p in {r["pair"] for r in rows if r["family"] == f}
                                               if all(r[f"hit_{s}"] for r in rows if r["pair"] == p)),
                                  "pairs": len({r["pair"] for r in rows if r["family"] == f})} for f in W.FAMILIES}
                          for s in SYSTEMS}
    out["by_delay_after"] = {s: {str(d): sum(r[f"hit_{s}"] for r in rows if r["side"] == "after" and r["delay"] == d)
                                 for d in W.DELAYS} for s in SYSTEMS}
    out["indistinguishable"] = {f"{s}|{f}": len(v) for (s, f), v in sorted(indist.items())}
    out["required_cells"] = {f"{s}|{f}": {"pairs": len(indist[(s, f)]), "required": need, "ok": len(indist[(s, f)]) >= need}
                             for s, fams in REQUIRED.items() for f in fams}
    ivs = {}
    for kind in KINDS:
        sel = [r for r in iv_rows if r["kind"] == kind]
        ivs[kind] = {"cases": len(sel), "answer_changed": sum(r["changed"] for r in sel),
                     "unchanged": sum(r["unchanged"] for r in sel), "M_equals_R": sum(r["M_equals_R"] for r in sel),
                     "returns_to_previous": sum(r["returns_to_previous"] for r in sel),
                     "changed_pairs_at_delay_0": {f: sum(1 for r in sel if r["delay"] == 0 and r["family"] == f and r["changed"])
                                                  for f in W.FAMILIES}}
    out["interventions"] = ivs
    s4_ok = all(r["hit_S4"] for r in rows)
    m_errors = [r["qid"] for r in rows if not r["hit_M"]]
    criteria = {
        "M_zero_errors": not m_errors,
        "conformance_100": all(c["ok"] for c in conf40) and all(c["ok"] for c in conf41),
        "M_equals_R_everywhere": all(r["M_equals_R"] for r in rows) and all(r["M_equals_R"] for r in iv_rows),
        "S4_positive_control": s4_ok,
        "interventions_as_predicted": all(r["M_equals_R"] for r in iv_rows)
            and all(v >= need for v in ivs["remove_change"]["changed_pairs_at_delay_0"].values())
            and ivs["remove_change"]["returns_to_previous"] == ivs["remove_change"]["cases"]
            and ivs["irrelevant_control"]["unchanged"] == ivs["irrelevant_control"]["cases"] > 0,
        "persistence": persist_res["ok"],
        "audit_clean": not violations and not state_breaks,
        "required_cells_filled": all(v["ok"] for v in out["required_cells"].values()),
    }
    out.update(criteria=criteria, M_errors=m_errors[:50], violations=violations[:50], n_violations=len(violations),
               state_breaks=state_breaks[:20], persistence=persist_res,
               conformance={"r40": [sum(c["ok"] for c in conf40), len(conf40)],
                            "r41": [sum(c["ok"] for c in conf41), len(conf41)],
                            "failed": [c for c in conf40 + conf41 if not c["ok"]][:10]})
    return out


def write_summary(path, res):
    s = res["summary"]
    L = [f"# Round 4.1 stale test - {res['split']} (attempt {res['attempt']}{', repeat' if res['repeat_of'] else ''})", "",
         f"Verdict: **{res['verdict']}**", "", "| criterion | ok |", "|---|---|"]
    L += [f"| {k} | {'yes' if v else 'NO'} |" for k, v in s["criteria"].items()]
    L += ["", "Answers right (BEFORE: once per world; AFTER: per world and delay):", "",
          "| system | BEFORE | AFTER | stale / denominator |", "|---|---|---|---|"]
    for k in SYSTEMS:
        a = s["answers"][k]
        L.append(f"| {k} | {a['before']['right']}/{a['before']['n']} | {a['after']['right']}/{a['after']['n']} | "
                 f"{s['stale'][k]['stale']}/{s['stale'][k]['denominator']} |")
    L += ["", "AFTER answers by failure class (priority right > stale > conflict > abstain > other), per family and world:", ""]
    cols = [f"{f}|{w}" for f in W.FAMILIES for w in "AB"]
    L += ["| system | class | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
    for k in SYSTEMS:
        for c in CLASSES:
            L.append(f"| {k} | {c} | " + " | ".join(str(s["classes_after"][k][x][c]) for x in cols) + " |")
    L += ["", "Over-update flag (world B: BEFORE right, AFTER wrong) - flagged / denominator:", "",
          "| system | " + " | ".join(W.FAMILIES) + " |", "|---|" + "---|" * len(W.FAMILIES)]
    for k in SYSTEMS:
        cells = []
        for f in W.FAMILIES:
            v = s["over_update"][k][f]
            cells.append(v if isinstance(v, str) else f"{v['flagged']}/{v['denominator']}")
        L.append(f"| {k} | " + " | ".join(cells) + " |")
    L += ["", "Pairs fully right (BEFORE and AFTER, both worlds, all delays):", "",
          "| system | " + " | ".join(W.FAMILIES) + " |", "|---|" + "---|" * len(W.FAMILIES)]
    for k in SYSTEMS:
        L.append(f"| {k} | " + " | ".join(f"{s['pairs_right'][k][f]['right']}/{s['pairs_right'][k][f]['pairs']}" for f in W.FAMILIES) + " |")
    L += ["", f"Required B-indistinguishable cells (AFTER; min {s['min_pairs']} pairs):", ""]
    L += [f"- {k}: {v['pairs']}" + ("" if v["ok"] else " (TOO FEW)") for k, v in s["required_cells"].items()]
    L += ["", "| intervention | cases | answer changed | unchanged | M = R | returns to previous answer |", "|---|---|---|---|---|---|"]
    for k, v in s["interventions"].items():
        L.append(f"| {k} | {v['cases']} | {v['answer_changed']} | {v['unchanged']} | {v['M_equals_R']} | {v['returns_to_previous']} |")
    L += ["", f"Conformance: round 4.0 set {s['conformance']['r40'][0]}/{s['conformance']['r40'][1]}, round 4.1 set "
              f"{s['conformance']['r41'][0]}/{s['conformance']['r41'][1]}. Persistence: {s['persistence']['stores']} stores, "
              f"ok = {s['persistence']['ok']}. Audit violations: {s['n_violations']}.", "", "Resources:", ""]
    L += [f"- {k}: {v['seconds']} s, peak +{v['peak_extra_mb']} MB traced" for k, v in res["resources"]["phases"].items()]
    L += [f"- process max RSS: {res['resources']['max_rss_mb_self']} MB; reload subprocess max RSS: "
          f"{res['resources']['max_rss_mb_children']} MB"]
    Path(path).write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("dev", "holdout"), required=True)
    ap.add_argument("--request", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    req = json.loads(Path(a.request).read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tracemalloc.start()
    phases = {k: R40.Phase() for k in ("R", "R_interventions", "M", "M_interventions", "baselines", "audit",
                                       "persist_write", "persist_reload")}
    t0 = time.perf_counter()
    store, digests = pass_reference(a.split, phases)
    freeze_now = {"generator": W.GENERATOR_VERSION, "digests": digests, "code": code_hashes()}
    res = {"schema": RESULT_SCHEMA, "split": a.split, "attempt": req.get("attempt", 1),
           "repeat_of": req.get("repeat_of"), "freeze_now": freeze_now, "commit": os.environ.get("GITHUB_SHA", "")}
    if a.split == "holdout" and req.get("freeze") != freeze_now:
        res.update(verdict="FREEZE_MISMATCH", frozen=req.get("freeze"))
        (out / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True))
        (out / "VERDICT").write_text("FREEZE_MISMATCH\n")
        print("FREEZE_MISMATCH")
        return 1
    conf40, conf41 = R40.conformance(), conformance41()
    with tempfile.TemporaryDirectory() as tmp:
        rows, iv_rows, indist, indist_log, violations, persist, state_breaks = evaluate(a.split, store, phases, tmp)
        persist_res = R40.run_persistence(persist, tmp, phases)
    summary = summarize(a.split, rows, iv_rows, indist, violations, persist_res, conf40, conf41, state_breaks)
    passed = all(summary["criteria"].values())
    res.update(summary=summary, total_seconds=round(time.perf_counter() - t0, 1),
               resources={"phases": {k: v.report() for k, v in phases.items()},
                          "max_rss_mb_self": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                          "max_rss_mb_children": round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1)},
               verdict=("PASS" if passed else "FAIL") if a.split == "holdout" else ("DEV_OK" if passed else "DEV_PROBLEMS"))
    (out / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    for name, data in (("rows.jsonl", rows), ("interventions.jsonl", iv_rows), ("indist_log.jsonl", indist_log)):
        with open(out / name, "w") as fh:
            for r in data:
                fh.write(json.dumps(r, sort_keys=True) + "\n")
    write_summary(out / "SUMMARY.md", res)
    (out / "VERDICT").write_text(res["verdict"] + "\n")
    print(res["verdict"], json.dumps(summary["criteria"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
