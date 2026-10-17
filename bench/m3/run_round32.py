"""Round 3.2 cell job: one world (both overlap conditions), every comparison cell.

Cells (docs/ROUND_3_2.md): A0, A1 (pilot baselines, v1 instruction), lex+reader,
struct+reader, lex+ops, struct+ops (regex encoder), struct+ops with the LM encoder,
random+ops; plus the misbound-store control, encoder slot accuracy, retrieval recall per
retrieving cell, and the restart test (fresh isolated process reading only the store).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from episodic_lab.arms import AllInPrompt, NoMemory  # noqa: E402
from episodic_lab.cells import (LexOps, LexReader, LMEncoder, RandomOps, StructOps,  # noqa: E402
                                StructReader, slot_accuracy)
from episodic_lab.memory import EpisodeStore, answer_query, parse_question, regex_encode  # noqa: E402
from episodic_lab.questions import make_world  # noqa: E402
from episodic_lab.runner import retention, run_world  # noqa: E402
from episodic_lab.score import score_world, summarise  # noqa: E402

SCHEMA = "episodic_lab.round32_cell.v1"
RESTART = ("import json, sys\nsys.path.insert(0, sys.argv[1])\n"
           "from episodic_lab.memory import EpisodeStore, answer_query, parse_question\n"
           "store = EpisodeStore(sys.argv[2])\nqs = json.loads(open(sys.argv[3]).read())\n"
           "print(json.dumps({q['qid']: answer_query(store.records, *parse_question(q['text'])).answer()"
           " for q in qs}))\n")
SLIM = ("qid", "criterion", "qtype", "phase", "raw", "category", "correct", "false_recall")


def slim(rows):
    return [{k: r[k] for k in SLIM + ("pair",) if k in r} for r in rows]


def answers_from(records, questions, phase="final"):
    return {q["qid"]: answer_query(records, *parse_question(q["text"])).answer()
            for q in questions["public"][phase]}


def scored(questions, answers, phase="final"):
    rows = score_world(questions["gold"], questions["candidates"], answers, phase)
    return {"summary": summarise(rows), "rows": slim(rows)}


def recall(cell, world, questions) -> dict:
    """Share of final positive items whose target episodes are all in the cell's retrieval."""
    texts = {e["episode_id"]: e["text"] for e in world["episodes"]}
    records = cell.store._records
    hit = {}
    for q in questions["public"]["final"]:
        g = questions["gold"][q["qid"]]
        if not g["targets"]:
            continue
        qtype, query = parse_question(q["text"])
        got = {r["text"] for r in cell.retrieve(q["text"], qtype, query, records)}
        hit.setdefault(g["criterion"], []).append(all(texts[t] in got for t in g["targets"]))
    return {c: sum(v) / len(v) for c, v in sorted(hit.items())}


def misbound(records, seed: str):
    rng = random.Random(seed)
    places, objects = [r["place"] for r in records], [r["object"] for r in records]
    rng.shuffle(places)
    rng.shuffle(objects)
    return [dict(r, place=p, object=o) for r, p, o in zip(records, places, objects)]


def restart_test(world, questions) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        store = EpisodeStore(tmp / "store.jsonl")
        for e in world["episodes"]:
            store.append(e["text"], regex_encode(e["text"]))
        (tmp / "q.json").write_text(json.dumps(questions["public"]["final"]))
        (tmp / "restart.py").write_text(RESTART)

        def fresh(path):
            out = subprocess.run([sys.executable, "-I", str(tmp / "restart.py"), str(ROOT), str(path),
                                  str(tmp / "q.json")], capture_output=True, text=True, check=True)
            return json.loads(out.stdout)
        after = fresh(tmp / "store.jsonl")
        empty = fresh(tmp / "missing.jsonl")
        lines = (tmp / "store.jsonl").read_text().splitlines()
        lines[0] = lines[0].replace(store.records[0]["place"], store.records[1]["place"] + "x", 1)
        (tmp / "tampered.jsonl").write_text("\n".join(lines) + "\n")
        refused = subprocess.run([sys.executable, "-I", str(tmp / "restart.py"), str(ROOT),
                                  str(tmp / "tampered.jsonl"), str(tmp / "q.json")],
                                 capture_output=True, text=True).returncode != 0
    before = answers_from(store.records, questions)
    gold = questions["gold"]
    positives = [q for q in after if gold[q]["gold"] != ["none"]]
    return {"same_as_in_process": after == before,
            "accuracy_after_restart": sum(after[q] in gold[q]["gold"] for q in after) / len(after),
            "empty_store_positive_accuracy": sum(empty[q] in gold[q]["gold"] for q in positives) / len(positives),
            "tampered_store_refused": refused}


def run_condition(model, world, questions, out: dict) -> None:
    cells = {"A0": NoMemory(model, "v1"), "A1": AllInPrompt(model, "v1"),
             "lex+reader": LexReader(model), "struct+reader": StructReader(model),
             "lex+ops": LexOps(), "struct+ops": StructOps(), "random+ops": RandomOps(),
             "struct+ops/lm-encoder": StructOps(encoder=LMEncoder(model), encoder_name="lm:" + model.slug)}
    for name, cell in cells.items():
        t0, calls = time.perf_counter(), model.stats["calls"]
        result = run_world(cell, world, questions)
        entry = {"phase1": result["phase1"], "final": result["final"], "retention": retention(result),
                 "rows": slim(result["rows"]), "seconds": round(time.perf_counter() - t0, 1),
                 "lm_calls": model.stats["calls"] - calls}
        if hasattr(cell, "retrieve") and name != "struct+ops/lm-encoder":
            entry["retrieval_recall"] = recall(cell, world, questions)
        out["cells"][name] = entry
    lm_cell = cells["struct+ops/lm-encoder"]
    pairs = [({k: r[k] for k in ("actor", "partner", "action", "object", "place", "event_day")},
              regex_encode(r["text"])) for r in lm_cell.store._records]
    out["encoder"] = {"slot_accuracy": slot_accuracy(pairs),
                      "errors": [{"text": r["text"], "lm": a, "truth": t, "raw": raw}
                                 for r, (a, t), raw in zip(lm_cell.store._records, pairs, lm_cell.encoder.raw)
                                 if a != t][:20]}
    regex_records = cells["struct+ops"].store._records
    out["misbound"] = scored(questions, answers_from(misbound(regex_records, world["seed"]), questions))
    out["restart"] = restart_test(world, questions)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--series", required=True)
    ap.add_argument("--index", type=int, required=True)
    ap.add_argument("--pins", default="config/model_pins.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = {"schema": SCHEMA, "model": args.model, "series": args.series, "index": args.index,
           "status": "ERROR", "code_commit": os.environ.get("GITHUB_SHA", "local"), "conditions": {}}
    t0 = time.perf_counter()
    try:
        from episodic_lab.models import PinnedModel
        model = PinnedModel(args.model, args.pins)
        start = model.weights_digest()
        out.update({"revision": model.revision, "weights_digest": start})
        attempt, pair = make_world(args.series, args.index, order_both=True)
        out["attempt"] = attempt
        for overlap, (world, questions) in pair.items():
            cond = out["conditions"][overlap] = {"seed": world["seed"], "cells": {}}
            run_condition(model, world, questions, cond)
        if model.weights_digest(recompute=True) != start:
            raise RuntimeError("weights changed")
        out["status"] = "OK"
    except Exception:
        out["traceback"] = traceback.format_exc()[-4000:]
    out["seconds"] = round(time.perf_counter() - t0, 1)
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0 if out["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
