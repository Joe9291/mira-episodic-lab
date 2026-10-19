"""Round 3.6 parse job (docs/ROUND_3_6.md): the only part that runs a model.

  --phase timing  40 development question texts, cached scoring timed per text, cache check
  --phase probe   2 development texts per development wording (quick development iterations)
  --phase encode  every distinct question text of a split, in chunks (texts[chunk::chunks])

The output keeps every scored candidate with its canonical value and score; every outcome
is derived later and model-free (episodic_lab/parser36.py, analysis36.py).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench" / "m3"))

from episodic_lab.cands35 import ranking  # noqa: E402
from episodic_lab.env36 import split_pairs  # noqa: E402
from episodic_lab.parser36 import SLOTS, candidates, encode_question, messages  # noqa: E402

SCHEMA = "episodic_lab.round36_parse.v1"
CACHE_TOLERANCE = 1e-3


def split_texts(split: str) -> list[str]:
    """Every distinct question text of the split (texts repeated from earlier splits included:
    their parses are reused for the task metrics)."""
    return sorted({q["text"] for p in split_pairs(split) for q in p["questions"]})


def probe_texts(per_wording: int = 2) -> list[str]:
    by = {}
    for p in split_pairs("dev"):
        for q in p["questions"]:
            by.setdefault(q["wording"], set()).add(q["text"])
    return sorted(t for w in sorted(by) for t in sorted(by[w])[:per_wording])


def timing_texts() -> list[str]:
    return probe_texts(1)[:40]


def scorer_of(model):
    return getattr(model, "score_candidates_prefixed", None) or model.score_candidates_cached


def cache_check(model, texts: list[str], prompt: str) -> dict:
    worst, same = 0.0, True
    for text in texts:
        for slot in SLOTS:
            surf = candidates(slot, text)
            a = scorer_of(model)(messages(slot, text, prompt), [s for s, _ in surf])
            b = model.score_candidates(messages(slot, text, prompt), [s for s, _ in surf])
            worst = max(worst, max(abs(x - y) for x, y in zip(a, b)))
            same &= ranking([(s, c, x) for (s, c), x in zip(surf, a)])[0] == ranking(
                [(s, c, x) for (s, c), x in zip(surf, b)])[0]
    return {"texts": len(texts), "max_abs_diff": worst, "same_choices": same,
            "ok": same and worst <= CACHE_TOLERANCE, "tolerance": CACHE_TOLERANCE}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("timing", "probe", "encode"), required=True)
    ap.add_argument("--model", required=True, help="a model slug, or a variant 'slug+prompt'")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--chunk", type=int, default=0)
    ap.add_argument("--chunks", type=int, default=1)
    ap.add_argument("--pins", default="config/model_pins.json")
    ap.add_argument("--request", default="config/round36.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    slug, _, prompt = args.model.partition("+")
    prompt = prompt or "q1"
    out = {"schema": SCHEMA, "phase": args.phase, "model": args.model, "split": args.split, "chunk": args.chunk,
           "chunks": args.chunks, "prompt_version": prompt, "status": "ERROR",
           "provenance": {"code_commit": os.environ.get("GITHUB_SHA", "local"),
                          "request_sha256": hashlib.sha256(Path(args.request).read_bytes()).hexdigest(),
                          "pins_sha256": hashlib.sha256(Path(args.pins).read_bytes()).hexdigest()}}
    try:
        if args.phase == "encode":   # a frozen request must match the code before any model work
            import freeze36
            problems = freeze36.check(json.loads(Path(args.request).read_text()).get("frozen"))
            if problems:
                raise RuntimeError("frozen configuration does not match the code: " + "; ".join(problems))
        from episodic_lab.models import PinnedModel
        t0 = time.perf_counter()
        model = PinnedModel(slug, args.pins)
        out["load_seconds"] = round(time.perf_counter() - t0, 1)
        out["weights_sha256"] = model.weights_digest()
        texts = (timing_texts() if args.phase == "timing" else probe_texts() if args.phase == "probe"
                 else split_texts(args.split)[args.chunk::args.chunks])
        encodings, seconds = {}, {}
        ntok = (lambda s: model.count_tokens(s) + 1)
        for text in texts:
            t = time.perf_counter()
            encodings[text] = encode_question(scorer_of(model), text, ntok, prompt)
            seconds[text] = round(time.perf_counter() - t, 3)
        out.update(encodings=encodings, seconds=seconds, texts=len(texts))
        if args.phase in ("timing", "probe"):
            t = time.perf_counter()
            out["cache_check"] = cache_check(model, texts[:10] if args.phase == "timing" else texts[:3], prompt)
            out["cache_check"]["seconds"] = round(time.perf_counter() - t, 1)
        if model.weights_digest(recompute=True) != out["weights_sha256"]:
            raise RuntimeError("weights changed")
        out["status"] = "OK"
    except Exception as exc:  # recorded, the collector decides
        import traceback
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["traceback"] = traceback.format_exc()[-3000:]
    Path(args.out).write_text(json.dumps(out, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
