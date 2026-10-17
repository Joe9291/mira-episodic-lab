"""Collector of round 3.3. Two separate results:

VERDICT (COMPLETE / INCOMPLETE): the evaluation is complete and reproducible - schema,
identity and provenance (request hash, code commit) check out, the pair design holds
(worlds differ only in the critical episode, identical decision inputs), the collector's
re-run of the whole deterministic job reproduces every row, the decision process refuses
cut-off and changed stores.

MILESTONE (PASS / FAIL): the development criteria of docs/ROUND_3_3.md (fixed before the
GitHub run), including the required numbers of available and informative cases. The workflow fails unless both are
COMPLETE and PASS.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_round33  # noqa: E402
from episodic_lab.env import KINDS, generate_pair  # noqa: E402

FULLY_AVAILABLE = ("intact", "none", "random", "relevant_removed")
MIN_AVAILABLE = 0.9      # swapped_binding, irrelevant_removed: share of planned cases
MIN_INFORMATIVE = 0.6    # swapped_binding, relevant_removed: informative cases / planned


def criteria(s: dict, pairs: int) -> list[tuple[str, bool]]:
    planned = 2 * pairs
    out = []

    def every(fn):
        return all(fn(k) for k in KINDS)
    out.append(("every case planned for intact, none, random, relevant_removed is available",
                every(lambda k: all(s[f"{k}:{n}"].get("n") == planned == s[f"{k}:{n}"]["n_planned"]
                                    for n in FULLY_AVAILABLE))))
    out.append((f"swapped_binding and irrelevant_removed available in >= {MIN_AVAILABLE:.0%} of planned cases",
                every(lambda k: all(s[f"{k}:{n}"].get("n", 0) >= MIN_AVAILABLE * planned
                                    for n in ("swapped_binding", "irrelevant_removed")))))
    out.append((f"informative cases (prediction != truth) >= {MIN_INFORMATIVE:.0%} of planned for swap and relevant removal",
                every(lambda k: all(s[f"{k}:{n}"].get("n_informative", 0) >= MIN_INFORMATIVE * planned
                                    for n in ("swapped_binding", "relevant_removed")))))
    out.append(("intact: success 1.0 and pair success 1.0",
                every(lambda k: s[f"{k}:intact"]["success"] == 1.0 and s[f"{k}:intact"]["pair_success"] == 1.0)))
    out.append(("no memory and random memory: pair success 0 (fixed, deterministic exploration policy)",
                every(lambda k: s[f"{k}:none"]["pair_success"] == 0.0 and s[f"{k}:random"]["pair_success"] == 0.0)))
    out.append(("swapped binding: action as predicted in >= 0.95 of informative cases",
                every(lambda k: (s[f"{k}:swapped_binding"].get("as_predicted_informative") or 0) >= 0.95)))
    out.append(("relevant episode removed: action as predicted in >= 0.95 of informative cases",
                every(lambda k: (s[f"{k}:relevant_removed"].get("as_predicted_informative") or 0) >= 0.95)))
    out.append(("irrelevant episode removed: success 1.0", every(lambda k: s[f"{k}:irrelevant_removed"]["success"] == 1.0)))
    return out


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


def main(request_path: str, result_path: str, dest: str, commit: str | None = None) -> int:
    req = json.loads(Path(request_path).read_text())
    data = json.loads(Path(result_path).read_text())
    problems = []
    if data.get("schema") != run_round33.SCHEMA:
        problems.append("schema")
    if (data.get("series"), data.get("pairs_per_kind"), data.get("status")) != (req["series"], req["pairs_per_kind"], "OK"):
        problems.append("identity_or_status")
    prov = data.get("provenance") or {}
    if prov.get("request_sha256") != hashlib.sha256(Path(request_path).read_bytes()).hexdigest():
        problems.append("provenance:request")
    if not isinstance(prov.get("code_commit"), str) or (commit and prov["code_commit"] != commit):
        problems.append("provenance:commit")
    problems += design_problems(req["series"], req["pairs_per_kind"])
    with tempfile.TemporaryDirectory() as tmp:
        again = run_round33.run(req["series"], req["pairs_per_kind"], Path(tmp))
    if json.dumps(again["rows"], sort_keys=True) != json.dumps(data.get("rows"), sort_keys=True):
        problems.append("rerun_rows_differ")
    if again["summary"] != data.get("summary") or again["pair_hashes"] != data.get("pair_hashes"):
        problems.append("rerun_summary_or_hashes_differ")
    if data.get("refused") != {"cut": True, "changed": True} or again["refused"] != data.get("refused"):
        problems.append("store_integrity")
    verdict = "COMPLETE" if not problems else "INCOMPLETE"
    results = criteria(again["summary"], req["pairs_per_kind"])
    milestone = "PASS" if verdict == "COMPLETE" and all(ok for _, ok in results) else "FAIL"
    lines = [f"FAILED {x}" for x in problems] or ["OK schema, provenance, design, re-run and store integrity"]
    lines += ["", f"VERDICT {verdict}", ""] + [f"{'PASS' if ok else 'FAIL'} {text}" for text, ok in results]
    lines += ["", f"MILESTONE {milestone}"]
    s = again["summary"]
    md = ["# Round 3.3 summary (paired action worlds, explicit agent memory)", "",
          f"{req['pairs_per_kind']} pairs per kind. Every case was decided by its own fresh isolated "
          "process that received only that case's store, seal and decision text. The evaluation "
          "units are the pairs: the cases are repeated conditions of the same worlds. The causal "
          "evidence is the intervention pattern; the memory-branch share only describes the policy.", "",
          "| kind | intervention | n / planned | success | pair success | as predicted | informative n | as predicted (informative) | share decided via memory branch |",
          "|---|---|---|---|---|---|---|---|---|"]
    for key, v in s.items():
        kind, name = key.split(":")
        if not v.get("n"):
            md.append(f"| {kind} | {name} | 0 / {v['n_planned']} | - | - | - | - | - | - |")
            continue
        inf = "-" if v["as_predicted_informative"] is None else f"{v['as_predicted_informative']:.2f}"
        md.append(f"| {kind} | {name} | {v['n']} / {v['n_planned']} | {v['success']:.2f} | {v['pair_success']:.2f} | "
                  f"{v['as_predicted']:.2f} | {v['n_informative']} | {inf} | {v['memory_policy']:.2f} |")
    md += ["", f"Store integrity in the decision process: cut-off store refused {data.get('refused', {}).get('cut')}, "
           f"changed store refused {data.get('refused', {}).get('changed')}.", "",
           f"VERDICT {verdict} - MILESTONE {milestone}", "", "Development criteria (fixed before the GitHub run, after a local development run):", ""]
    md += [f"- {'PASS' if ok else 'FAIL'} {text}" for text, ok in results]
    d = Path(dest)
    (d / "CHECK.txt").write_text("\n".join(lines) + "\n")
    (d / "SUMMARY.md").write_text("\n".join(md) + "\n")
    (d / "VERDICT").write_text(verdict + "\n")
    (d / "MILESTONE").write_text(milestone + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:5]))
