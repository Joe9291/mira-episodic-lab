"""Collector of round 3.4 step 1 (docs/ROUND_3_4.md). Two separate results:

VERDICT (COMPLETE / INCOMPLETE): schema, identity, provenance (request hash, the run's
code commit); the design (identical final state, identical decision texts, current and
previous truths equal and first truths different in every pair; the state-only
baseline's state identical in A and B and equal to the environment's final state); one
store per world and intervention for all three goals; the collector's re-run of the whole
deterministic job reproduces every row; cut-off and changed stores refused.

MILESTONE (PASS / FAIL): the criteria of docs/ROUND_3_4.md, fixed before the first run.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_round34  # noqa: E402
from episodic_lab.history_agent import state_only_encode  # noqa: E402
from episodic_lab.history_env import GOAL_NAMES, KINDS, generate_pair  # noqa: E402

FULLY_AVAILABLE = ("intact", "none", "old_removed", "last_removed", "irrelevant_removed")
MIN_AVAILABLE = 0.9
MIN_INFORMATIVE = 0.6


def criteria(s: dict, pairs: int) -> list[tuple[str, bool]]:
    planned = 2 * pairs

    def g(kind, system, name, goal):
        return s.get(f"{kind}:{system}:{name}:{goal}", {"n": 0, "n_planned": 0})

    def every(fn):
        return all(fn(k) for k in KINDS)
    out = [
        ("availability: every planned case of intact, none, old_removed, last_removed, irrelevant_removed",
         every(lambda k: all(g(k, "episodic", n, q)["n"] == planned == g(k, "episodic", n, q)["n_planned"]
                             for n in FULLY_AVAILABLE for q in GOAL_NAMES))),
        (f"availability: old_swapped in >= {MIN_AVAILABLE:.0%} of planned cases",
         every(lambda k: all(g(k, "episodic", "old_swapped", q)["n"] >= MIN_AVAILABLE * planned for q in GOAL_NAMES))),
        (f"informative cases >= {MIN_INFORMATIVE:.0%} of planned (first goal: old_removed, old_swapped; current goal: last_removed)",
         every(lambda k: all(g(k, "episodic", n, q).get("n_informative", 0) >= MIN_INFORMATIVE * planned
                             for n, q in (("old_removed", "first"), ("old_swapped", "first"), ("last_removed", "current"))))),
        ("episodic intact: success 1.0 for all goals, pair success 1.0 for the first goal",
         every(lambda k: all(g(k, "episodic", "intact", q).get("success") == 1.0 for q in GOAL_NAMES)
               and g(k, "episodic", "intact", "first").get("pair_success") == 1.0)),
        ("state_only: success 1.0 for the current goal, pair success 0.0 for the first goal",
         every(lambda k: g(k, "state_only", "intact", "current").get("success") == 1.0
               and g(k, "state_only", "intact", "first").get("pair_success") == 0.0)),
        ("episodic none: pair success 0.0 for the first goal",
         every(lambda k: g(k, "episodic", "none", "first").get("pair_success") == 0.0)),
        ("old_removed, old_swapped: first goal as predicted >= 0.95 (informative); current and previous unchanged 1.0",
         every(lambda k: all((g(k, "episodic", n, "first").get("as_predicted_informative") or 0) >= 0.95
                             and g(k, "episodic", n, "current").get("unchanged") == 1.0
                             and g(k, "episodic", n, "previous").get("unchanged") == 1.0
                             for n in ("old_removed", "old_swapped")))),
        ("last_removed: current goal as predicted >= 0.95 (informative); first goal unchanged 1.0",
         every(lambda k: (g(k, "episodic", "last_removed", "current").get("as_predicted_informative") or 0) >= 0.95
               and g(k, "episodic", "last_removed", "first").get("unchanged") == 1.0)),
        ("irrelevant_removed: success 1.0 for all goals",
         every(lambda k: all(g(k, "episodic", "irrelevant_removed", q).get("success") == 1.0 for q in GOAL_NAMES))),
    ]
    return out


def design_problems(series: str, pairs: int) -> list:
    p = []
    for kind in KINDS:
        for i in range(pairs):
            pair = generate_pair(f"{series}-{i}", kind)
            a, b = pair["worlds"]["A"], pair["worlds"]["B"]
            diff = [j for j, (x, y) in enumerate(zip(a["experiences"], b["experiences"])) if x != y]
            ok = (diff == [pair["critical"]] and a["final_state"] == b["final_state"]
                  and a["decisions"] == b["decisions"]
                  and a["truth"]["current"] == b["truth"]["current"]
                  and a["truth"]["previous"] == b["truth"]["previous"]
                  and a["truth"]["first"] != b["truth"]["first"])
            sa, sb = state_only_encode(a["experiences"]), state_only_encode(b["experiences"])
            final = {part: {k: v for k, v in a["final_state"][part].items() if v is not None}
                     for part in ("objects", "people")}
            if not ok or sa != sb or sa != final:
                p.append(f"pair_design:{kind}:{i}")
    return p


def one_store_per_world(rows: list) -> bool:
    """Every available world x intervention has exactly one store (seal) and all three goals."""
    seals, goals = {}, {}
    for r in rows:
        if r["system"] == "episodic" and r["available"]:
            key = (r["kind"], r["seed"], r["world"], r["intervention"])
            seals.setdefault(key, set()).add(r["seal"])
            goals.setdefault(key, set()).add(r["goal"])
    return bool(seals) and all(len(s) == 1 for s in seals.values()) and all(g == set(GOAL_NAMES) for g in goals.values())


def main(request_path: str, result_path: str, dest: str, commit: str | None = None) -> int:
    req = json.loads(Path(request_path).read_text())
    data = json.loads(Path(result_path).read_text())
    problems = []
    if data.get("schema") != run_round34.SCHEMA:
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
        again = run_round34.run(req["series"], req["pairs_per_kind"], Path(tmp))
    if json.dumps(again["rows"], sort_keys=True) != json.dumps(data.get("rows"), sort_keys=True):
        problems.append("rerun_rows_differ")
    if (again["summary"] != data.get("summary") or again["pair_hashes"] != data.get("pair_hashes")
            or again["stored"] != data.get("stored")):
        problems.append("rerun_summary_hashes_or_stored_differ")
    if not one_store_per_world(again["rows"]):
        problems.append("one_store_per_world")
    if data.get("refused") != {"cut": True, "changed": True} or again["refused"] != data.get("refused"):
        problems.append("store_integrity")
    verdict = "COMPLETE" if not problems else "INCOMPLETE"
    results = criteria(again["summary"], req["pairs_per_kind"])
    milestone = "PASS" if verdict == "COMPLETE" and all(ok for _, ok in results) else "FAIL"
    lines = [f"FAILED {x}" for x in problems] or ["OK schema, provenance, design, one store per world, re-run and store integrity"]
    lines += ["", f"VERDICT {verdict}", ""] + [f"{'PASS' if ok else 'FAIL'} {text}" for text, ok in results]
    lines += ["", f"MILESTONE {milestone}"]
    s = again["summary"]
    rec = [v["records"] for v in again["stored"].values()]
    ent = [v["state_entries"] for v in again["stored"].values()]
    md = ["# Round 3.4 step 1 summary (history goals, identical final state)", "",
          f"{req['pairs_per_kind']} pairs per kind; every decision in its own fresh isolated process; one "
          "episodic store per world written before any goal was drawn. Evaluation units are the pairs. "
          f"Stored information: episodic store {min(rec)}-{max(rec)} records per world; state-only baseline "
          f"{min(ent)}-{max(ent)} entries (one place per object and person).", "",
          "| kind | system | intervention | goal | n / planned | success | pair success | as predicted (informative, n) | unchanged vs intact |",
          "|---|---|---|---|---|---|---|---|---|"]
    for key, v in s.items():
        kind, system, name, goal = key.split(":")
        if not v.get("n"):
            md.append(f"| {kind} | {system} | {name} | {goal} | 0 / {v['n_planned']} | - | - | - | - |")
            continue
        inf = "-" if v.get("as_predicted_informative") is None else f"{v['as_predicted_informative']:.2f} ({v['n_informative']})"
        unch = "-" if "unchanged" not in v else f"{v['unchanged']:.2f}"
        md.append(f"| {kind} | {system} | {name} | {goal} | {v['n']} / {v['n_planned']} | {v['success']:.2f} | "
                  f"{v['pair_success']:.2f} | {inf} | {unch} |")
    md += ["", f"Store integrity in the decision process: cut-off store refused {data.get('refused', {}).get('cut')}, "
           f"changed store refused {data.get('refused', {}).get('changed')}.", "",
           f"VERDICT {verdict} - MILESTONE {milestone}", "",
           "Criteria (docs/ROUND_3_4.md, fixed before the first run of the code):", ""]
    md += [f"- {'PASS' if ok else 'FAIL'} {text}" for text, ok in results]
    d = Path(dest)
    (d / "CHECK.txt").write_text("\n".join(lines) + "\n")
    (d / "SUMMARY.md").write_text("\n".join(md) + "\n")
    (d / "VERDICT").write_text(verdict + "\n")
    (d / "MILESTONE").write_text(milestone + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:5]))
