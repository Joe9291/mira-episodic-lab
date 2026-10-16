"""Completeness check of a milestone 0 run (used by the workflow's collector).

Every expected model must have a result file whose top level is a JSON object with the
right model id, status OK, a 40-hex revision and finite, positive numeric measurements
(booleans are not numbers here). Anything else - missing file, unreadable or non-object
JSON (null, a list), wrong or missing fields - makes the run INCOMPLETE. The check never
raises: it always writes CHECK.txt and VERDICT, so the run is registered either way.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

EXPECTED = {"smollm2-135m": "HuggingFaceTB/SmolLM2-135M-Instruct",
            "smollm2-360m": "HuggingFaceTB/SmolLM2-360M-Instruct",
            "qwen2.5-0.5b": "Qwen/Qwen2.5-0.5B-Instruct",
            "qwen3-0.6b": "Qwen/Qwen3-0.6B"}
NUMERIC = ("lora_step_s_median", "peak_rss_mb", "load_s", "prefill_tokens_per_s")


def _positive_number(value) -> bool:
    return (type(value) in (int, float) and math.isfinite(value) and value > 0)


def problems_of(path: Path, model: str) -> list[str]:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        return [f"unreadable:{type(exc).__name__}"]
    if not isinstance(result, dict):
        return [f"not_an_object:{type(result).__name__}"]
    found = []
    if result.get("model_id") != model:
        found.append("model_id")
    if result.get("status") != "OK":
        found.append("status")
    if not (isinstance(result.get("resolved_revision"), str)
            and re.fullmatch(r"[0-9a-f]{40}", result["resolved_revision"])):
        found.append("resolved_revision")
    found += [name for name in NUMERIC if not _positive_number(result.get(name))]
    return found


def check(dest: Path) -> bool:
    lines, complete = [], True
    for slug, model in EXPECTED.items():
        try:
            found = problems_of(dest / f"m0_{slug}.json", model)
        except Exception as exc:  # never let the registration fail
            found = [f"check_error:{type(exc).__name__}"]
        complete = complete and not found
        lines.append(f"{'OK' if not found else 'FAILED'} {slug} {' '.join(found)}".rstrip())
    (dest / "CHECK.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (dest / "VERDICT").write_text("COMPLETE\n" if complete else "INCOMPLETE\n", encoding="utf-8")
    return complete


if __name__ == "__main__":
    check(Path(sys.argv[1]))
