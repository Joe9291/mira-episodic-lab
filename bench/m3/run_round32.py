"""Round 3.2 cell job: one world (both overlap conditions), every comparison cell.

Cells (docs/ROUND_3_2.md): A0, A1 (pilot baselines, v1 instruction); lex3+reader and
lex3+ops (same BM25 selection); struct3+reader and struct3+ops (same index selection);
full+ops (reference, regex encoder, store on disk with a seal); random3+ops (control);
full+ops/lm-encoder (the LM slot-filling encoder). Plus the misbound-store control, the
encoder record by record, and the restart test on exactly the store file of full+ops.

Per answer row: the selected record ids, the scope flag, the operator status and trace
(replayed deterministically after the run from the record set of that test point, never
while answering) and, as evaluator-only information, whether all gold target episodes
were selected. A failing cell is recorded with its traceback; the other cells still run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from episodic_lab.arms import AllInPrompt, NoMemory  # noqa: E402
from episodic_lab.cells import (FullOps, Lex3Ops, Lex3Reader, LMEncoder, Random3Ops,  # noqa: E402
                                Struct3Ops, Struct3Reader)
from episodic_lab.memory import (EpisodeStore, answer_query, misbind, parse_question,  # noqa: E402
                                 regex_encode)
from episodic_lab.questions import make_world  # noqa: E402
from episodic_lab.runner import retention, run_world  # noqa: E402
from episodic_lab.score import score_world, summarise  # noqa: E402

SCHEMA = "episodic_lab.round32_cell.v2"
CONTENT = ("actor", "partner", "action", "object", "place", "event_day")
RESTART = ("import json, sys\nsys.path.insert(0, sys.argv[1])\n"
           "from episodic_lab.memory import EpisodeStore, answer_query, parse_question\n"
           "store = EpisodeStore(sys.argv[2], expect=json.loads(open(sys.argv[3]).read()))\n"
           "qs = json.loads(open(sys.argv[4]).read())\n"
           "print(json.dumps({q['qid']: answer_query(store.records, *parse_question(q['text'])).answer()"
           " for q in qs}))\n")
SLIM = ("qid", "criterion", "qtype", "phase", "raw", "category", "correct", "false_recall")


def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def slim(rows):
    return [{k: r[k] for k in SLIM + ("pair",) if k in r} for r in rows]


def phase_records(records, world, phase):
    n_early = sum(e["block"] == "early" for e in world["episodes"])
    return records if phase == "final" else [r for r in records if r["seq"] < n_early]


def add_diagnostics(cell, rows, world, questions):
    texts = {e["episode_id"]: e["text"] for e in world["episodes"]}
    by_qid = {q["qid"]: q["text"] for q in questions["public"]["final"]}
    for row in rows:
        recs = phase_records(cell.store._records, world, row["phase"])
        diag = cell.explain(by_qid[row["qid"]], recs)
        chosen = {r["text"] for r in recs if r["id"] in set(diag["selected"])}
        targets = questions["gold"][row["qid"]]["targets"]
        diag["gold_support_selected"] = all(texts[t] in chosen for t in targets) if targets else None
        row["diag"] = diag


def restart_test(store_path: Path, seal: dict, questions, in_process: dict) -> dict:
    tmp = store_path.parent
    (tmp / "seal.json").write_text(json.dumps(seal))
    (tmp / "q.json").write_text(json.dumps(questions["public"]["final"]))
    (tmp / "restart.py").write_text(RESTART)

    def fresh(path, seal_path):
        out = subprocess.run([sys.executable, "-I", str(tmp / "restart.py"), str(ROOT), str(path),
                              str(seal_path), str(tmp / "q.json")], capture_output=True, text=True)
        return json.loads(out.stdout) if out.returncode == 0 else None
    after = fresh(store_path, tmp / "seal.json")
    (tmp / "empty_seal.json").write_text(json.dumps({"count": 0, "head": "0" * 64}))
    empty = fresh(tmp / "missing.jsonl", tmp / "empty_seal.json")
    lines = store_path.read_text().splitlines()
    (tmp / "truncated.jsonl").write_text("\n".join(lines[:-1]) + "\n")
    rec = json.loads(lines[0])
    rec["place"] = rec["place"] + "x"
    (tmp / "changed.jsonl").write_text("\n".join([json.dumps(rec, sort_keys=True)] + lines[1:]) + "\n")
    gold = questions["gold"]
    positives = [q for q in gold if gold[q]["gold"] != ["none"]]
    return {"same_as_in_process": after == in_process,
            "accuracy_after_restart": (sum(after[q] in gold[q]["gold"] for q in after) / len(after)) if after else None,
            "empty_store_positive_accuracy": sum(empty[q] in gold[q]["gold"] for q in positives) / len(positives),
            "truncated_store_refused": fresh(tmp / "truncated.jsonl", tmp / "seal.json") is None,
            "changed_store_refused": fresh(tmp / "changed.jsonl", tmp / "seal.json") is None}


def run_cell(name, cell, model, world, questions):
    t0 = time.perf_counter()
    before = dict(model.stats) if model is not None else {}
    try:
        result = run_world(cell, world, questions)
        rows = slim(result["rows"])
        if hasattr(cell, "explain"):
            add_diagnostics(cell, rows, world, questions)
        entry = {"status": "OK", "phase1": result["phase1"], "final": result["final"],
                 "retention": retention(result), "rows": rows}
    except Exception:
        entry = {"status": "ERROR", "traceback": traceback.format_exc()[-3000:]}
    entry["seconds"] = round(time.perf_counter() - t0, 1)
    entry["cost"] = ({k: model.stats[k] - before.get(k, 0) for k in ("calls", "prompt_tokens", "new_tokens")}
                     if model is not None else {"calls": 0, "prompt_tokens": 0, "new_tokens": 0})
    return entry


def run_condition(model, world, questions, out: dict, workdir: Path) -> None:
    store_path = workdir / f"{world['overlap']}_full.jsonl"
    full = FullOps(store=EpisodeStore(store_path))
    lm_encoder = LMEncoder(model)
    cells = {"A0": NoMemory(model, "v1"), "A1": AllInPrompt(model, "v1"),
             "lex3+reader": Lex3Reader(model), "lex3+ops": Lex3Ops(),
             "struct3+reader": Struct3Reader(model), "struct3+ops": Struct3Ops(),
             "full+ops": full, "random3+ops": Random3Ops(),
             "full+ops/lm-encoder": FullOps(encoder=lm_encoder, encoder_name="lm:" + model.slug)}
    for name, cell in cells.items():
        uses_model = name in ("A0", "A1", "lex3+reader", "struct3+reader", "full+ops/lm-encoder")
        out["cells"][name] = run_cell(name, cell, model if uses_model else None, world, questions)
    lm_cell = cells["full+ops/lm-encoder"]
    out["encoder"] = {"records": [
        {"text": r["text"], "lm": {k: r[k] for k in CONTENT}, "truth": regex_encode(r["text"]),
         "invalid": bad, "raw": raw}
        for r, bad, raw in zip(lm_cell.store._records, lm_encoder.invalid, lm_encoder.raw)]}
    records = full.store.records
    mis = score_world(questions["gold"], questions["candidates"],
                      {q["qid"]: answer_query(misbind(records, world["seed"]), *parse_question(q["text"])).answer()
                       for q in questions["public"]["final"]}, "final")
    out["misbound"] = {"summary": summarise(mis), "rows": slim(mis)}
    in_process = {q["qid"]: answer_query(records, *parse_question(q["text"])).answer()
                  for q in questions["public"]["final"]}
    out["restart"] = restart_test(store_path, full.store.seal(), questions, in_process)
    out["store_seal"] = full.store.seal()


def check_weights(model, start: str) -> None:
    """The reader's weights must be unchanged after the whole job (recomputed from tensors)."""
    if model.weights_digest(recompute=True) != start:
        raise RuntimeError("weights changed")


