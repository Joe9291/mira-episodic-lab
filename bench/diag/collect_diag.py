"""Collector of round 3.1: checks every model's result and writes CHECK.txt, VERDICT and
SUMMARY.md with the decision table (sub-skill x channel against the development target).

A result is OK only if: status OK, the expected model, every battery case present exactly
once (same case ids as the battery built from this code), and the stored summary equal to
the summary recomputed here from the rows.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from episodic_lab.diagnostics import SKILLS, TARGET, build_battery, summarise  # noqa: E402

SCHEMA = "episodic_lab.diag_result.v1"


def validate(data, model: str, cids: set) -> list:
    if not isinstance(data, dict):
        return ["not_an_object"]
    problems = []
    if data.get("schema") != SCHEMA:
        problems.append("schema")
    if data.get("model") != model:
        problems.append("identity")
    if data.get("status") != "OK":
        return problems + ["status"]
    rows = data.get("rows")
    if not isinstance(rows, list) or sorted(r.get("cid") for r in rows) != sorted(cids):
        return problems + ["cases"]
    for r in rows:
        if not (isinstance(r.get("free", {}).get("correct"), bool)
                and isinstance(r.get("cand", {}).get("correct"), bool)
                and r["cand"].get("correct") == (r["cand"].get("choice") == r.get("gold"))):
            return problems + ["row"]
    if json.dumps(data.get("summary"), sort_keys=True) != json.dumps(summarise(rows), sort_keys=True):
        problems.append("summary_vs_rows")
    return problems


def table(results: dict) -> str:
    lines = ["# Round 3.1 diagnostic battery (exploratory)", "",
             f"Development target per sub-skill and channel: {TARGET}. Below target -> the "
             "prototype solves that sub-skill with an explicit operator (docs/STRATEGY.md).",
             "free = generated text, strict grammar; cand = highest-likelihood allowed answer.",
             "", "| model | skill | n | free | cand | free by kind | cand by kind | meets target |",
             "|---|---|---|---|---|---|---|---|"]
    for model, data in sorted(results.items()):
        for skill in SKILLS:
            s = data["summary"][skill]
            kinds = lambda ch: ", ".join(f"{k} {v:.2f}" for k, v in s[f"{ch}_by_kind"].items())
            extra = ""
            if skill == "S2":
                extra = " | pairs free " + ", ".join(f"{k} {v:.2f}" for k, v in s["free_pairs"].items()) \
                        + "; cand " + ", ".join(f"{k} {v:.2f}" for k, v in s["cand_pairs"].items())
            meets = "free" if s["free"] >= TARGET else ""
            meets += ("+" if meets else "") + "cand" if s["cand"] >= TARGET else ""
            lines.append(f"| {model} | {skill} | {s['n']} | {s['free']:.2f} | {s['cand']:.2f} | "
                         f"{kinds('free')} | {kinds('cand')}{extra} | {meets or 'no'} |")
    return "\n".join(lines) + "\n"


def main(models: list, dest: str) -> int:
    cids = {c["cid"] for c in build_battery()["cases"]}
    dest_path, results, lines = Path(dest), {}, []
    for m in models:
        name = f"diag_{m}.json"
        try:
            data = json.loads((dest_path / name).read_text())
            problems = validate(data, m, cids)
        except Exception as exc:
            data, problems = None, [f"unreadable:{type(exc).__name__}"]
        lines.append(f"{'OK' if not problems else 'FAILED'} {name} {' '.join(problems)}".rstrip())
        if not problems:
            results[m] = data
    ok = len(results) == len(models)
    try:
        (dest_path / "SUMMARY.md").write_text(table(results))
    except Exception as exc:
        ok = False
        lines.append(f"FAILED SUMMARY.md {type(exc).__name__}")
    (dest_path / "CHECK.txt").write_text("\n".join(lines) + "\n")
    (dest_path / "VERDICT").write_text("COMPLETE\n" if ok else "INCOMPLETE\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[2].split(","), sys.argv[1]))
