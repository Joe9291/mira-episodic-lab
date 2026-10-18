"""Round 3.5 encode job (docs/ROUND_3_5.md section 4): the only part that runs a model.

  --phase timing  a fixed development slice (2 pairs per kind plus the 20 development
                  texts with the most candidates), cached scoring timed per text, and for
                  the first 10 texts the uncached scores as well (cache check)
  --phase probe   a small stratified development slice (4 distinct texts per development
                  wording frame) for quick development iterations
  --phase encode  every distinct text of a split, in chunks (texts[chunk::chunks])

The output keeps every scored surface candidate with its canonical value and score; all
decisions are derived later and model-free (episodic_lab/analysis35.py).
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

from episodic_lab.cands35 import CANDIDATE_VERSION, SLOTS, candidates, ranking  # noqa: E402
from episodic_lab.encoder35 import NULL_NOTE, encode_text, messages  # noqa: E402
from episodic_lab.env35 import KINDS35, split_pairs  # noqa: E402

SCHEMA = "episodic_lab.round35_encode.v1"
CACHE_TOLERANCE = 1e-3


def split_texts(split: str) -> list[str]:
    return sorted({e["text"] for p in split_pairs(split) for w in p["worlds"].values() for e in w["experiences"]})


def timing_texts() -> list[str]:
    pairs = split_pairs("dev")
    chosen = {e["text"] for kind in KINDS35 for p in [x for x in pairs if x["kind"] == kind][:2]
              for w in p["worlds"].values() for e in w["experiences"]}
    longest = sorted(split_texts("dev"), key=lambda t: (-sum(len(candidates(s, t)) for s in SLOTS), t))[:20]
    return sorted(chosen | set(longest))


def probe_texts(per_frame: int = 4) -> list[str]:
    frames = {}
    for p in split_pairs("dev"):
        for w in p["worlds"].values():
            for e in w["experiences"]:
                frames.setdefault(e["frame"], set()).add(e["text"])
    return sorted(t for f in sorted(frames) for t in sorted(frames[f])[:per_frame])


class NullScores:
    """Scores without the note ("(no note)"), cached per (slot, surface) within the job."""
    def __init__(self, model, prompt: str = "p2"):
        self.model, self.cache, self.prompt = model, {}, prompt

    def __call__(self, slot: str, surfaces: list[str]) -> list[float]:
        todo = [s for s in dict.fromkeys(surfaces) if (slot, s) not in self.cache]
        if todo:
            for s, x in zip(todo, self.model.score_candidates_cached(messages(slot, NULL_NOTE, self.prompt), todo)):
                self.cache[(slot, s)] = x
        return [self.cache[(slot, s)] for s in surfaces]


def cache_check(model, texts: list[str]) -> dict:
    """Cached vs uncached scores on the same candidates: largest absolute difference and
    whether every slot's best canonical value is the same."""
    worst, same = 0.0, True
    for text in texts:
        for slot in SLOTS:
            surf = candidates(slot, text)
            a = model.score_candidates_cached(messages(slot, text), [s for s, _ in surf])
            b = model.score_candidates(messages(slot, text), [s for s, _ in surf])
            worst = max(worst, max(abs(x - y) for x, y in zip(a, b)))
            ra = ranking([(s, c, x) for (s, c), x in zip(surf, a)])[0]
            rb = ranking([(s, c, x) for (s, c), x in zip(surf, b)])[0]
            same &= ra == rb
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
    ap.add_argument("--request", default="config/round35.json")
    ap.add_argument("--prompt", default="p2")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    slug, _, variant_prompt = args.model.partition("+")
    if variant_prompt:
        args.prompt = variant_prompt
    out = {"schema": SCHEMA, "phase": args.phase, "model": args.model, "split": args.split, "chunk": args.chunk,
           "chunks": args.chunks, "prompt_version": args.prompt, "candidate_version": CANDIDATE_VERSION,
           "status": "ERROR",
           "provenance": {"code_commit": os.environ.get("GITHUB_SHA", "local"),
                          "request_sha256": hashlib.sha256(Path(args.request).read_bytes()).hexdigest(),
                          "pins_sha256": hashlib.sha256(Path(args.pins).read_bytes()).hexdigest()}}
    try:
        from episodic_lab.models import PinnedModel
        t0 = time.perf_counter()
        model = PinnedModel(slug, args.pins)
        out["load_seconds"] = round(time.perf_counter() - t0, 1)
        out["weights_sha256"] = model.weights_digest()
        texts = (timing_texts() if args.phase == "timing" else probe_texts() if args.phase == "probe"
                 else split_texts(args.split)[args.chunk::args.chunks])
        encodings, seconds = {}, {}
        nulls = NullScores(model, args.prompt)
        ntok = (lambda s: model.count_tokens(s) + 1)
        for text in texts:
            t = time.perf_counter()
            encodings[text] = encode_text(model.score_candidates_cached, text, nulls, ntok, args.prompt)
            seconds[text] = round(time.perf_counter() - t, 3)
        out.update(encodings=encodings, seconds=seconds, texts=len(texts))
        if args.phase == "timing":
            t = time.perf_counter()
            out["cache_check"] = cache_check(model, texts[:10])
            out["cache_check"]["seconds"] = round(time.perf_counter() - t, 1)
            out["candidates_per_text"] = {text: sum(len(candidates(s, text)) for s in SLOTS) for text in texts}
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
