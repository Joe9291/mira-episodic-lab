"""Round 3.1: run the diagnostic battery on one pinned model, both output channels.

Modes:
- direct (round 3.1): free channel = greedy generation with the v1 instruction, strict
  answer grammar; candidate channel = log-probability of every allowed answer as the
  complete reply (models.score_candidates), the highest wins. Same prompt for both.
- think (round 3.1b, Qwen3 only): thinking mode with its recommended seeded sampling,
  up to 1024 new tokens; the answer after </think> is parsed with the same grammar.
- cot (round 3.1b): step-by-step instruction, greedy, up to 384 new tokens; the text
  after the last "Answer:" is parsed with the same grammar.
Writes one JSON with every case, raw answer, parse and the summary.
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

from episodic_lab.arms import FORMAT_V1, build_messages  # noqa: E402
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


MODES = {"direct": 16, "think": 1024, "cot": 384}  # max new tokens per mode


def cot_messages(case: dict) -> list[dict]:
    text = ("You read story notes and answer one question about them. Think step by step "
            "first. Then write your final answer on a last line that starts with 'Answer:' "
            f"followed by only {FORMAT_V1[case['answer_type']]}.")
    if case["answer_type"] != "choice":
        text += (" If the notes do not contain the event the question asks about, the final "
                 "answer is the single word: none.")
    return [{"role": "system", "content": text},
            {"role": "user", "content": f"Story notes:\n" + "\n".join(case["notes"])
             + f"\n\nQuestion: {case['question']}"}]


def cot_answer(text: str) -> str:
    """Text after the last 'Answer:' (case-insensitive); empty if there is none."""
    pos = text.lower().rfind("answer:")
    return text[pos + len("answer:"):].strip() if pos >= 0 else ""


def run_case(model, case: dict, mode: str = "direct") -> dict:
    if mode == "think":
        messages = build_messages(case["question"], case["notes"], case["answer_type"], STYLE)
        r = model.generate_reasoning(messages, seed=int(case["cid"][1:9], 16))
        kind, value = parse(r["answer"], case["answer_type"], candidate_names(case))
        return {"cid": case["cid"], "skill": case["skill"], "kind": case["kind"],
                "pair": case.get("pair"), "gold": case["gold"],
                "free": {"raw": r["answer"], "parsed": kind, "value": value,
                         "new_tokens": r["new_tokens"], "finished": r["finished"],
                         "correct": free_correct(case, kind, value)}}
    if mode == "cot":
        full = model.generate(cot_messages(case))
        answer = cot_answer(full)
        kind, value = parse(answer, case["answer_type"], candidate_names(case))
        return {"cid": case["cid"], "skill": case["skill"], "kind": case["kind"],
                "pair": case.get("pair"), "gold": case["gold"],
                "free": {"raw": full, "answer": answer, "parsed": kind, "value": value,
                         "correct": free_correct(case, kind, value)}}
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
    ap.add_argument("--mode", default="direct", choices=sorted(MODES))
    ap.add_argument("--skills", default="S1,S2,S3,S4,S5")
    args = ap.parse_args()
    battery = build_battery()
    skills = args.skills.split(",")
    cases = [c for c in battery["cases"] if c["skill"] in skills]
    out = {"schema": SCHEMA, "model": args.model, "mode": args.mode, "skills": skills,
           "style": STYLE, "status": "ERROR",
           "code_commit": os.environ.get("GITHUB_SHA", "local"),
           "battery_seed": battery["seed"], "n_cases": len(cases), "rows": []}
    t0 = time.perf_counter()
    try:
        from episodic_lab.models import PinnedModel
        model = PinnedModel(args.model, args.pins, max_new_tokens=MODES[args.mode],
                            thinking=args.mode == "think")
        out.update({"revision": model.revision, "weights_digest": model.weights_digest()})
        for case in cases:
            out["rows"].append(run_case(model, case, args.mode))
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
