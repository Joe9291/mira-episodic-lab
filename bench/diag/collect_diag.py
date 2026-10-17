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


def validate(data, model: str, cids: set, mode: str = "direct") -> list:
    if not isinstance(data, dict):
        return ["not_an_object"]
    problems = []
    if data.get("schema") != SCHEMA:
        problems.append("schema")
    if data.get("model") != model or data.get("mode", "direct") != mode:
        problems.append("identity")
    if data.get("status") != "OK":
        return problems + ["status"]
    rows = data.get("rows")
    if not isinstance(rows, list) or sorted(r.get("cid") for r in rows) != sorted(cids):
        return problems + ["cases"]
    for r in rows:
        if not isinstance(r.get("free", {}).get("correct"), bool):
            return problems + ["row"]
        if mode == "direct" and not (
                isinstance(r.get("cand", {}).get("correct"), bool)
                and r["cand"]["correct"] == (r["cand"].get("choice") == r.get("gold"))):
            return problems + ["row"]
    if json.dumps(data.get("summary"), sort_keys=True) != json.dumps(summarise(rows), sort_keys=True):
        problems.append("summary_vs_rows")
    return problems


def table(results: dict) -> str:
    lines = ["# Round 3.1 diagnostic battery (exploratory)", "",
             f"Development target per sub-skill and channel: {TARGET}. Below target -> the "
             "prototype solves that sub-skill with an explicit operator (docs/STRATEGY.md).",
             "free = generated text, strict grammar; cand = highest-likelihood allowed answer.",
             "Modes: direct (no reasoning), think (Qwen3 thinking mode), cot (step-by-step "
             "instruction); reasoning modes have no candidate channel.",
             "", "| model | mode | skill | n | free | cand | free by kind | cand by kind | pairs | meets target |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for (model, mode), data in sorted(results.items()):
        for skill in SKILLS:
            if skill not in data["summary"]:
                continue
            s = data["summary"][skill]
            has = [ch for ch in ("free", "cand") if ch in s]
            kinds = {ch: ", ".join(f"{k} {v:.2f}" for k, v in s[f"{ch}_by_kind"].items()) for ch in has}
            pairs = "; ".join(f"{ch} " + ", ".join(f"{k} {v:.2f}" for k, v in s[f"{ch}_pairs"].items())
                              for ch in has) if skill == "S2" else ""
            meets = "+".join(ch for ch in has if s[ch] >= TARGET)
            cell = lambda ch, fmt: fmt(ch) if ch in s else "-"
            lines.append(f"| {model} | {mode} | {skill} | {s['n']} | {s['free']:.2f} | "
                         f"{cell('cand', lambda c: f'{s[c]:.2f}')} | {kinds['free']} | "
                         f"{kinds.get('cand', '-')} | {pairs} | {meets or 'no'} |")
    return "\n".join(lines) + "\n"


def main(entries: list, dest: str) -> int:
    """entries: "model" (direct, all skills) or "model:mode:S2+S3+..." (reasoning probe)."""
    battery = build_battery()["cases"]
    dest_path, results, lines = Path(dest), {}, []
    for entry in entries:
        parts = entry.split(":")
        model, mode = parts[0], parts[1] if len(parts) > 1 else "direct"
        skills = set(parts[2].split("+")) if len(parts) > 2 else set(SKILLS)
        cids = {c["cid"] for c in battery if c["skill"] in skills}
        name = f"diag_{model}.json" if mode == "direct" else f"diag_{model}_{mode}.json"
        try:
            data = json.loads((dest_path / name).read_text())
            problems = validate(data, model, cids, mode)
        except Exception as exc:
            data, problems = None, [f"unreadable:{type(exc).__name__}"]
        lines.append(f"{'OK' if not problems else 'FAILED'} {name} {' '.join(problems)}".rstrip())
        if not problems:
            results[(model, mode)] = data
    ok = len(results) == len(entries)
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
