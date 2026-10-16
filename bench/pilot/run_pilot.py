"""Pilot cell: one model, one arm, one world (both overlap conditions).

Writes a JSON result with every raw answer, the scored rows (each with its prompt length,
answer length and a truncation flag), summaries, E6 inputs, timing and token telemetry,
E1b processing counts per episode, provenance (code commit, SHA-256 of the pilot request
and of the pins manifest, SHA-256 of every world and question set), plus whether the
symbolic arm solves the same world (reference). On any failure the result keeps what was
done (finished conditions, raw answers of finished test phases under "partial") and
status ERROR; the exit code is then non-zero.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from episodic_lab.arms import ARMS  # noqa: E402
from episodic_lab.questions import make_world  # noqa: E402
from episodic_lab.runner import retention, run_world  # noqa: E402
from episodic_lab.symbolic import SymbolicMemory  # noqa: E402

SCHEMA = "episodic_lab.pilot_cell.v2"


def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inclusion_summary(counts: dict) -> dict:
    values = list(counts.values())
    return {"episodes": len(values), "total": sum(values), "min": min(values),
            "max": max(values), "mean": sum(values) / len(values)}


def run_cell(model, arm: str, series: str, index: int, out: dict) -> None:
    attempt, pair = make_world(series, index)
    out.update({"series": series, "index": index, "attempt": attempt, "conditions": {},
                "partial": {}})
    for overlap, (world, questions) in pair.items():
        t0 = time.perf_counter()
        before = dict(model.stats)
        first_call = len(model.call_log)
        out["partial"][overlap] = {}
        result = run_world(ARMS[arm](model), world, questions,
                           on_phase=lambda phase, answers: out["partial"][overlap].update({phase: answers}))
        calls = model.call_log[first_call:]
        if len(calls) != len(result["asked"]):
            raise RuntimeError(f"{len(calls)} model calls for {len(result['asked'])} questions")
        per_answer = {tuple(k): c for k, c in zip(map(tuple, result["asked"]), calls)}
        for row in result["rows"]:
            row.update(per_answer[(row["phase"], row["qid"])])
        reference = run_world(SymbolicMemory(), world, questions)
        processing = result["processing"]
        tokens = {e["episode_id"]: model.count_tokens(e["text"]) for e in world["episodes"]}
        processing["episode_tokens"] = tokens
        processing["prompt_tokens_per_episode"] = {
            k: n * tokens[k] for k, n in processing["prompt_inclusions"].items()}
        out["conditions"][overlap] = {
            "seed": world["seed"], "seconds": round(time.perf_counter() - t0, 1),
            "world_sha256": canonical_sha256(world),
            "questions_sha256": canonical_sha256(questions),
            "telemetry": {k: model.stats[k] - before[k] for k in model.stats},
            "phase1": result["phase1"], "final": result["final"],
            "retention": retention(result), "rows": result["rows"],
            "episodes_presented": result["episodes_presented"],
            "processing": dict(processing,
                               prompt_inclusion_summary=inclusion_summary(processing["prompt_inclusions"])),
            "symbolic_all_correct": all(r["correct"] for r in reference["rows"])}
        del out["partial"][overlap]
    del out["partial"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--arm", required=True, choices=sorted(ARMS))
    parser.add_argument("--series", required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--pins", default="config/model_pins.json")
    parser.add_argument("--request", default="config/pilot.json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = {"schema": SCHEMA, "model": args.model, "arm": args.arm, "series": args.series,
           "index": args.index, "status": "ERROR",
           "provenance": {"code_commit": os.environ.get("GITHUB_SHA", "local"),
                          "request_sha256": file_sha256(args.request),
                          "pins_sha256": file_sha256(args.pins)}}
    t0 = time.perf_counter()
    try:
        from episodic_lab.models import PinnedModel
        model = PinnedModel(args.model, args.pins)
        out.update({"repo": model.repo, "revision": model.revision,
                    "max_new_tokens": model.max_new_tokens,
                    "weights_digest": model.weights_digest()})
        run_cell(model, args.arm, args.series, args.index, out)
        out["status"] = "OK"
    except Exception:
        out["traceback"] = traceback.format_exc()[-4000:]
    out["total_seconds"] = round(time.perf_counter() - t0, 1)
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("conditions", "partial")},
                     sort_keys=True))
    return 0 if out["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
