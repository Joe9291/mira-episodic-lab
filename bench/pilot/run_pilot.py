"""Pilot cell: one model, one arm, one world (both overlap conditions).

Writes a JSON result with every raw answer, the scored rows, summaries, E6 inputs,
timing and token telemetry, plus the symbolic arm's result on the same world as a
reference. On any failure the result keeps what was done and status ERROR; the exit
code is then non-zero.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from episodic_lab.arms import ARMS  # noqa: E402
from episodic_lab.questions import make_world  # noqa: E402
from episodic_lab.runner import retention, run_world  # noqa: E402
from episodic_lab.symbolic import SymbolicMemory  # noqa: E402


def run_cell(model, arm: str, series: str, index: int, out: dict) -> None:
    attempt, pair = make_world(series, index)
    out.update({"series": series, "index": index, "attempt": attempt, "conditions": {}})
    for overlap, (world, questions) in pair.items():
        t0 = time.perf_counter()
        before = dict(model.stats)
        result = run_world(ARMS[arm](model), world, questions)
        reference = run_world(SymbolicMemory(), world, questions)
        out["conditions"][overlap] = {
            "seed": world["seed"], "seconds": round(time.perf_counter() - t0, 1),
            "telemetry": {k: model.stats[k] - before[k] for k in model.stats},
            "phase1": result["phase1"], "final": result["final"],
            "retention": retention(result), "rows": result["rows"],
            "episodes_presented": result["episodes_presented"],
            "symbolic_all_correct": all(r["correct"] for r in reference["rows"])}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--arm", required=True, choices=sorted(ARMS))
    parser.add_argument("--series", required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--pins", default="config/model_pins.json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = {"schema": "episodic_lab.pilot_cell.v1", "model": args.model, "arm": args.arm,
           "status": "ERROR"}
    t0 = time.perf_counter()
    try:
        from episodic_lab.models import PinnedModel
        model = PinnedModel(args.model, args.pins)
        out.update({"repo": model.repo, "revision": model.revision,
                    "weights_digest": model.weights_digest()})
        run_cell(model, args.arm, args.series, args.index, out)
        out["status"] = "OK"
    except Exception:
        out["traceback"] = traceback.format_exc()[-4000:]
    out["total_seconds"] = round(time.perf_counter() - t0, 1)
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "conditions"}, sort_keys=True))
    return 0 if out["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
