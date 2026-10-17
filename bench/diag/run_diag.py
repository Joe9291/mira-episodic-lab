"""Round 3.1: run the diagnostic battery on one pinned model, both output channels.

Free channel: greedy generation with the v1 instruction, strict answer grammar.
Candidate channel: log-probability of every allowed answer as the complete reply
(models.score_candidates); the highest wins. Same prompt for both channels. Writes one
JSON with every case, raw answer, parse, candidate scores and the summary.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from episodic_lab.arms import build_messages  # noqa: E402
from episodic_lab.diagnostics import build_battery, candidate_names, summarise  # noqa: E402
from episodic_lab.score import parse  # noqa: E402

SCHEMA = "episodic_lab.diag_result.v1"
STYLE = "v1"


def free_correct(case: dict, kind: str, value) -> bool:
    gold = case["gold"]
    if gold == "none":
        return kind == "none"
    if kind != "value":
        return False
    if case["answer_type"] == "day":
        return gold == f"Day {value}"
    return value == gold


def run_case(model, case: dict) -> dict:
    messages = build_messages(case["question"], case["notes"], case["answer_type"], STYLE)
    raw = model.generate(messages)
    kind, value = parse(raw, case["answer_type"], candidate_names(case))
    scores = model.score_candidates(messages, case["candidates"])
    best = case["candidates"][max(range(len(scores)), key=scores.__getitem__)]
    return {"cid": case["cid"], "skill": case["skill"], "kind": case["kind"],
            "pair": case.get("pair"), "gold": case["gold"],
            "free": {"raw": raw, "parsed": kind, "value": value,
                     "correct": free_correct(case, kind, value)},
            "cand": {"scores": scores, "choice": best, "correct": best == case["gold"]}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--pins", default="config/model_pins.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    battery = build_battery()
    out = {"schema": SCHEMA, "model": args.model, "style": STYLE, "status": "ERROR",
           "code_commit": os.environ.get("GITHUB_SHA", "local"),
           "battery_seed": battery["seed"], "n_cases": len(battery["cases"]), "rows": []}
    t0 = time.perf_counter()
    try:
        from episodic_lab.models import PinnedModel
        model = PinnedModel(args.model, args.pins)
        out.update({"revision": model.revision, "weights_digest": model.weights_digest()})
        for case in battery["cases"]:
            out["rows"].append(run_case(model, case))
        if model.weights_digest(recompute=True) != out["weights_digest"]:
            raise RuntimeError("weights changed")
        out["summary"] = summarise(out["rows"])
        out["status"] = "OK"
    except Exception:
        out["traceback"] = traceback.format_exc()[-4000:]
    out["seconds"] = round(time.perf_counter() - t0, 1)
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0 if out["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
