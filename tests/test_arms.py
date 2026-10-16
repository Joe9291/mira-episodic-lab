"""Milestone 2 tests without PyTorch: prompts, arms, oracle evidence, pin check, pilot collector."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench" / "pilot"))

from episodic_lab.arms import ARMS, FORMAT, NO_NOTES, build_messages, instruction  # noqa: E402
from episodic_lab.models import PinError, verify_snapshot  # noqa: E402
from episodic_lab.questions import make_world  # noqa: E402
from episodic_lab.runner import StateChangedWhileAnswering, run_world  # noqa: E402
from episodic_lab.symbolic import SymbolicMemory  # noqa: E402
import collect  # noqa: E402

PAIRS = [make_world("arms-test", i)[1] for i in range(4)]


class FakeModel:
    """Answers each chat by reading ONLY the prompt: rule-based memory of the notes in it."""

    def __init__(self):
        self.seen = []
        self.stats = {"calls": 0}

    def weights_digest(self, recompute=False):
        return "fake-weights"

    def generate(self, messages):
        self.seen.append(messages)
        user = messages[1]["content"]
        notes, question = user[len("Story notes:\n"):].split("\n\nQuestion: ")
        memory = SymbolicMemory()
        if notes != NO_NOTES:
            for line in notes.split("\n"):
                memory.encode(line)
        return memory.answer(question, None)


class ArmTests(unittest.TestCase):
    def test_instruction_names_only_the_asked_answer_type(self):
        for answer_type, (form, example) in FORMAT.items():
            text = instruction(answer_type)
            self.assertIn(form, text)
            self.assertIn(example, text)
            for other, (other_form, _) in FORMAT.items():
                if other != answer_type:
                    self.assertNotIn(other_form, text)
            self.assertEqual("none" in text, answer_type != "choice")

    def test_examples_never_name_world_vocabulary(self):
        from episodic_lab.world import FIRST, LAST, OBJ_ADJ, OBJ_NOUN, PLACE_KIND, PLACE_STEM
        words = set(FIRST + LAST + OBJ_ADJ + OBJ_NOUN + PLACE_KIND + PLACE_STEM)
        for _, example in FORMAT.values():
            self.assertFalse(set(example.split()) & words, example)

    def test_prompts_differ_only_in_notes(self):
        a = build_messages("Who?", [], "person")
        b = build_messages("Who?", ["Day 1: x."], "person")
        self.assertEqual(a[0], {"role": "system", "content": instruction("person")})
        self.assertEqual(a[0], b[0])
        self.assertEqual(a[1]["content"], f"Story notes:\n{NO_NOTES}\n\nQuestion: Who?")
        self.assertEqual(b[1]["content"], "Story notes:\nDay 1: x.\n\nQuestion: Who?")

    def test_all_in_prompt_and_oracle_carry_enough_information(self):
        for pair in PAIRS:
            for world, q in pair.values():
                for arm in ("A1", "O1"):
                    result = run_world(ARMS[arm](FakeModel()), world, q)
                    wrong = [r for r in result["rows"] if not r["correct"]]
                    self.assertEqual(wrong, [], (arm, world["overlap"], wrong[:1]))

    def test_no_memory_sees_no_story(self):
        world, q = PAIRS[0]["high"]
        model = FakeModel()
        result = run_world(ARMS["A0"](model), world, q)
        self.assertTrue(all(m[1]["content"].startswith(f"Story notes:\n{NO_NOTES}") for m in model.seen))
        self.assertEqual(result["final"]["E5"]["accuracy"], 1.0)
        self.assertEqual(result["final"]["E2"]["accuracy"], 0.0)

    def test_every_answer_is_a_fresh_two_message_chat(self):
        world, q = PAIRS[1]["low"]
        model = FakeModel()
        run_world(ARMS["A1"](model), world, q)
        self.assertEqual(len(model.seen), len(q["public"]["phase1"]) + len(q["public"]["final"]))
        self.assertTrue(all(len(m) == 2 for m in model.seen))

    def test_oracle_gets_target_episodes_only_and_nothing_for_lures(self):
        world, q = PAIRS[2]["high"]
        model = FakeModel()
        run_world(ARMS["O1"](model), world, q)
        texts = {r["text"]: r["qid"] for r in q["public"]["final"]}
        for messages in model.seen:
            user = messages[1]["content"]
            notes, question = user[len("Story notes:\n"):].split("\n\nQuestion: ")
            gold = q["gold"][texts[question]]
            expected = len(gold["targets"])
            self.assertEqual(0 if notes == NO_NOTES else len(notes.split("\n")), expected)

    def test_changed_weights_are_detected(self):
        class Drifting(FakeModel):
            def __init__(self):
                super().__init__()
                self.n = 0

            def weights_digest(self, recompute=False):
                if recompute:
                    self.n += 1
                    return f"w{self.n}"
                return "w"
        world, q = PAIRS[0]["high"]
        with self.assertRaises(StateChangedWhileAnswering):
            run_world(ARMS["A1"](Drifting()), world, q)


class PinTests(unittest.TestCase):
    def test_snapshot_must_match_pins_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.safetensors").write_bytes(b"weights")
            (root / "config.json").write_text("{}")
            spec = {"files": {name: {"size": (root / name).stat().st_size,
                                     "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()}
                              for name in ("model.safetensors", "config.json")}}
            verify_snapshot(root, spec)
            (root / "model.safetensors").write_bytes(b"weightz")
            with self.assertRaises(PinError):
                verify_snapshot(root, spec)
            (root / "model.safetensors").write_bytes(b"weights")
            (root / "extra.json").write_text("{}")
            with self.assertRaises(PinError):
                verify_snapshot(root, spec)

    def test_pin_file_is_complete(self):
        pins = json.loads((ROOT / "config" / "model_pins.json").read_text())
        request = json.loads((ROOT / "config" / "pin_request.json").read_text())
        self.assertEqual(pins["errors"], {})
        for slug, spec in request["models"].items():
            self.assertEqual(pins["models"][slug]["revision"], spec["revision"])
            self.assertEqual(pins["models"][slug]["license"], "apache-2.0")
            self.assertTrue(any(f.endswith(".safetensors") for f in pins["models"][slug]["files"]))


class CollectorTests(unittest.TestCase):
    def test_incomplete_cells_are_registered(self):
        request = {"models": ["m"], "arms": ["A0", "A1"], "indices": [0]}
        world, q = PAIRS[0]["high"]
        good = run_world(ARMS["A1"](FakeModel()), world, q)
        cond = {"rows": good["rows"], "final": good["final"], "phase1": good["phase1"],
                "retention": {"phase1": 1.0, "final": 1.0}, "symbolic_all_correct": True}
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "req.json").write_text(json.dumps(request))
            (dest / "pilot_m_A1_0.json").write_text(json.dumps(
                {"status": "OK", "conditions": {"high": cond, "low": cond}}))
            (dest / "pilot_m_A0_0.json").write_text("null")
            collect.main(str(dest / "req.json"), str(dest))
            self.assertEqual((dest / "VERDICT").read_text().strip(), "INCOMPLETE")
            check = (dest / "CHECK.txt").read_text()
            self.assertIn("FAILED pilot_m_A0_0.json not_an_object", check)
            self.assertIn("OK pilot_m_A1_0.json", check)
            self.assertIn("| m | A1 | 1 |", (dest / "SUMMARY.md").read_text())
            (dest / "pilot_m_A0_0.json").write_text(json.dumps(
                {"status": "OK", "conditions": {"high": cond, "low": cond}}))
            collect.main(str(dest / "req.json"), str(dest))
            self.assertEqual((dest / "VERDICT").read_text().strip(), "COMPLETE")
            for bad, reason in (({"status": "ERROR", "conditions": {"high": cond, "low": cond}}, "status"),
                                ({"status": "OK", "conditions": {"high": cond, "low": dict(cond, symbolic_all_correct=False)}}, "reference:low")):
                (dest / "pilot_m_A0_0.json").write_text(json.dumps(bad))
                collect.main(str(dest / "req.json"), str(dest))
                self.assertEqual((dest / "VERDICT").read_text().strip(), "INCOMPLETE")
                self.assertIn(reason, (dest / "CHECK.txt").read_text())


if __name__ == "__main__":
    unittest.main()
