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

    max_new_tokens = 16

    def __init__(self):
        self.seen = []
        self.stats = {"calls": 0, "prompt_tokens": 0, "new_tokens": 0, "truncated": 0}
        self.call_log = []

    def count_tokens(self, text):
        return len(text.split())

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
        reply = memory.answer(question, None)
        cut = self.cut_off(question)
        self.stats["calls"] += 1
        self.stats["prompt_tokens"] += len(user.split())
        self.stats["new_tokens"] += 16 if cut else 1
        self.stats["truncated"] += int(cut)
        self.call_log.append({"prompt_tokens": len(user.split()), "new_tokens": 16 if cut else 1,
                              "truncated": cut})
        return reply

    def cut_off(self, question):
        return False


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

    def test_oracle_gets_targets_and_confusable_notes_for_lures(self):
        from episodic_lab.questions import matching
        from episodic_lab.world import episodes_of
        for pair in PAIRS:
            world, q = pair["high"]
            episodes = episodes_of(world)
            by_text = {e.text: e for e in episodes}
            model = FakeModel()
            run_world(ARMS["O1"](model), world, q)
            texts = {r["text"]: r["qid"] for r in q["public"]["final"]}
            lures = 0
            for messages in model.seen:
                user = messages[1]["content"]
                notes, question = user[len("Story notes:\n"):].split("\n\nQuestion: ")
                self.assertNotEqual(notes, NO_NOTES)  # never an empty context
                shown = [by_text[line] for line in notes.split("\n")]
                self.assertEqual([e.position for e in shown], sorted(e.position for e in shown))
                gold = q["gold"][texts.get(question) or next(
                    r["qid"] for r in q["public"]["phase1"] if r["text"] == question)]
                if gold["criterion"] != "E5":
                    self.assertEqual({e.episode_id for e in shown}, set(gold["targets"]))
                    continue
                lures += 1
                cue = gold["cue"]
                self.assertTrue(all(e.block == "early" for e in shown))
                self.assertEqual(matching(shown, **cue), [])  # no note answers the lure
                keys = sorted(cue)
                for i, a in enumerate(keys):  # every pair of details is shown
                    for b in keys[i + 1:]:
                        self.assertTrue(matching(shown, **{a: cue[a], b: cue[b]}), (a, b))
                self.assertLessEqual(len(shown), 3)
            self.assertGreater(lures, 0)

    def test_processing_counts_follow_the_declared_exposure(self):
        world, q = PAIRS[1]["high"]
        n1, nf = len(q["public"]["phase1"]), len(q["public"]["final"])
        counts = {arm: run_world(ARMS[arm](FakeModel()), world, q)["processing"] for arm in ARMS}
        self.assertEqual(set(counts["A0"]["prompt_inclusions"].values()), {0})
        for e in world["episodes"]:
            self.assertEqual(counts["A1"]["prompt_inclusions"][e["episode_id"]],
                             n1 + nf if e["block"] == "early" else nf)
            for arm in ARMS:
                self.assertEqual(counts[arm]["encode_reads"][e["episode_id"]], 1)
        model = FakeModel()
        result = run_world(ARMS["O1"](model), world, q)
        shown = sum(len(m[1]["content"].split("\n\nQuestion: ")[0].split("\n")) - 1 for m in model.seen)
        self.assertEqual(sum(result["processing"]["prompt_inclusions"].values()), shown)
        self.assertEqual(counts["A1"]["declared_per_episode"]["store_writes"], 1)
        self.assertEqual(counts["A0"]["declared_per_episode"]["store_writes"], 0)

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


import run_pilot  # noqa: E402

REQUEST = {"schema": "episodic_lab.pilot_request.v1", "enabled": True, "series": "arms-test",
           "models": ["m"], "arms": ["A0", "A1", "O1"], "indices": [0]}
PINS = {"models": {"m": {"repo": "org/m", "revision": "a" * 40}}}


def realistic_cell(arm, model=None, index=0, request_sha="", pins_sha=""):
    """A full cell as run_pilot writes it, produced by run_cell with the fake model."""
    out = {"schema": run_pilot.SCHEMA, "model": "m", "arm": arm, "series": REQUEST["series"],
           "index": index, "status": "ERROR",
           "provenance": {"code_commit": "c" * 40, "request_sha256": request_sha,
                          "pins_sha256": pins_sha},
           "repo": "org/m", "revision": "a" * 40, "max_new_tokens": 16,
           "weights_digest": "b" * 64}
    run_pilot.run_cell(model or FakeModel(), arm, REQUEST["series"], index, out)
    out["status"] = "OK"
    return json.loads(json.dumps(out))


class CollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.req, cls.pins = root / "pilot.json", root / "pins.json"
        cls.req.write_text(json.dumps(REQUEST))
        cls.pins.write_text(json.dumps(PINS))
        shas = dict(request_sha=collect.sha256_file(cls.req), pins_sha=collect.sha256_file(cls.pins))
        cls.cells = {arm: realistic_cell(arm, **shas) for arm in REQUEST["arms"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_collect(self, cells):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            for arm, data in cells.items():
                text = data if isinstance(data, str) else json.dumps(data)
                (dest / f"pilot_m_{arm}_0.json").write_text(text)
            collect.main(str(self.req), str(dest), str(self.pins))
            return ((dest / "VERDICT").read_text().strip(), (dest / "CHECK.txt").read_text(),
                    (dest / "SUMMARY.md").read_text())

    def test_realistic_cells_are_complete_and_summarised(self):
        verdict, check, summary = self.run_collect(self.cells)
        self.assertEqual(verdict, "COMPLETE", check)
        self.assertIn("| m | A1 | 1 | 1.00 |", summary)
        self.assertIn("| m | O1 (diagnostic) | 1 |", summary)
        self.assertIn("E3b at_day | E3b latest", summary)
        self.assertIn("E5 uncertain", summary)
        self.assertIn("| m | 1 | 1.000 | 1.000 | yes |", summary)  # O1 selection, positives only
        for arm in ("A0", "A1", "O1"):
            self.assertIn(f"OK pilot_m_{arm}_0.json", check)

    def mutate(self, arm, change):
        cells = json.loads(json.dumps(self.cells))
        change(cells[arm])
        return self.run_collect(cells)

    def test_every_damage_is_detected(self):
        def drop(path):
            def f(cell):
                node = cell
                for key in path[:-1]:
                    node = node[key]
                del node[path[-1]]
            return f

        def put(path, value):
            def f(cell):
                node = cell
                for key in path[:-1]:
                    node = node[key]
                node[path[-1]] = value
            return f
        def row(cond, **match):
            def pick(cell):
                return next(r for r in cell["conditions"][cond]["rows"]
                            if all(r[k] == v for k, v in match.items()))
            return pick

        def edit_row(cond, changes, **match):
            return lambda c: row(cond, **match)(c).update(changes)

        def proc(cond, key):
            return lambda c: c["conditions"][cond]["processing"][key]

        def first_id(c, cond="low"):
            return next(iter(c["conditions"][cond]["processing"]["encode_reads"]))

        def restate(c, cond):  # make the stored summaries consistent with edited rows
            rows = c["conditions"][cond]["rows"]
            for phase in ("phase1", "final"):
                c["conditions"][cond][phase] = collect.recompute_summary(rows, phase)

        def all_latest_to_at_day(c):
            for r in c["conditions"]["low"]["rows"]:
                if r["qtype"] == "latest":
                    r["qtype"] = "at_day"
            restate(c, "low")

        def a1_inclusion_off_by_one(c):
            pr = c["conditions"]["low"]["processing"]
            k = first_id(c)
            pr["prompt_inclusions"][k] -= 1
            pr["prompt_token_equivalents"][k] = pr["prompt_inclusions"][k] * pr["episode_tokens"][k]
            pr["prompt_inclusion_summary"] = collect.inclusion_summary(pr["prompt_inclusions"])

        def o1_no_notes(c):
            pr = c["conditions"]["low"]["processing"]
            for k in pr["prompt_inclusions"]:
                pr["prompt_inclusions"][k] = pr["prompt_token_equivalents"][k] = 0
            pr["prompt_inclusion_summary"] = collect.inclusion_summary(pr["prompt_inclusions"])

        def rename_episode(c):  # consistent inside the cell, different from the other cells
            pr = c["conditions"]["low"]["processing"]
            k = first_id(c)
            for key in ("encode_reads", "prompt_inclusions", "episode_tokens", "prompt_token_equivalents"):
                pr[key]["ep-zzzzzz"] = pr[key].pop(k)

        def shift_categories(c):
            cats = c["conditions"]["high"]["final"]["E2"]["categories"]
            cats["correct"], cats["wrong_value"] = cats["correct"] - 0.25, cats["wrong_value"] + 0.25
        cases = [
            # identity, status, provenance
            ("A1", put(["arm"], "A0"), "identity:arm"),
            ("A1", put(["model"], "x"), "identity:model"),
            ("A1", put(["index"], 1), "identity:index"),
            ("A1", put(["series"], "other"), "identity:series"),
            ("A1", put(["status"], "ERROR"), "status"),
            ("A1", put(["schema"], "episodic_lab.pilot_cell.v1"), "schema"),
            ("A1", put(["revision"], "b" * 40), "revision:pin"),
            ("A1", put(["provenance", "request_sha256"], "0" * 64), "provenance:request"),
            ("A1", put(["provenance", "pins_sha256"], "0" * 64), "provenance:pins"),
            ("A1", put(["provenance", "code_commit"], "d" * 40), "provenance:mixed_commits"),
            ("A1", put(["partial"], {}), "partial_left"),
            ("A1", drop(["max_new_tokens"]), "max_new_tokens"),
            # structure
            ("A1", drop(["conditions", "low"]), "conditions"),
            ("A1", drop(["conditions", "high", "final"]), "criteria:high:final"),
            ("A1", drop(["conditions", "high", "phase1", "E5"]), "criteria:high:phase1"),
            ("A1", put(["conditions", "high", "seconds"], None), "seconds:high"),
            ("A1", put(["conditions", "high", "rows"], [{}]), "row_structure:high"),
            ("A1", edit_row("high", {"correct": 1}, criterion="E2"), "row_structure:high"),
            ("A1", lambda c: c["conditions"]["high"]["rows"][0].pop("truncated"), "row_structure:high"),
            ("A1", edit_row("high", {"qtype": "latest"}, phase="phase1", qtype="at_day"), "row_structure:high"),
            ("A1", edit_row("high", {"phase": "phase1"}, criterion="E7"), "row_structure:high"),
            ("A1", put(["conditions", "high", "world_sha256"], "x"), "world_sha256:high"),
            ("A1", put(["conditions", "high", "world_sha256"], "0" * 64), "world_differs:high"),
            ("A1", put(["conditions", "low", "symbolic_all_correct"], False), "reference:low"),
            ("A0", rename_episode, "world_differs:low"),
            # formally valid values that contradict the rows
            ("A1", put(["conditions", "low", "final", "E3b", "by_qtype", "latest", "accuracy"], 0.0),
             "summary_vs_rows:low:final"),
            ("A1", put(["conditions", "low", "final", "E3b", "by_qtype", "latest", "n"], 1),
             "summary_vs_rows:low:final"),
            ("A1", drop(["conditions", "low", "final", "E3b", "by_qtype"]), "summary_vs_rows:low:final"),
            ("A1", all_latest_to_at_day, "e3b_subtypes:low:final"),
            ("A1", put(["conditions", "low", "final", "E2", "accuracy"], 0.5), "summary_vs_rows:low:final"),
            ("A1", put(["conditions", "low", "final", "E2", "n"], 99), "summary_vs_rows:low:final"),
            ("A1", shift_categories, "summary_vs_rows:high:final"),
            ("A1", put(["conditions", "low", "final", "E5", "false_recall"], 0.5), "summary_vs_rows:low:final"),
            ("A1", put(["conditions", "high", "retention", "final"], 0.3), "retention_vs_rows:high"),
            ("A1", drop(["conditions", "high", "retention"]), "retention_vs_rows:high"),
            ("A1", edit_row("high", {"false_recall": True}, criterion="E5"), "row_inconsistent:high"),
            ("A1", edit_row("high", {"truncated": True}, criterion="E2"), "row_tokens:high"),
            ("A1", edit_row("high", {"new_tokens": 17}, criterion="E2"), "row_tokens:high"),
            ("A1", lambda c: c["conditions"]["high"]["telemetry"].update(calls=3), "telemetry_vs_rows:high"),
            ("A1", lambda c: c["conditions"]["high"]["telemetry"].update(
                prompt_tokens=c["conditions"]["high"]["telemetry"]["prompt_tokens"] + 1), "telemetry_vs_rows:high"),
            ("A1", lambda c: c["conditions"]["high"]["telemetry"].update(new_tokens=0), "telemetry_vs_rows:high"),
            ("A1", drop(["conditions", "low", "resources"]), "resources:low"),
            ("A1", put(["conditions", "low", "resources", "max_prompt_tokens"], 1), "resources:low"),
            # E1b fields are mandatory and must agree with each other and with the arm
            ("A1", drop(["conditions", "low", "processing", "episode_tokens"]), "processing_fields:low"),
            ("A1", drop(["conditions", "low", "processing", "prompt_token_equivalents"]), "processing_fields:low"),
            ("A1", drop(["conditions", "low", "processing", "declared_per_episode"]), "processing_fields:low"),
            ("A1", drop(["conditions", "low", "processing", "prompt_inclusion_summary"]), "processing_fields:low"),
            ("A1", put(["conditions", "low", "processing", "exposure"], "none"), "processing_exposure:low"),
            ("A1", put(["conditions", "low", "processing", "declared_per_episode", "store_writes"], 0),
             "processing_declared:low"),
            ("O1", put(["conditions", "low", "processing", "declared_per_episode", "store_writes"], 1),
             "processing_declared:low"),
            ("A1", lambda c: proc("low", "episode_tokens")(c).pop(first_id(c)), "processing_maps:low"),
            ("A1", lambda c: proc("low", "prompt_token_equivalents")(c).update({first_id(c): 1}),
             "processing_equivalents:low"),
            ("A1", lambda c: proc("low", "encode_reads")(c).update({first_id(c): 2}), "processing_reads:low"),
            ("A1", put(["conditions", "low", "episodes_presented"], 39), "processing_reads:low"),
            ("A1", lambda c: proc("low", "prompt_inclusion_summary")(c).update(total=0), "processing_summary:low"),
            ("A1", a1_inclusion_off_by_one, "processing_a1:low"),
            ("A0", lambda c: proc("low", "prompt_inclusions")(c).update({first_id(c): 1}), "processing_a0:low"),
            ("O1", o1_no_notes, "processing_o1:low"),
        ]
        for arm, change, reason in cases:
            verdict, check, _ = self.mutate(arm, change)
            self.assertEqual(verdict, "INCOMPLETE", reason)
            self.assertIn(reason, check, reason)
        verdict, check, _ = self.run_collect(dict(self.cells, A0="null"))
        self.assertIn("FAILED pilot_m_A0_0.json not_an_object", check)
        verdict, check, _ = self.run_collect(dict(self.cells, A0="{"))
        self.assertIn("unreadable:JSONDecodeError", check)
        cells = dict(self.cells)
        del cells["O1"]
        verdict, check, _ = self.run_collect(cells)
        self.assertIn("FAILED pilot_m_O1_0.json unreadable:FileNotFoundError", check)

    def test_failed_summary_makes_the_run_incomplete(self):
        original = collect.summarise
        collect.summarise = lambda cells: 1 / 0
        try:
            verdict, check, summary = self.run_collect(self.cells)
        finally:
            collect.summarise = original
        self.assertEqual(verdict, "INCOMPLETE")
        self.assertIn("FAILED SUMMARY.md ZeroDivisionError", check)

    def test_cells_carry_provenance_and_truncation(self):
        class Cutting(FakeModel):
            def cut_off(self, question):
                return question.startswith("Which happened first?")
        cell = realistic_cell("A1", model=Cutting())
        for name, cond in cell["conditions"].items():
            self.assertEqual(len(cond["world_sha256"]), 64)
            self.assertEqual(len(cond["questions_sha256"]), 64)
            rows = cond["rows"]
            cut = [r for r in rows if r["truncated"]]
            self.assertTrue(cut)
            self.assertTrue(all(r["qtype"] == "order" for r in cut))
            self.assertEqual(cond["telemetry"]["truncated"], len(cut))
            proc = cond["processing"]
            for k, n in proc["prompt_inclusions"].items():
                self.assertEqual(proc["prompt_token_equivalents"][k], n * proc["episode_tokens"][k])

    def test_partial_answers_survive_a_failing_phase(self):
        class FailsLater(FakeModel):
            phases_done = 0

            def cut_off(self, question):
                if self.phases_done >= 3:  # high done, low phase1 done, low final fails
                    raise RuntimeError("boom")
                return False
        model = FailsLater()
        out = {}
        original = run_pilot.run_world

        def wrapped(system, world, questions, on_phase=None):
            if on_phase is None:  # the symbolic reference run
                return original(system, world, questions)

            def mark(phase, answers):
                on_phase(phase, answers)
                model.phases_done += 1
            return original(system, world, questions, on_phase=mark)
        run_pilot.run_world = wrapped
        try:
            with self.assertRaises(RuntimeError):
                run_pilot.run_cell(model, "A1", REQUEST["series"], 0, out)
        finally:
            run_pilot.run_world = original
        self.assertEqual(list(out["conditions"]), ["high"])
        self.assertEqual(list(out["partial"]), ["low"])  # finished conditions are not repeated
        self.assertEqual(list(out["partial"]["low"]), ["phase1"])
        self.assertTrue(out["partial"]["low"]["phase1"])

    def test_selection_ignores_lures(self):
        cell = json.loads(json.dumps(self.cells["O1"]))
        for cond in cell["conditions"].values():
            for r in cond["rows"]:
                if r["criterion"] == "E5":
                    r.update(correct=False, category="wrong_value", false_recall=True)
            for phase in ("phase1", "final"):
                cond[phase] = collect.recompute_summary(cond["rows"], phase)
        verdict, check, summary = self.run_collect(dict(self.cells, O1=cell))
        self.assertEqual(verdict, "COMPLETE", check)  # a consistent cell with wrong lures
        self.assertIn("| m | 1 | 1.000 | 1.000 | yes |", summary)

    def test_collector_recomputation_equals_the_scorer(self):
        from episodic_lab.score import summarise
        for cell in self.cells.values():
            for cond in cell["conditions"].values():
                for phase in ("phase1", "final"):
                    rows = [r for r in cond["rows"] if r["phase"] == phase]
                    self.assertTrue(collect.same(collect.recompute_summary(cond["rows"], phase),
                                                 json.loads(json.dumps(summarise(rows)))))


if __name__ == "__main__":
    unittest.main()
