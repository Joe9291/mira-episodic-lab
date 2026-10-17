"""Round 3.2 job logic with a fake model (no PyTorch): every cell runs, recall, encoder
accuracy, misbound control and restart test behave as designed."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench" / "m3"))
sys.path.insert(0, str(ROOT / "tests"))

import run_round32  # noqa: E402
from episodic_lab.cells import LMEncoder, bm25_top, struct_top  # noqa: E402
from episodic_lab.memory import EpisodeStore, parse_question, regex_encode  # noqa: E402
from episodic_lab.questions import make_world  # noqa: E402
from test_arms import FakeModel  # noqa: E402

PAIR = make_world("round32-test", 0, order_both=True)[1]


class SlotModel(FakeModel):
    """Reads story notes like FakeModel; answers encoder slot questions from the note."""
    slug = "fake"

    def generate(self, messages):
        user = messages[1]["content"]
        if not user.startswith("Note:\n"):
            return super().generate(messages)
        self.stats["calls"] += 1
        note, question = user[len("Note:\n"):].split("\n\nQuestion: ")
        f = regex_encode(note)
        for key, slot in (("day", "event_day"), ("do?", "action"), ("second person", "partner"),
                          ("first person", "actor"), ("object", "object"), ("place", "place")):
            if key in question:
                v = f[slot]
                return "none" if v is None else (f"Day {v}" if slot == "event_day" else str(v))
        return "unknown"


class Round32Tests(unittest.TestCase):
    def test_condition_job(self):
        world, questions = PAIR["high"]
        out = {"cells": {}}
        run_round32.run_condition(SlotModel(), world, questions, out)
        cells = out["cells"]
        self.assertEqual(set(cells), {"A0", "A1", "lex+reader", "struct+reader", "lex+ops",
                                      "struct+ops", "random+ops", "struct+ops/lm-encoder"})
        for name in ("struct+ops", "struct+ops/lm-encoder"):
            self.assertTrue(all(r["correct"] for r in cells[name]["rows"]), name)
        self.assertEqual(out["encoder"]["slot_accuracy"]["all_slots"], 1.0)
        self.assertEqual(set(cells["struct+ops"]["retrieval_recall"].values()), {1.0})
        self.assertLess(cells["random+ops"]["final"]["E2"]["accuracy"], 0.5)
        self.assertLess(out["misbound"]["summary"]["E2"]["accuracy"], 0.5)
        r = out["restart"]
        self.assertEqual((r["same_as_in_process"], r["accuracy_after_restart"], r["tampered_store_refused"]),
                         (True, 1.0, True))
        self.assertEqual(r["empty_store_positive_accuracy"], 0.0)
        self.assertEqual(cells["A0"]["final"]["E2"]["accuracy"], 0.0)

    def test_encoder_cleaning(self):
        class Raw(SlotModel):
            def generate(self, messages):
                reply = super().generate(messages)
                return {"none": "None.", }.get(reply, f"The {reply}." if " " in reply and reply[0].islower()
                                               else reply)
        enc = LMEncoder(Raw())
        world, _ = PAIR["low"]
        for e in world["episodes"][:10]:
            self.assertEqual(enc(e["text"]), regex_encode(e["text"]))

    def test_retrievers_return_presentation_order_and_at_most_k(self):
        world, questions = PAIR["low"]
        store = EpisodeStore()
        for e in world["episodes"]:
            store.append(e["text"], regex_encode(e["text"]))
        recs = store.records
        for q in questions["public"]["final"]:
            qtype, query = parse_question(q["text"])
            for got in (bm25_top(recs, q["text"]), struct_top(recs, qtype, query)):
                self.assertLessEqual(len(got), 3)
            got = struct_top(recs, qtype, query)
            self.assertEqual([r["seq"] for r in got], sorted(r["seq"] for r in got))


class CollectorTests(unittest.TestCase):
    def test_complete_and_damaged(self):
        import json
        import tempfile
        import collect_round32
        data = {"schema": run_round32.SCHEMA, "model": "m", "series": "round32-test", "index": 0,
                "status": "OK", "conditions": {}}
        for overlap, (world, questions) in PAIR.items():
            cond = data["conditions"][overlap] = {"seed": world["seed"], "cells": {}}
            run_round32.run_condition(SlotModel(), world, questions, cond)
        data = json.loads(json.dumps(data))
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            req = dest / "req.json"
            req.write_text(json.dumps({"model": "m", "worlds": {"round32-test": [0]}}))
            (dest / "r32_round32-test_0.json").write_text(json.dumps(data))
            collect_round32.main(str(req), str(dest))
            self.assertEqual((dest / "VERDICT").read_text().strip(), "COMPLETE", (dest / "CHECK.txt").read_text())
            summary = (dest / "SUMMARY.md").read_text()
            self.assertIn("| struct+ops | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |", summary)
            self.assertIn("tampered store refused 2/2", summary)
            data["conditions"]["low"]["cells"]["lex+ops"]["final"]["E2"]["accuracy"] = 1.0
            (dest / "r32_round32-test_0.json").write_text(json.dumps(data))
            collect_round32.main(str(req), str(dest))
            self.assertIn("summary:low:lex+ops:final", (dest / "CHECK.txt").read_text())
            del data["conditions"]["low"]["cells"]["A1"]
            (dest / "r32_round32-test_0.json").write_text(json.dumps(data))
            collect_round32.main(str(req), str(dest))
            self.assertIn("cells:low", (dest / "CHECK.txt").read_text())
            self.assertEqual((dest / "VERDICT").read_text().strip(), "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