def file_sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--series", required=True)
    ap.add_argument("--index", type=int, required=True)
    ap.add_argument("--pins", default="config/model_pins.json")
    ap.add_argument("--request", default="config/round32.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = {"schema": SCHEMA, "model": args.model, "series": args.series, "index": args.index,
           "status": "ERROR", "conditions": {},
           "provenance": {"code_commit": os.environ.get("GITHUB_SHA", "local"),
                          "request_sha256": file_sha256(args.request),
                          "pins_sha256": file_sha256(args.pins)}}
    t0 = time.perf_counter()
    try:
        from episodic_lab.models import PinnedModel
        model = PinnedModel(args.model, args.pins)
        start = model.weights_digest()
        out.update({"revision": model.revision, "weights_digest": start})
        attempt, pair = make_world(args.series, args.index, order_both=True)
        out["attempt"] = attempt
        with tempfile.TemporaryDirectory() as tmp:
            for overlap, (world, questions) in pair.items():
                cond = out["conditions"][overlap] = {
                    "seed": world["seed"], "world_sha256": canonical_sha256(world),
                    "questions_sha256": canonical_sha256(questions), "cells": {}}
                run_condition(model, world, questions, cond, Path(tmp))
        check_weights(model, start)
        out["status"] = "OK"
    except Exception:
        out["traceback"] = traceback.format_exc()[-4000:]
    out["seconds"] = round(time.perf_counter() - t0, 1)
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0 if out["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
