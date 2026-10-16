"""Completeness check and summary of a pilot run (used by the workflow's collector).

Never raises for a bad cell: every expected cell is listed in CHECK.txt as OK or FAILED
with reasons, VERDICT is COMPLETE only if all are OK, and SUMMARY.md gives per model and
arm the mean over worlds of the final-test accuracy per criterion (both overlap
conditions), the E5 answer categories and the E6 inputs. Exploratory pilot numbers.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        return None, [f"unreadable:{type(exc).__name__}"]
    if not isinstance(data, dict):
        return None, ["not_an_object"]
    problems = []
    if data.get("status") != "OK":
        problems.append("status")
    conds = data.get("conditions")
    if not isinstance(conds, dict) or set(conds) != {"high", "low"}:
        problems.append("conditions")
    else:
        for name, c in conds.items():
            if not isinstance(c, dict) or not c.get("rows"):
                problems.append(f"rows:{name}")
            elif c.get("symbolic_all_correct") is not True:
                problems.append(f"reference:{name}")
    return data, problems


def mean(values):
    return sum(values) / len(values) if values else float("nan")


def summarise(cells: dict) -> str:
    lines = ["# Pilot summary (exploratory)", "",
             "Mean over worlds and both overlap conditions, final test. E5 = correct rejections.",
             ""]
    groups = {}
    for (model, arm, index), data in cells.items():
        groups.setdefault((model, arm), []).append(data)
    criteria = ["E2", "E3a", "E3b", "E4", "E5", "E7"]
    lines.append("| model | arm | worlds | " + " | ".join(criteria)
                 + " | E5 false recall | E5 other | E6 phase1 | E6 final high | E6 final low |")
    lines.append("|" + "---|" * (len(criteria) + 8))
    for (model, arm), datas in sorted(groups.items()):
        row = [model, arm, str(len(datas))]
        for c in criteria:
            row.append(f"{mean([d['conditions'][o]['final'][c]['accuracy'] for d in datas for o in ('high', 'low') if c in d['conditions'][o]['final']]):.2f}")
        e5 = [d["conditions"][o]["final"]["E5"] for d in datas for o in ("high", "low") if "E5" in d["conditions"][o]["final"]]
        row.append(f"{mean([x['false_recall'] for x in e5]):.2f}")
        row.append(f"{mean([x['categories']['other'] for x in e5]):.2f}")
        row.append(f"{mean([d['conditions'][o]['retention']['phase1'] for d in datas for o in ('high', 'low')]):.2f}")
        row.append(f"{mean([d['conditions']['high']['retention']['final'] for d in datas]):.2f}")
        row.append(f"{mean([d['conditions']['low']['retention']['final'] for d in datas]):.2f}")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def main(request_path: str, dest: str) -> int:
    request = json.loads(Path(request_path).read_text())
    dest_path = Path(dest)
    lines, ok, cells = [], True, {}
    for m in request["models"]:
        for a in request["arms"]:
            for i in request["indices"]:
                name = f"pilot_{m}_{a}_{i}.json"
                try:
                    data, problems = load(dest_path / name)
                except Exception as exc:  # never let the registration fail
                    data, problems = None, [f"check_error:{type(exc).__name__}"]
                if not problems:
                    cells[(m, a, i)] = data
                ok = ok and not problems
                lines.append(f"{'OK' if not problems else 'FAILED'} {name} {' '.join(problems)}".rstrip())
    (dest_path / "CHECK.txt").write_text("\n".join(lines) + "\n")
    (dest_path / "VERDICT").write_text("COMPLETE\n" if ok else "INCOMPLETE\n")
    try:
        (dest_path / "SUMMARY.md").write_text(summarise(cells))
    except Exception as exc:
        (dest_path / "SUMMARY.md").write_text(f"summary failed: {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
