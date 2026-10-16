"""Completeness check and summary of a pilot run (used by the workflow's collector).

Never raises for a bad cell. Every expected cell (model x arm x world index of the
request) is validated against the full cell schema: identity (model, arm, series, index
must equal the matrix entry), status, provenance (code commit equal across cells, request
and pins manifest hashes equal to the files the collector holds, revision equal to the
pin), both overlap conditions, phase summaries with every criterion, finite values in
their ranges, the row structure, E1b processing counts and the symbolic reference. Across
cells, every model and arm must have seen the same world and question set for a given
index and condition. CHECK.txt lists every cell as OK or FAILED with reasons.

VERDICT is COMPLETE only if every cell is OK AND the summary was written; otherwise
INCOMPLETE. SUMMARY.md gives, per model and arm, means over worlds (both overlap
conditions, final test) per criterion with E3b split into at_day and latest, the E5
answer categories, the truncation rate and the E6 inputs, plus the model-selection
criterion of protocol section 5 (O1 accuracy on positive items only). O1 is diagnostic:
its evidence is supplied by the evaluator for every question, so its E5 and E6 values are
no memory results. Exploratory pilot numbers.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

SCHEMA = "episodic_lab.pilot_cell.v2"
CRITERIA = {"phase1": ("E2", "E3a", "E3b", "E4", "E5"),
            "final": ("E2", "E3a", "E3b", "E4", "E5", "E7")}
E3B_SUBTYPES = {"phase1": ("at_day",), "final": ("at_day", "latest")}
CATEGORIES = ("correct", "wrong_value", "none_answer", "uncertain", "other")
POSITIVE = ("E2", "E3a", "E3b", "E4", "E7")  # O1 selection criterion: no lures
SELECTION_THRESHOLD = 0.8
EXPOSURE = {"A0": "none", "A1": "all_presented", "O1": "evidence"}
TELEMETRY = ("calls", "prompt_tokens", "new_tokens", "truncated")
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _rate(x) -> bool:
    return _num(x) and 0.0 <= x <= 1.0


def _count(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and x >= 0


def _check_summary(summary, phase: str, rows: list, problems: list, where: str) -> None:
    if not isinstance(summary, dict) or set(summary) != set(CRITERIA[phase]):
        problems.append(f"criteria:{where}")
        return
    for c in CRITERIA[phase]:
        s = summary[c]
        sub = [r for r in rows if r.get("phase") == phase and r.get("criterion") == c]
        if (not isinstance(s, dict) or not _count(s.get("n")) or s["n"] == 0
                or s["n"] != len(sub) or not _rate(s.get("accuracy"))):
            problems.append(f"summary:{where}:{c}")
            continue
        if abs(s["accuracy"] - sum(r.get("correct") is True for r in sub) / len(sub)) > 1e-9:
            problems.append(f"summary_vs_rows:{where}:{c}")
        cats = s.get("categories")
        if (not isinstance(cats, dict) or set(cats) != set(CATEGORIES)
                or not all(_rate(v) for v in cats.values())
                or abs(sum(cats.values()) - 1.0) > 1e-9):
            problems.append(f"categories:{where}:{c}")
        if c == "E5" and not _rate(s.get("false_recall")):
            problems.append(f"false_recall:{where}")
        if c == "E3b":
            by = s.get("by_qtype")
            if (not isinstance(by, dict) or set(by) != set(E3B_SUBTYPES[phase])
                    or not all(isinstance(v, dict) and _count(v.get("n")) and v["n"] > 0
                               and _rate(v.get("accuracy")) for v in by.values())):
                problems.append(f"e3b_subtypes:{where}")


def _check_rows(rows, problems: list, where: str) -> None:
    if not isinstance(rows, list) or not rows:
        problems.append(f"rows:{where}")
        return
    seen = set()
    for r in rows:
        ok = (isinstance(r, dict) and isinstance(r.get("qid"), str)
              and isinstance(r.get("criterion"), str) and r.get("phase") in CRITERIA
              and isinstance(r.get("qtype"), str) and isinstance(r.get("raw"), str)
              and r.get("category") in CATEGORIES and isinstance(r.get("correct"), bool)
              and isinstance(r.get("false_recall"), bool)
              and isinstance(r.get("truncated"), bool)
              and _count(r.get("new_tokens")) and _count(r.get("prompt_tokens"))
              and r["correct"] == (r["category"] == "correct"))
        if not ok:
            problems.append(f"row_structure:{where}")
            return
        key = (r["phase"], r["qid"])
        if key in seen:
            problems.append(f"row_duplicate:{where}")
            return
        seen.add(key)


def validate(data, expected: dict, request_sha: str, pins: dict | None, pins_sha: str | None) -> list:
    """All problems of one cell; an empty list means the cell is usable."""
    if not isinstance(data, dict):
        return ["not_an_object"]
    problems = []
    if data.get("schema") != SCHEMA:
        problems.append("schema")
    for key in ("model", "arm", "series", "index"):
        if data.get(key) != expected[key] or (key == "index" and isinstance(data.get(key), bool)):
            problems.append(f"identity:{key}")
    if data.get("status") != "OK":
        problems.append("status")
    if "partial" in data:
        problems.append("partial_left")
    prov = data.get("provenance")
    if not isinstance(prov, dict) or not isinstance(prov.get("code_commit"), str):
        problems.append("provenance")
    else:
        if prov.get("request_sha256") != request_sha:
            problems.append("provenance:request")
        if pins_sha is not None and prov.get("pins_sha256") != pins_sha:
            problems.append("provenance:pins")
    if not isinstance(data.get("revision"), str) or not HEX40.fullmatch(data["revision"]):
        problems.append("revision")
    elif pins is not None:
        spec = pins.get("models", {}).get(expected["model"], {})
        if data["revision"] != spec.get("revision") or data.get("repo") != spec.get("repo"):
            problems.append("revision:pin")
    if not isinstance(data.get("weights_digest"), str) or not HEX64.fullmatch(data["weights_digest"]):
        problems.append("weights_digest")
    conds = data.get("conditions")
    if not isinstance(conds, dict) or set(conds) != {"high", "low"}:
        return problems + ["conditions"]
    for name in ("high", "low"):
        c = conds[name]
        if not isinstance(c, dict):
            problems.append(f"condition:{name}")
            continue
        for key in ("world_sha256", "questions_sha256"):
            if not isinstance(c.get(key), str) or not HEX64.fullmatch(c[key]):
                problems.append(f"{key}:{name}")
        if not isinstance(c.get("seed"), str):
            problems.append(f"seed:{name}")
        if not _num(c.get("seconds")) or c["seconds"] < 0:
            problems.append(f"seconds:{name}")
        tel = c.get("telemetry")
        if not isinstance(tel, dict) or not all(_count(tel.get(k)) for k in TELEMETRY):
            problems.append(f"telemetry:{name}")
            tel = None
        rows = c.get("rows")
        _check_rows(rows, problems, name)
        rows = rows if isinstance(rows, list) and all(isinstance(r, dict) for r in rows) else []
        if tel is not None and rows:
            if tel["calls"] != len(rows):
                problems.append(f"calls_vs_rows:{name}")
            if tel["truncated"] != sum(r.get("truncated") is True for r in rows):
                problems.append(f"truncated_vs_rows:{name}")
        for phase in CRITERIA:
            _check_summary(c.get(phase), phase, rows, problems, f"{name}:{phase}")
        ret = c.get("retention")
        if not isinstance(ret, dict) or not all(_rate(ret.get(p)) for p in ("phase1", "final")):
            problems.append(f"retention:{name}")
        proc = c.get("processing")
        if not isinstance(proc, dict) or proc.get("exposure") != EXPOSURE.get(expected["arm"]):
            problems.append(f"processing:{name}")
        else:
            reads, incl = proc.get("encode_reads"), proc.get("prompt_inclusions")
            if (not isinstance(reads, dict) or not reads
                    or any(v != 1 for v in reads.values())
                    or not isinstance(incl, dict) or set(incl) != set(reads)
                    or not all(_count(v) for v in incl.values())):
                problems.append(f"processing_counts:{name}")
            elif expected["arm"] == "A0" and any(incl.values()):
                problems.append(f"processing_a0:{name}")
            if c.get("episodes_presented") != (len(reads) if isinstance(reads, dict) else None):
                problems.append(f"episodes_presented:{name}")
        if c.get("symbolic_all_correct") is not True:
            problems.append(f"reference:{name}")
    if (isinstance(conds.get("high"), dict) and isinstance(conds.get("low"), dict)):
        p1 = [{r.get("qid") for r in (conds[o].get("rows") or []) if isinstance(r, dict)
               and r.get("phase") == "phase1"} for o in ("high", "low")]
        if p1[0] != p1[1]:
            problems.append("phase1_items_differ")
    return problems


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else float("nan")


def _final_rows(d, overlap=None):
    return [r for o in (("high", "low") if overlap is None else (overlap,))
            for r in d["conditions"][o]["rows"] if r["phase"] == "final"]


def selection(cells: dict) -> list[str]:
    """Protocol section 5: per model, O1 accuracy over the positive final-test items of a
    world (both conditions pooled), then the mean over worlds; lures are excluded."""
    lines = ["", "## Model selection (protocol section 5): O1 on positive items only", "",
             f"Per world: share correct over final-test items {', '.join(POSITIVE)} of both "
             f"conditions (E5 lures excluded). Threshold {SELECTION_THRESHOLD}.", "",
             "| model | worlds | mean | min world | meets threshold |", "|---|---|---|---|---|"]
    per_model = {}
    for (model, arm, _), d in sorted(cells.items()):
        if arm != "O1":
            continue
        rows = [r for r in _final_rows(d) if r["criterion"] in POSITIVE]
        per_model.setdefault(model, []).append(mean(r["correct"] for r in rows))
    for model, values in sorted(per_model.items()):
        m = mean(values)
        lines.append(f"| {model} | {len(values)} | {m:.3f} | {min(values):.3f} | "
                     f"{'yes' if m >= SELECTION_THRESHOLD else 'no'} |")
    return lines


def summarise(cells: dict) -> str:
    lines = ["# Pilot summary (exploratory)", "",
             "Means over worlds and both overlap conditions, final test. E5 = correct "
             "rejections; uncertain and other answers are not rejections. Trunc = share of "
             "answers cut off by the token limit. O1 is diagnostic (evaluator-supplied "
             "evidence for every question, confusable notes for lures): its E5 and E6 "
             "columns are no memory results. A0 is the missing-evidence control with "
             "requested abstention.", ""]
    groups = {}
    for (model, arm, index), data in cells.items():
        groups.setdefault((model, arm), []).append(data)
    head = ["E2", "E3a", "E3b at_day", "E3b latest", "E4", "E5", "E7", "E5 false recall",
            "E5 uncertain", "E5 other", "trunc", "E6 phase1", "E6 final high", "E6 final low"]
    lines.append("| model | arm | worlds | " + " | ".join(head) + " |")
    lines.append("|" + "---|" * (len(head) + 3))
    for (model, arm), datas in sorted(groups.items()):
        both = [d["conditions"][o] for d in datas for o in ("high", "low")]
        row = [model, arm + (" (diagnostic)" if arm == "O1" else ""), str(len(datas))]
        for c in ("E2", "E3a"):
            row.append(f"{mean(x['final'][c]['accuracy'] for x in both):.2f}")
        for q in ("at_day", "latest"):
            row.append(f"{mean(x['final']['E3b']['by_qtype'][q]['accuracy'] for x in both):.2f}")
        for c in ("E4", "E5", "E7"):
            row.append(f"{mean(x['final'][c]['accuracy'] for x in both):.2f}")
        row.append(f"{mean(x['final']['E5']['false_recall'] for x in both):.2f}")
        row.append(f"{mean(x['final']['E5']['categories']['uncertain'] for x in both):.2f}")
        row.append(f"{mean(x['final']['E5']['categories']['other'] for x in both):.2f}")
        row.append(f"{mean(r['truncated'] for x in both for r in x['rows']):.2f}")
        row.append(f"{mean(x['retention']['phase1'] for x in both):.2f}")
        row.append(f"{mean(d['conditions']['high']['retention']['final'] for d in datas):.2f}")
        row.append(f"{mean(d['conditions']['low']['retention']['final'] for d in datas):.2f}")
        lines.append("| " + " | ".join(row) + " |")
    lines += selection(cells)
    return "\n".join(lines) + "\n"


def main(request_path: str, dest: str, pins_path: str | None = None) -> int:
    request = json.loads(Path(request_path).read_text())
    request_sha = sha256_file(request_path)
    pins = json.loads(Path(pins_path).read_text()) if pins_path else None
    pins_sha = sha256_file(pins_path) if pins_path else None
    dest_path = Path(dest)
    results, cells = {}, {}
    for m in request["models"]:
        for a in request["arms"]:
            for i in request["indices"]:
                name = f"pilot_{m}_{a}_{i}.json"
                expected = {"model": m, "arm": a, "series": request["series"], "index": i}
                try:
                    data = json.loads((dest_path / name).read_text(encoding="utf-8"))
                    problems = validate(data, expected, request_sha, pins, pins_sha)
                except (OSError, ValueError, UnicodeError) as exc:
                    data, problems = None, [f"unreadable:{type(exc).__name__}"]
                except Exception as exc:  # never let the registration fail
                    data, problems = None, [f"check_error:{type(exc).__name__}"]
                results[name] = problems
                if not problems:
                    cells[(m, a, i)] = data
    # Across cells: one code commit, and one world / question set per index and condition.
    commits = {d["provenance"]["code_commit"] for d in cells.values()}
    if len(commits) > 1:
        for (m, a, i) in cells:
            results[f"pilot_{m}_{a}_{i}.json"].append("provenance:mixed_commits")
    for i in request["indices"]:
        for o in ("high", "low"):
            hashes = {(d["conditions"][o]["world_sha256"], d["conditions"][o]["questions_sha256"])
                      for (m, a, j), d in cells.items() if j == i}
            if len(hashes) > 1:
                for (m, a, j) in cells:
                    if j == i:
                        results[f"pilot_{m}_{a}_{j}.json"].append(f"world_differs:{o}")
    lines = [f"{'OK' if not p else 'FAILED'} {n} {' '.join(p)}".rstrip() for n, p in results.items()]
    ok = all(not p for p in results.values())
    usable = {k: v for k, v in cells.items() if not results[f"pilot_{k[0]}_{k[1]}_{k[2]}.json"]}
    try:
        (dest_path / "SUMMARY.md").write_text(summarise(usable))
    except Exception as exc:
        ok = False
        lines.append(f"FAILED SUMMARY.md {type(exc).__name__}: {exc}")
        (dest_path / "SUMMARY.md").write_text(f"summary failed: {type(exc).__name__}: {exc}\n")
    (dest_path / "CHECK.txt").write_text("\n".join(lines) + "\n")
    (dest_path / "VERDICT").write_text("COMPLETE\n" if ok else "INCOMPLETE\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:4]))
