"""Tests: generator, questions, evaluator, statistics, runner and the symbolic arm."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from episodic_lab import score  # noqa: E402
from episodic_lab.questions import (MINIMUM, MINIMUM_QTYPE, _binding_needed,  # noqa: E402
                                    answer_for, make_world, matching)
from episodic_lab.runner import StateChangedWhileAnswering, retention, run_world  # noqa: E402
from episodic_lab.symbolic import SymbolicMemory  # noqa: E402
from episodic_lab.world import Episode, episodes_of, vocabulary  # noqa: E402

PAIRS = [make_world("test", i)[1] for i in range(10)]


def ep(day, actor, place, action, obj, partner=None):
    return Episode(f"id{day}", day, actor, partner, place, action, obj, "early", day - 1,
                   False, "")


# A hand-made world; the expected answers below were written by hand, not computed.
HAND = [ep(1, "Ann Lee", "Mill", "sold", "map"),
        ep(2, "Bob Ray", "Mill", "hid", "map", partner="Ann Lee"),
        ep(3, "Ann Lee", "Forge", "sold", "clock"),
        ep(4, "Bob Ray", "Forge", "cleaned", "clock"),
        ep(5, "Ann Lee", "Garden", "cleaned", "lamp")]


class HandWorldTests(unittest.TestCase):
    def test_answers_written_by_hand(self):
        cases = [("object", dict(person="Ann Lee", action="sold", place="Forge"), ["clock"]),
                 ("place", dict(person="Bob Ray", action="hid", obj="map"), ["Mill"]),
                 ("person", dict(action="hid", place="Mill", obj="map"), ["Bob Ray", "Ann Lee"]),
                 ("object", dict(person="Bob Ray", action="sold", place="Mill"), ["none"]),
                 ("day", dict(person="Ann Lee", action="cleaned", obj="lamp"), ["5"]),
                 ("order", {"a": dict(person="Bob Ray", action="cleaned", obj="clock"),
                            "b": dict(person="Ann Lee", action="sold", obj="map")}, ["B"]),
                 ("latest", dict(person="Bob Ray"), ["Forge"]),
                 ("latest", dict(person="Ann Lee"), ["Garden"]),
                 ("at_day", dict(person="Ann Lee", day=2), ["Mill"]),
                 ("at_day", dict(person="Bob Ray", day=1), ["none"]),
                 ("act", dict(obj="clock"), ["Forge"]),
                 ("find", dict(action="sold", place="Forge", obj="clock"), ["Garden"])]
        for qtype, cue, expected in cases:
            self.assertEqual(answer_for(HAND, qtype, cue), expected, (qtype, cue))

    def test_binding_means_different_answers(self):
        # Astra's counterexample: each dropped cue leaves several episodes, but all of
        # them give the same answer - so the full binding is not needed.
        same = [ep(1, "Ann Lee", "Mill", "repaired", "lantern"),
                ep(2, "Bob Ray", "Mill", "repaired", "lantern"),
                ep(3, "Ann Lee", "Mill", "painted", "lantern"),
                ep(4, "Ann Lee", "Forge", "repaired", "lantern")]
        cue = dict(person="Ann Lee", action="repaired", place="Mill")
        self.assertFalse(_binding_needed(same, cue, "object"))
        varied = [ep(1, "Ann Lee", "Mill", "repaired", "lantern"),
                  ep(2, "Bob Ray", "Mill", "repaired", "clock"),
                  ep(3, "Ann Lee", "Mill", "painted", "map"),
                  ep(4, "Ann Lee", "Forge", "repaired", "lamp")]
        self.assertTrue(_binding_needed(varied, cue, "object"))
        # person questions: a person present in every remaining episode answers them all
        shared = [ep(1, "Ann Lee", "Mill", "hid", "map"),
                  ep(2, "Ann Lee", "Mill", "hid", "clock", partner="Bob Ray"),
                  ep(3, "Ann Lee", "Forge", "hid", "map", partner="Cy Fox"),
                  ep(4, "Ann Lee", "Mill", "sold", "map", partner="Bob Ray")]
        self.assertFalse(_binding_needed(shared, dict(action="hid", place="Mill", obj="map"),
                                         "person"))

    def test_ill_defined_items_are_refused(self):
        with self.assertRaises(ValueError):
            answer_for(HAND, "object", dict(person="Ann Lee", action="sold"))  # two events
        with self.assertRaises(ValueError):
            answer_for(HAND, "act", dict(obj="map"))  # last handling had two people


class WorldTests(unittest.TestCase):
    def test_deterministic(self):
        a = json.dumps(make_world("x", 0)[1]["high"], sort_keys=True)
        self.assertEqual(a, json.dumps(make_world("x", 0)[1]["high"], sort_keys=True))
        self.assertNotEqual(a, json.dumps(make_world("x", 1)[1]["high"], sort_keys=True))

    def test_structure_and_conditions(self):
        for pair in PAIRS:
            high, low = (episodes_of(pair[c][0]) for c in ("high", "low"))
            self.assertEqual([e for e in high if e.block == "early"],
                             [e for e in low if e.block == "early"])
            for eps in (high, low):
                self.assertEqual(sorted(e.day for e in eps), list(range(1, len(eps) + 1)))
                self.assertEqual(len({e.episode_id for e in eps}), len(eps))
                self.assertTrue(any(e.out_of_order for e in eps))
                for e in eps:
                    self.assertIn(f"day {e.day}", e.text.lower())
                    self.assertNotIn(e.episode_id, e.text)
                    self.assertTrue(all(p in e.text for p in e.participants))
                    self.assertNotEqual(e.actor, e.partner)
            early = [e for e in low if e.block == "early"]
            late = [e for e in low if e.block == "followup"]
            self.assertFalse({p for e in early for p in e.participants}
                             & {p for e in late for p in e.participants})
            for field in ("place", "action", "object"):
                self.assertFalse({getattr(e, field) for e in early}
                                 & {getattr(e, field) for e in late}, field)

    def test_every_world_has_out_of_order_narration(self):
        from episodic_lab.world import generate_world
        for i in range(600):
            eps = episodes_of(generate_world(f"order-{i}", early=8, followup=0))
            self.assertTrue(any(e.out_of_order for e in eps), i)

    def test_vocabulary_lists_every_detail(self):
        world = PAIRS[0]["low"][0]
        vocab = vocabulary(world)
        for e in episodes_of(world):
            self.assertIn(e.place, vocab["places"])
            self.assertIn(e.action, vocab["actions"])


class QuestionTests(unittest.TestCase):
    def test_gold_matches_the_rule_and_minimums(self):
        for pair in PAIRS:
            for world, q in pair.values():
                eps = episodes_of(world)
                for g in q["gold"].values():
                    self.assertEqual(answer_for(eps, g["qtype"], g["cue"]), g["gold"])
                for criterion, minimum in MINIMUM.items():
                    self.assertGreaterEqual(q["counts"][criterion], minimum)

    def test_phase1_items_identical_in_both_conditions(self):
        for pair in PAIRS:
            (wh, qh), (wl, ql) = pair["high"], pair["low"]
            ph = {k: v for k, v in qh["gold"].items() if v["phase1"]}
            pl = {k: v for k, v in ql["gold"].items() if v["phase1"]}
            self.assertEqual(ph, pl)
            early = [e for e in episodes_of(wh) if e.block == "early"]
            for g in ph.values():
                self.assertEqual(answer_for(early, g["qtype"], g["cue"]), g["gold"])

    def test_binding_is_needed_for_recall_items(self):
        for pair in PAIRS:
            world, q = pair["high"]
            early = [e for e in episodes_of(world) if e.block == "early"]
            for g in q["gold"].values():
                if g["criterion"] == "E2":
                    for drop in g["cue"]:
                        rest = {k: v for k, v in g["cue"].items() if k != drop}
                        hits = matching(early, **rest)
                        if g["qtype"] == "person":
                            common = set.intersection(*(set(e.participants) for e in hits))
                            self.assertEqual(common, set(), (g["cue"], drop))
                        else:
                            field = "object" if g["qtype"] == "object" else "place"
                            self.assertGreater(len({getattr(e, field) for e in hits}), 1,
                                               (g["cue"], drop))

    def test_source_items_ask_about_repeated_content(self):
        for pair in PAIRS:
            world, q = pair["high"]
            early = [e for e in episodes_of(world) if e.block == "early"]
            for g in q["gold"].values():
                if g["criterion"] == "E4":
                    cue = g["cue"]
                    self.assertIn("place", cue)
                    days = {e.day for e in matching(early, person=cue["person"],
                                                    action=cue["action"], obj=cue["obj"])}
                    self.assertGreaterEqual(len(days), 2)
                    self.assertIn(int(g["gold"][0]), days)

    def test_state_subtype_minimums(self):
        for pair in PAIRS:
            for world, q in pair.values():
                for qtype, minimum in MINIMUM_QTYPE.items():
                    real = sum(g["qtype"] == qtype for g in q["gold"].values())
                    self.assertEqual(q["counts"][qtype], real)
                    self.assertGreaterEqual(real, minimum)

    def test_lures_are_binding_lures_already_at_phase1(self):
        for pair in PAIRS:
            world, q = pair["low"]
            early = [e for e in episodes_of(world) if e.block == "early"]
            for g in q["gold"].values():
                if g["criterion"] != "E5":
                    continue
                self.assertTrue(g["phase1"])
                cue = g["cue"]
                for w, _ in pair.values():
                    self.assertEqual(matching(episodes_of(w), **cue), [])
                keys = list(cue)
                for i, x in enumerate(keys):
                    for y in keys[i + 1:]:
                        self.assertTrue(matching(early, **{x: cue[x], y: cue[y]}), (cue, x, y))

    def test_decision_items_need_two_episodes(self):
        for pair in PAIRS:
            world, q = pair["high"]
            eps = {e.episode_id: e for e in episodes_of(world)}
            for g in q["gold"].values():
                if g["criterion"] == "E7":
                    first, second = (eps[t] for t in g["targets"])
                    self.assertIsNone(first.partner)
                    self.assertNotEqual(first.place, g["gold"][0])
                    self.assertEqual(second.place, g["gold"][0])
                    self.assertGreater(second.day, first.day)

    def test_public_files_hold_no_answers(self):
        world, q = PAIRS[0]["high"]
        for phase in ("phase1", "final"):
            for record in q["public"][phase]:
                self.assertEqual(set(record), {"qid", "text", "answer_type"})
        dump = json.dumps(q["public"])
        for e in episodes_of(world):
            self.assertNotIn(e.episode_id, dump)

    def test_order_items_defeat_presentation_order_strategies(self):
        for pair in PAIRS:
            for world, q in pair.values():
                eps = {e.episode_id: e for e in episodes_of(world)}
                kinds, used, earlier_told, later_told = [], [], 0, 0
                for g in q["gold"].values():
                    if g["criterion"] != "E3a":
                        continue
                    a, b = (eps[t] for t in g["targets"])
                    kinds.append(g["variant"])
                    used += [a.episode_id, b.episode_id]
                    first_told = "A" if a.position < b.position else "B"
                    earlier_told += first_told == g["gold"][0]
                    later_told += first_told != g["gold"][0]
                self.assertEqual(sorted(kinds), ["aligned"] * 4 + ["inverted"] * 4)
                self.assertEqual(len(used), len(set(used)))  # every anchor episode once
                self.assertEqual((earlier_told, later_told), (4, 4))  # both exactly at chance

    def test_order_items_include_out_of_order_pairs(self):
        mixed = 0
        for pair in PAIRS:
            world, q = pair["high"]
            eps = {e.episode_id: e for e in episodes_of(world)}
            for g in q["gold"].values():
                if g["criterion"] == "E3a":
                    a, b = (eps[t] for t in g["targets"])
                    mixed += (a.position < b.position) != (a.day < b.day)
        self.assertGreater(mixed, 0)


class ScorerTests(unittest.TestCase):
    cands = {"person": ["Varo Tellin", "Odile Quist"], "place": ["Mossgate Mill", "Carrow Forge"],
             "object": ["copper lantern", "blue map"]}

    def test_grammar(self):
        p = score.parse
        accepted = [("Varo Tellin.", "person", "Varo Tellin"), ("It was Varo", "person", "Varo Tellin"),
                    ("the lantern", "object", "copper lantern"), ("At Mossgate.", "place", "Mossgate Mill"),
                    ("The answer is Carrow Forge", "place", "Carrow Forge"), ("Day 7", "day", "7"),
                    ("7", "day", "7"), ("B", "choice", "B"), ("Option A", "choice", "A"),
                    ("Mossgate Mill\nbecause Carrow Forge", "place", "Mossgate Mill")]
        for answer, kind, value in accepted:
            self.assertEqual(p(answer, kind, self.cands), ("value", value), answer)
        refused = [("Not Mossgate Mill.", "place"), ("Mossgate Mill or Paris.", "place"),
                   ("red lantern", "object"), ("Paris", "place"), ("Varo or Odile", "person"),
                   ("Tellin", "person"), ("day 7 or 8", "day"), ("A and B", "choice"),
                   ("", "place"), ("Mossgate Mill and Carrow Forge", "place")]
        for answer, kind in refused:
            self.assertEqual(p(answer, kind, self.cands), ("other", None), answer)
        self.assertEqual(p("Nobody.", "person", self.cands), ("none", "none"))
        self.assertEqual(p("I don't know", "place", self.cands), ("uncertain", None))

    def test_categories_and_false_recall(self):
        g = {"criterion": "E5", "qtype": "place", "answer_type": "place", "gold": ["none"],
             "targets": [], "phase1": True, "cue": {}}
        gold = {f"q{i}": dict(g) for i in range(5)}
        answers = {"q0": "none", "q1": "Carrow", "q2": "Paris", "q3": "I don't know",
                   "q4": "Mossgate or Carrow"}
        rows = {r["qid"]: r for r in score.score_world(gold, self.cands, answers, "final")}
        self.assertEqual([rows[f"q{i}"]["category"] for i in range(5)],
                         ["correct", "wrong_value", "other", "uncertain", "other"])
        self.assertEqual([rows[f"q{i}"]["false_recall"] for i in range(5)],
                         [False, True, False, False, False])
        self.assertEqual(rows["q2"]["raw"], "Paris")
        summary = score.summarise(list(rows.values()))["E5"]
        self.assertAlmostEqual(summary["accuracy"], 0.2)
        self.assertAlmostEqual(summary["false_recall"], 0.2)
        self.assertAlmostEqual(summary["categories"]["other"], 0.4)

    def test_statistics(self):
        self.assertAlmostEqual(score.upper_bound(0, 100), 1 - 0.05 ** (1 / 100), places=6)
        self.assertAlmostEqual(score.upper_bound(1, 100), 0.0466, places=3)
        self.assertAlmostEqual(score.lower_bound(18, 20), 0.7174, places=3)
        lo, hi = score.world_rate_bounds({i: False for i in range(20)})
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 1 - 0.05 ** (1 / 20), places=6)
        mean, lo, hi = score.mean_interval([0.5, 0.6, 0.7, 0.8])
        self.assertAlmostEqual(hi - mean, 3.182 * 0.12909944 / 2, places=4)
        self.assertEqual(score.t975(22), 2.086)
        d = score.paired_difference({"w1": 0.9, "w2": 0.8, "w3": 0.85},
                                    {"w3": 0.6, "w1": 0.5, "w2": 0.45})
        self.assertAlmostEqual(d[0], (0.4 + 0.35 + 0.25) / 3)
        with self.assertRaises(ValueError):
            score.paired_difference({"w1": 1.0}, {"w2": 1.0})
        for bad in ({"w1": "False"}, {"w1": 1}, {}):
            with self.assertRaises(ValueError):
                score.world_rate_bounds(bad)


class CheckResultsTests(unittest.TestCase):
    def test_every_bad_result_is_registered_as_incomplete(self):
        import tempfile
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench" / "m0"))
        import check_results
        good = {"status": "OK", "resolved_revision": "a" * 40, "lora_step_s_median": 0.3,
                "peak_rss_mb": 1000.0, "load_s": 0.5, "prefill_tokens_per_s": 700.0}
        cases = {"null": "null", "list": "[]", "garbage": "{", "bool": None, "nan": None,
                 "missing": None, "ok": None}
        for name in cases:
            with tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp)
                for slug, model in check_results.EXPECTED.items():
                    record = dict(good, model_id=model)
                    text = json.dumps(record)
                    if slug == "qwen3-0.6b":
                        if name in ("null", "list", "garbage"):
                            text = cases[name]
                        elif name == "bool":
                            text = json.dumps(dict(record, peak_rss_mb=True))
                        elif name == "nan":
                            text = json.dumps(dict(record, load_s=float("nan")))
                        elif name == "missing":
                            continue
                    (dest / f"m0_{slug}.json").write_text(text)
                complete = check_results.check(dest)
                self.assertEqual(complete, name == "ok", name)
                self.assertEqual((dest / "VERDICT").read_text().strip(),
                                 "COMPLETE" if name == "ok" else "INCOMPLETE")
                self.assertEqual(len((dest / "CHECK.txt").read_text().splitlines()), 4)
                if name in ("null", "list"):
                    self.assertIn("not_an_object", (dest / "CHECK.txt").read_text())

    def test_check_never_raises(self):
        import tempfile
        from unittest.mock import patch
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench" / "m0"))
        import check_results
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(check_results, "problems_of", side_effect=RuntimeError("boom")):
            self.assertFalse(check_results.check(Path(tmp)))
            self.assertEqual((Path(tmp) / "VERDICT").read_text().strip(), "INCOMPLETE")


class _Constant:
    def __init__(self, reply):
        self.reply = reply

    def encode(self, text):
        pass

    def answer(self, text):
        return self.reply

    def state_digest(self):
        return "constant"


class _Cheat(SymbolicMemory):
    """Stores every question it sees: must be rejected by the runner."""

    def answer(self, text):
        self.events.append({"question": text})
        return "none"


class _BufferCheat(SymbolicMemory):
    """Keeps questions OUTSIDE the digested event list: must still be rejected."""

    def __init__(self):
        super().__init__()
        self.seen_questions = []

    def answer(self, text):
        self.seen_questions.append(text)
        return super().answer(text)


class RunnerTests(unittest.TestCase):
    def test_symbolic_arm_solves_every_item(self):
        for pair in PAIRS:
            for world, q in pair.values():
                result = run_world(SymbolicMemory(), world, q)
                self.assertEqual(result["episodes_presented"], result["episodes_in_world"])
                self.assertEqual([r for r in result["rows"] if not r["correct"]], [])
                self.assertEqual(retention(result), {"phase1": 1.0, "final": 1.0})

    def test_retention_uses_only_recall_and_source_items(self):
        rows = [{"criterion": "E2", "phase": "phase1", "correct": False},
                {"criterion": "E4", "phase": "phase1", "correct": True},
                {"criterion": "E3b", "phase": "phase1", "correct": True},
                {"criterion": "E5", "phase": "phase1", "correct": True},
                {"criterion": "E2", "phase": "final", "correct": False},
                {"criterion": "E3b", "phase": "final", "correct": True}]
        self.assertEqual(retention({"rows": rows}), {"phase1": 0.5, "final": 0.0})

    def test_questions_cannot_become_memory(self):
        world, q = PAIRS[0]["high"]
        with self.assertRaises(StateChangedWhileAnswering):
            run_world(_Cheat(), world, q)
        with self.assertRaises(StateChangedWhileAnswering):
            run_world(_BufferCheat(), world, q)

    def test_trivial_baselines(self):
        world, q = PAIRS[0]["high"]
        none = run_world(_Constant("none"), world, q)
        self.assertEqual(none["final"]["E5"]["accuracy"], 1.0)
        self.assertEqual(none["final"]["E2"]["accuracy"], 0.0)
        person = world["early_pool"]["people"][0]
        guess = run_world(_Constant(person), world, q)
        self.assertEqual(guess["final"]["E5"]["accuracy"], 0.0)
        self.assertLess(guess["final"]["E2"]["accuracy"], 0.5)


if __name__ == "__main__":
    unittest.main()
