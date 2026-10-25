#!/usr/bin/env python3
"""Round 4.3 collector (docs/ROUND_4_3.md section 6): merges the job files of one split,
checks the bound numbers against config/round43_counts.json and applies the pass rule.
Writes SUMMARY.md, summary.json and VERDICT (PASS / FAIL / INCOMPLETE).

usage: collect_round43.py --split dev|holdout --dir DIR [--counts config/round43_counts.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ("r1_M_vs_R", "r1_modeA", "r1_R_synthetic", "r2_modeT", "r3_composition", "r4_integrity",
         "r4_interrupted", "r4_persistence", "r5_binding", "r5_digest_partition", "r6_controls", "r7_conformance",
         "r8_state")
TAMPER_CASES, INTERRUPTED_CASES = 12, 10
FAMILIES = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "T1", "T2", "T3", "T4", "T5")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--counts", default=str(ROOT / "config/round43_counts.json"))
    ap.add_argument("--request", default=str(ROOT / "config/round43.json"))
    a = ap.parse_args()
    d = Path(a.dir)
    jobs = [json.loads(p.read_text()) for p in sorted(d.glob(f"r43_run_{a.split}_*.json"))]
    counts_file = json.loads(Path(a.counts).read_text())
    frozen = counts_file["splits"][a.split]
    problems = []
    if any(j["status"] != "OK" for j in jobs):
        problems += [f"job {j['families']}: {j.get('error')}" for j in jobs if j["status"] != "OK"]
    fams = [f for j in jobs for f in j.get("families", [])]
    if sorted(fams) != sorted(FAMILIES):
        problems.append(f"families covered: {sorted(fams)}")
    if len({json.dumps(j["code"], sort_keys=True) for j in jobs}) > 1:
        problems.append("jobs ran different code")
    counts = {f: c for j in jobs for f, c in j.get("counts", {}).items()}
    if counts != frozen["families"]:
        problems.append("counts differ from config/round43_counts.json")
    if a.split == "holdout":
        fr = json.loads(Path(a.request).read_text()).get("freeze") or {}
        got = {f: dg for j in jobs for f, dg in j.get("digests", {}).items()}
        if got != fr.get("families"):
            problems.append("world / R-answer digests differ from the freeze")
        if any(j["code"] != fr.get("code") for j in jobs):
            problems.append("code differs from the freeze")
    viol = collections.Counter()
    meas = collections.Counter()
    ctl = {}
    items = []
    for j in jobs:
        viol.update(j.get("violations", {}))
        meas.update(j.get("measures", {}))
        items += j.get("violation_items", [])
        for k, v in j.get("controls", {}).items():
            c = ctl.setdefault(k, {"informative": 0, "pairs": 0, "families": set(), "operators": collections.Counter()})
            c["informative"] += v["informative"]
            c["pairs"] += v["pairs"]
            c["families"] |= set(v["families"])
            c["operators"].update(v["operators"])
    tot = frozen["total"]
    conf = sum(j.get("conformance_checks", 0) for j in jobs)
    expect = {"mode_a_answers": tot["questions"], "mode_t_evaluations": tot["mode_t_evaluations"],
              "composition": tot["cuts"] - tot["instances"], "tamper_cases": TAMPER_CASES * tot["instances"],
              "interrupted_cases": INTERRUPTED_CASES * tot["instances"], "persistence_checks": tot["instances"],
              "lost_fact_tests": tot["instances"] * 3 // 4,
              "state_checks_cut": tot["state_checks_cut"], "state_checks_mode_a": tot["state_checks_mode_a"],
              "state_checks_mode_t": tot["state_checks_mode_t"],
              "digest_partition_checks_mode_a": tot["digest_checks_mode_a"],
              "digest_partition_checks_mode_t": tot["digest_checks_mode_t"]}
    for k, v in expect.items():
        if meas.get(k) != v:
            problems.append(f"measure {k}: {meas.get(k)} != {v}")
    if conf != counts_file["conformance_checks"]:
        problems.append(f"conformance checks {conf} != {counts_file['conformance_checks']}")
    if sum(viol.values()):
        problems.append(f"violations: {dict(viol)}")
    controls_ok = all(c["informative"] >= 30 and c["pairs"] >= 10 for c in ctl.values()) and len(ctl) == 3
    verdict = "FAIL" if problems else ("PASS" if controls_ok else "INCOMPLETE")
    freeze_id = (json.loads(Path(a.request).read_text()).get("freeze") or {}).get("freeze_id")
    summary = {"split": a.split, "verdict": verdict, "freeze_id": freeze_id, "problems": problems, "violations": dict(viol),
               "measures": dict(meas), "conformance_checks": conf, "totals": tot,
               "controls": {k: {"informative": v["informative"], "pairs": v["pairs"], "families": sorted(v["families"]),
                                "operators": dict(v["operators"])} for k, v in ctl.items()},
               "violation_items": items[:200], "seconds": {j["families"][0]: j.get("seconds") for j in jobs}}
    (d / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    lines = [f"# Round 4.3 ({a.split}) - {verdict}", "", f"Freeze id: {freeze_id}",
             f"Totals: {tot}", f"Measures: {dict(sorted(meas.items()))}", f"Conformance checks: {conf}",
             f"Violations: {dict(viol) or 'none'}", "Controls:"]
    lines += [f"- {k}: {v['informative']} informative cases, {v['pairs']} pairs, families {sorted(v['families'])}"
              for k, v in sorted(ctl.items())]
    lines += ["Problems:"] + [f"- {p}" for p in problems] if problems else ["Problems: none"]
    (d / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    (d / "VERDICT").write_text(verdict + "\n")
    print(verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
