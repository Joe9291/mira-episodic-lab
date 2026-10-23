#!/usr/bin/env python3
"""Round 4.2 encode job (docs/ROUND_4_2.md): the only part that runs a model.

  --phase timing  a fixed development slice (3 notes per gold note type and frame-set
                  position), timed per note, plus a cache check on 5 notes
  --phase probe   a stratified development slice (4 notes per gold type and frame)
  --phase encode  every distinct note of a split, in chunks (notes[chunk::chunks])
  --phase prior   no notes: only the label priors (every phase records them as well)

Output: every scored surface candidate of every slot with its canonical value and score;
all decisions are taken later and model-free.
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

from episodic_lab.cands42 import CANDIDATE_VERSION, SLOTS, candidates, ranking  # noqa: E402
from episodic_lab.encoder42 import CONTENT_FREE, CURRENT, LABEL_REENCODED, candidate_text, encode_note, label_priors, messages  # noqa: E402
from episodic_lab import r42_world as W  # noqa: E402

SCHEMA = "episodic_lab.round42_encode.v1"
CACHE_TOLERANCE = 1e-3


def note_key(header, text, ctx) -> str:
    return hashlib.sha256(json.dumps([header, text, ctx["author"], ctx["report_day"], sorted(ctx["sources"])],
                                     separators=(",", ":")).encode()).hexdigest()[:24]


def split_notes(split: str) -> list[dict]:
    """Distinct notes of a split with their context and gold type/frame (gold fields are
    used only for slicing the timing / probe sets, never by the encoder)."""
    out = {}
    for p in W.iter_pairs(split):
        for inst in p["instances"]:
            for w in ("A", "B"):
                for n in inst[w]["notes"]:
                    ctx = {"author": n["author"], "report_day": n["report_day"], "sources": p["sources"]}
                    k = note_key(n["header"], n["text"], ctx)
                    out.setdefault(k, {"key": k, "header": n["header"], "text": n["text"], "ctx": ctx,
                                       "gold_type": n["gold_type"], "frame": n["frame"]})
    return [out[k] for k in sorted(out)]


def stratified(notes, per_cell):
    cells = {}
    for n in notes:
        cells.setdefault((n["gold_type"], n["frame"]), []).append(n)
    return [n for c in sorted(cells) for n in cells[c][:per_cell]]


def scorer_of(model):
    return getattr(model, "score_candidates_prefixed", None) or model.score_candidates_cached


def cache_check(model, notes, prompt, slots=None):
    worst, same = 0.0, True
    for n in notes:
        full = candidate_text(n["header"], n["text"], prompt)
        for slot in (slots or SLOTS):
            surf = candidates(slot, full, n["ctx"])
            if not surf:
                continue
            msgs = messages(slot, n["header"], n["text"], prompt)
            a = scorer_of(model)(msgs, [s for s, _ in surf])
            b = model.score_candidates(msgs, [s for s, _ in surf])
            worst = max(worst, max(abs(x - y) for x, y in zip(a, b)))
            same &= ranking([(s, c, x) for (s, c), x in zip(surf, a)])[0] == ranking([(s, c, x) for (s, c), x in zip(surf, b)])[0]
    return {"notes": len(notes), "max_abs_diff": worst, "same_choices": same,
            "ok": same and worst <= CACHE_TOLERANCE, "tolerance": CACHE_TOLERANCE}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("timing", "probe", "encode", "prior"), required=True)
    ap.add_argument("--model", required=True, help="slug or 'slug+prompt'")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--chunk", type=int, default=0)
    ap.add_argument("--chunks", type=int, default=1)
    ap.add_argument("--pins", default="config/model_pins.json")
    ap.add_argument("--request", default="config/round42.json")
    ap.add_argument("--slots", default="", help="development probes only: comma-separated slots")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    slug, _, prompt = args.model.partition("+")
    prompt = prompt or CURRENT
    out = {"schema": SCHEMA, "phase": args.phase, "model": args.model, "split": args.split, "chunk": args.chunk,
           "chunks": args.chunks, "prompt_version": prompt, "candidate_version": CANDIDATE_VERSION,
           "generator_version": W.GENERATOR_VERSION, "status": "ERROR", "slots": args.slots or "all",
           "provenance": {"code_commit": os.environ.get("GITHUB_SHA", "local"),
                          "request_sha256": hashlib.sha256(Path(args.request).read_bytes()).hexdigest(),
                          "pins_sha256": hashlib.sha256(Path(args.pins).read_bytes()).hexdigest()}}
    try:
        slots = [x for x in args.slots.split(",") if x] or None
        request = json.loads(Path(args.request).read_text())
        if slots and args.phase == "encode" and not (request.get("label_reencode") is True
                                                    and sorted(slots) == sorted(LABEL_REENCODED)):
            raise RuntimeError("--slots in the encode phase only for the label re-encode of option B "
                               f"(label_reencode: true, slots {','.join(LABEL_REENCODED)})")
        if prompt != CURRENT:
            raise RuntimeError(f"prompt {prompt} belongs to an earlier candidate version; current: {CURRENT} / "
                               f"{CANDIDATE_VERSION}")
        if args.split == "holdout":
            raise RuntimeError("the holdout is encoded only after the freeze (not implemented in this job yet)")
        notes = split_notes(args.split)
        if args.phase == "timing":
            notes = stratified(notes, 1)
        elif args.phase == "probe":
            notes = stratified(notes, 4)
        elif args.phase == "prior":
            notes = []
        else:
            notes = notes[args.chunk::args.chunks]
        from episodic_lab.models import PinnedModel
        t0 = time.perf_counter()
        model = PinnedModel(slug, args.pins)
        out["load_seconds"] = round(time.perf_counter() - t0, 1)
        out["weights_sha256"] = model.weights_digest()
        t = time.perf_counter()
        out["priors"] = label_priors(scorer_of(model), prompt)
        out["prior_notes"] = list(CONTENT_FREE)
        out["prior_seconds"] = round(time.perf_counter() - t, 1)
        enc, secs = {}, {}
        for n in notes:
            t = time.perf_counter()
            enc[n["key"]] = encode_note(scorer_of(model), n["header"], n["text"], n["ctx"], prompt, slots)
            secs[n["key"]] = round(time.perf_counter() - t, 3)
        out.update(encodings=enc, seconds=secs, notes=len(notes),
                   index={n["key"]: {"header": n["header"], "text": n["text"], "ctx": n["ctx"]} for n in notes})
        if args.phase in ("timing", "probe"):
            t = time.perf_counter()
            out["cache_check"] = cache_check(model, notes[:5], prompt, slots)
            out["cache_check"]["seconds"] = round(time.perf_counter() - t, 1)
        if model.weights_digest(recompute=True) != out["weights_sha256"]:
            raise RuntimeError("weights changed")
        out["status"] = "OK"
    except Exception as exc:
        import traceback
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["traceback"] = traceback.format_exc()[-3000:]
    Path(args.out).write_text(json.dumps(out, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
