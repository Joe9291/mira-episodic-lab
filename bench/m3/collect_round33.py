"""Collector of round 3.3: re-runs the whole deterministic job and compares; checks the
pair design (worlds differ only in the critical episode, identical decision inputs) and
the pre-registered pass criteria (docs/ROUND_3_3.md)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_round33  # noqa: E402
from episodic_lab.env import KINDS, generate_pair  # noqa: E402

CRITERIA = (
    ("intact success = 1.0 in every kind", lambda s, k: s[f"{k}:intact"]["success"] == 1.0),
    ("intact pair success = 1.0 in every kind", lambda s, k: s[f"{k}:intact"]["pair_success"] == 1.0),
    ("no memory / random memory: pair success = 0", lambda s, k: s[f"{k}:none"]["pair_success"] == 0.0
     and s[f"{k}:random"]["pair_success"] == 0.0),
    ("swapped binding: action as predicted >= 0.95 where the prediction differs from the truth",
     lambda s, k: (s[f"{k}:swapped_binding"]["as_predicted_informative"] or 0) >= 0.95),
    ("relevant episode removed: action as predicted >= 0.95 where it differs from the truth",
     lambda s, k: (s[f"{k}:relevant_removed"]["as_predicted_informative"] or 0) >= 0.95),
    ("irrelevant episode removed: success = 1.0", lambda s, k: s[f"{k}:irrelevant_removed"]["success"] == 1.0),
)


def design_problems(series: str, pairs: int) -> list:
    p = []
    for kind in KINDS:
        for i in range(pairs):
            pair = generate_pair(f"{series}-{i}", kind)
            a, b = pair["worlds"]["A"], pair["worlds"]["B"]
            diff = [j for j, (x, y) in enumerate(zip(a["experiences"], b["experiences"])) if x != y]
            if diff != [pair["critical"]] or a["decision"] != b["decision"] or a["truth"] == b["truth"]:
                p.append(f"pair_design:{kind}:{i}")
    return p


def main(request_path: str, result_path: str, dest: str) -> int:
    req = json.loads(Path(request_path).read_text())
    data = json.loads(Path(result_path).read_text())
    lines, ok = [], True
    if (data.get("series"), data.get("pairs_per_kind"), data.get("status")) != (req["series"], req["pairs_per_kind"], "OK"):
        lines.append("FAILED identity_or_status")
        ok = False
    problems = design_problems(req["series"], req["pairs_per_kind"])
    with tempfile.TemporaryDirectory() as tmp:
        again = run_round33.run(req["series"], req["pairs_per_kind"], Path(tmp))
    if json.dumps(again["rows"], sort_keys=True) != json.dumps(data.get("rows"), sort_keys=True):
        problems.append("rerun_rows_differ")
    if again["summary"] != data.get("summary") or again["pair_hashes"] != data.get("pair_hashes"):
        problems.append("rerun_summary_or_hashes_differ")
    if data.get("refused") != {"cut": True, "changed": True}:
        problems.append("store_integrity")
    lines += [f"FAILED {x}" for x in problems] or ["OK rerun, design and integrity"]
    ok = ok and not problems
    s = again["summary"]
    lines.append("")
    for text, check in CRITERIA:
        passed = all(check(s, k) for k in KINDS)
        lines.append(f"{'PASS' if passed else 'FAIL'} {text}")
    md = ["# Round 3.3 summary (paired action worlds, explicit agent memory)", "",
          f"{req['pairs_per_kind']} pairs per kind; every action decided by a fresh process from the store only.",
          "", "| kind | intervention | n | success | pair success | as predicted | informative n | as predicted (informative) | memory used |",
          "|---|---|---|---|---|---|---|---|---|"]
    for key, v in s.items():
        kind, name = key.split(":")
        inf = "-" if v["as_predicted_informative"] is None else f"{v['as_predicted_informative']:.2f}"
        md.append(f"| {kind} | {name} | {v['n']} | {v['success']:.2f} | {v['pair_success']:.2f} | "
                  f"{v['as_predicted']:.2f} | {v['n_informative']} | {inf} | {v['memory_policy']:.2f} |")
    md += ["", f"Store integrity in the decision process: cut-off store refused {data.get('refused', {}).get('cut')}, "
           f"changed store refused {data.get('refused', {}).get('changed')}.", "", "Pre-registered criteria:", ""]
    md += [f"- {line}" for line in lines if line.startswith(("PASS", "FAIL "))]
    d = Path(dest)
    (d / "CHECK.txt").write_text("\n".join(lines) + "\n")
    (d / "SUMMARY.md").write_text("\n".join(md) + "\n")
    (d / "VERDICT").write_text("COMPLETE\n" if ok else "INCOMPLETE\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:4]))
