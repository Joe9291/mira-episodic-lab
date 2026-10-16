"""Technical smoke test of the model path (not a measurement): load a pinned model and
answer three questions about a tiny hand-written story, once without and once with the
notes. Nothing is scored; the output shows that loading, the pin check, the chat
template and greedy generation work on the runner, and how fast."""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from episodic_lab.arms import build_messages  # noqa: E402

NOTES = ["On day 1, Ann Lee repaired the blue map at Stone Mill.",
         "Day 2: at Reed Harbour, Bob Ray sold the old clock."]
QUESTIONS = ["Who repaired the blue map at Stone Mill?",
             "On which day did Bob Ray sell the old clock at Reed Harbour?",
             "What did Ann Lee sell at Reed Harbour?"]


def main(slug: str, out_path: str) -> int:
    out = {"model": slug, "status": "ERROR", "answers": []}
    t0 = time.perf_counter()
    try:
        from episodic_lab.models import PinnedModel
        model = PinnedModel(slug, "config/model_pins.json")
        out["load_s"] = round(time.perf_counter() - t0, 1)
        out["revision"] = model.revision
        t1 = time.perf_counter()
        digest = model.weights_digest(recompute=True)
        out["weights_hash_s"] = round(time.perf_counter() - t1, 2)
        out["weights_digest_stable"] = digest == model.weights_digest()
        for notes in ([], NOTES):
            for q in QUESTIONS:
                t1 = time.perf_counter()
                answer = model.generate(build_messages(q, notes))
                out["answers"].append({"notes": len(notes), "question": q, "answer": answer,
                                       "seconds": round(time.perf_counter() - t1, 2)})
        out["stats"] = model.stats
        out["status"] = "OK"
    except Exception:
        out["traceback"] = traceback.format_exc()[-4000:]
    out["total_s"] = round(time.perf_counter() - t0, 1)
    Path(out_path).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0 if out["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
