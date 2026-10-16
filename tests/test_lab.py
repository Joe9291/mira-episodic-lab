"""Milestone 1 tests: generator, questions, evaluator, statistics and the symbolic arm."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from episodic_lab import score  # noqa: E402
from episodic_lab.questions import build_questions  # noqa: E402
from episodic_lab.runner import run_world  # noqa: E402
from episodic_lab.symbolic import SymbolicMemory  # noqa: E402
from episodic_lab.world import episodes_of, generate_world, vocabulary  # noqa: E402

SEEDS = [f"test-{i}" for i in range(12)]


def matches(eps, person=None, action=None, place=None, obj=None):
    return [e for e in eps if (person is None or person in e.participants)
            and (action is None or e.action == action) and (place is None or e.place == place)
            and (obj is None or e.object == obj)]


class WorldTests(unittest.TestCase):
    def test_deterministic_and_seed_dependent(self):
        a = json.dumps(generate_world("x"), sort_keys=True)
        self.assertEqual(a, json.dumps(generate_world("x"), sort_keys=True))
        self.assertNotEqual(a, json.dumps(generate_world("y"), sort_keys=True))
        qa = json.dumps(build_questions(generate_world("x")), sort_keys=True)
        self.assertEqual(qa, json.dumps(build_questions(generate_world("x")), sort_keys=True))

    def test_structure(self):
        for seed in SEEDS:
            for overlap in ("high", "low"):
                w = generate_world(seed, overlap=overlap)
                eps = episodes_of(w)
                self.assertEqual(sorted(e.day for e in eps), list(range(1, len(eps) + 1)))
                self.assertEqual(len({e.episode_id for e in eps}), len(eps))
                self.assertEqual([e.position for e in eps], list(range(len(eps))))
                for e in eps:
                    self.assertIn(f"day {e.day}", e.text.lower())
                    self.assertNotIn(e.episode_id, e.text)
                    self.assertTrue(all(p in e.text for p in e.participants))
                self.assertTrue(any(e.out_of_order for e in eps), seed)
                if overlap == "low":
                    early = {p for e in eps if e.block == "early" for p in e.participants}
                    late = {p for e in eps if e.block == "followup" for p in e.participants}
                    self.assertFalse(early & late)
                    self.assertFalse({e.object for e in eps if e.block == "early"}
                                     & {e.object for e in eps if e.block == "followup"})

    def test_feature_overlap_makes_binding_necessary(self):
        w = generate_world("overlap")
        eps = episodes_of(w)
        for person in w["early_pool"]["people"]:
            self.assertGreaterEqual(len({e.place for e in matches(eps, person=person)}), 1)
        # every person, place and object of the early pool recurs or co-occurs widely
        places_per_person = [len({e.place for e in matches(eps, person=p)})
                             for p in w["early_pool"]["people"]]
        self.assertGreater(max(places_per_person), 1)


class PartnerTests(unittest.TestCase):
    def test_partner_differs_from_actor(self):
        for seed in SEEDS:
            for e in episodes_of(generate_world(seed)):
                self.assertNotEqual(e.actor, e.partner)


class QuestionTests(unittest.TestCase):
    def test_gold_is_unique_and_recomputed(self):
        for seed in SEEDS:
            for overlap in ("high", "low"):
                w = generate_world(seed, overlap=overlap)
                q = build_questions(w)
                eps = {e.episode_id: e for e in episodes_of(w)}
                for qid, g in q["gold"].items():
                    if g["criterion"] == "E5":
                        self.assertEqual(g["gold"], ["none"])
                        self.assertEqual(g["targets"], [])
                    else:
                        self.assertTrue(g["targets"], qid)
                        self.assertTrue(all(t in eps for t in g["targets"]))
                    if g["phase1"]:
                        self.assertTrue(all(eps[t].block == "early" for t in g["targets"]))

    def test_lures_use_known_details_only(self):
        for seed in SEEDS:
            w = generate_world(seed)
            q = build_questions(w)
            vocab = vocabulary(w)
            texts = {r["qid"]: r["text"] for r in q["public"]["final"]}
            for qid, g in q["gold"].items():
                if g["criterion"] != "E5":
                    continue
                names = [n for kind in vocab.values() for n in kind if n in texts[qid]]
                self.assertGreaterEqual(len(names), 2, texts[qid])

    def test_lures_are_binding_lures(self):
        for seed in SEEDS:
            for overlap in ("high", "low"):
                w = generate_world(seed, overlap=overlap)
                eps = episodes_of(w)
                for g in build_questions(w)["gold"].values():
                    if g["criterion"] != "E5":
                        continue
                    cue = g["cue"]
                    self.assertEqual(matches(eps, **cue), [])
                    keys = list(cue)
                    for i, x in enumerate(keys):
                        for y in keys[i + 1:]:
                            self.assertTrue(matches(eps, **{x: cue[x], y: cue[y]}), (cue, x, y))

    def test_action_items_need_two_episodes(self):
        found = 0
        for seed in SEEDS:
            w = generate_world(seed)
            eps = {e.episode_id: e for e in episodes_of(w)}
            for g in build_questions(w)["gold"].values():
                if g["criterion"] == "E7":
                    first, second = (eps[t] for t in g["targets"])
                    self.assertNotEqual(first.episode_id, second.episode_id)
                    self.assertNotEqual(first.place, g["gold"][0])
                    self.assertEqual(second.place, g["gold"][0])
                    self.assertIsNone(first.partner)
                    found += 1
        self.assertGreater(found, 0)

    def test_public_files_hold_no_answers(self):
        w = generate_world("public")
        q = build_questions(w)
        for phase in ("phase1", "final"):
            for record in q["public"][phase]:
                self.assertEqual(set(record), {"qid", "text", "answer_type"})
        dump = json.dumps(q["public"])
        for e in episodes_of(w):
            self.assertNotIn(e.episode_id, dump)

    def test_all_criteria_present_and_order_items_mixed(self):
        crits, mixed = set(), 0
        for seed in SEEDS:
            w = generate_world(seed)
            q = build_questions(w)
            crits |= {g["criterion"] for g in q["gold"].values()}
            eps = {e.episode_id: e for e in episodes_of(w)}
            for g in q["gold"].values():
                if g["criterion"] == "E3a":
                    a, b = (eps[t] for t in g["targets"])
                    mixed += (a.position < b.position) != (a.day < b.day)
        self.assertEqual(crits, {"E2", "E3a", "E3b", "E4", "E5", "E7"})
        self.assertGreater(mixed, 0)


class ScorerTests(unittest.TestCase):
    cands = {"person": ["Varo Tellin", "Odile Quist"], "place": ["Mossgate Mill", "Carrow Forge"],
             "object": ["copper lantern", "blue map"]}

    def test_extraction(self):
        ex = score.extract
        self.assertEqual(ex("Varo Tellin.", "person", self.cands), "Varo Tellin")
        self.assertEqual(ex("It was Varo", "person", self.cands), "Varo Tellin")
        self.assertIsNone(ex("Varo or Odile", "person", self.cands))
        self.assertIsNone(ex("Tellin", "person", self.cands))
        self.assertEqual(ex("Nobody did that.", "person", self.cands), "none")
        self.assertEqual(ex("the lantern", "object", self.cands), "copper lantern")
        self.assertEqual(ex("At Mossgate.", "place", self.cands), "Mossgate Mill")
        self.assertEqual(ex("Day 7", "day", self.cands), "7")
        self.assertIsNone(ex("day 7 or 8", "day", self.cands))
        self.assertEqual(ex("B", "choice", self.cands), "B")
        self.assertIsNone(ex("A and B", "choice", self.cands))
        self.assertIsNone(ex("", "place", self.cands))
        self.assertEqual(ex("Mossgate Mill\nbecause...Carrow Forge", "place", self.cands),
                         "Mossgate Mill")

    def test_invalid_answer_is_wrong_but_not_false_recall(self):
        gold = {"q1": {"criterion": "E5", "qtype": "place", "answer_type": "place",
                       "gold": ["none"], "targets": [], "phase1": True, "cue": {}},
                "q2": {"criterion": "E5", "qtype": "place", "answer_type": "place",
                       "gold": ["none"], "targets": [], "phase1": True, "cue": {}}}
        rows = score.score_world(gold, self.cands, {"q1": "Mossgate or Carrow", "q2": "Carrow"},
                                 "final")
        self.assertEqual([(r["correct"], r["false_recall"]) for r in rows],
                         [(False, False), (False, True)])

    def test_statistics(self):
        self.assertAlmostEqual(score.upper_bound(0, 100), 1 - 0.05 ** (1 / 100), places=6)
        self.assertAlmostEqual(score.upper_bound(1, 100), 0.0466, places=3)
        self.assertGreater(score.false_recall_bound([0, 0, 0], [10, 10, 10], 2.0),
                           score.false_recall_bound([0, 0, 0], [10, 10, 10], 1.0))
        mean, lo, hi = score.mean_interval([0.5, 0.6, 0.7, 0.8])
        self.assertAlmostEqual(mean, 0.65)
        self.assertAlmostEqual(hi - mean, 3.182 * 0.12909944 / 2, places=4)
        self.assertEqual(score.t975(22), 2.086)
        d = score.paired_difference([0.9, 0.8, 0.85], [0.5, 0.45, 0.6])
        self.assertGreater(d[1], 0)


class _Constant:
    def __init__(self, reply):
        self.reply, self.encoded = reply, 0

    def encode(self, text):
        self.encoded += 1

    def answer(self, text):
        return self.reply


class ArmTests(unittest.TestCase):
    def test_symbolic_arm_solves_every_criterion(self):
        for seed in SEEDS:
            for overlap in ("high", "low"):
                result = run_world(SymbolicMemory(), seed, overlap)
                self.assertEqual(result["episodes_presented"], result["episodes_in_world"])
                wrong = [r for r in result["rows"] if not r["correct"]]
                self.assertEqual(wrong, [], (seed, overlap))

    def test_trivial_baselines(self):
        none = run_world(_Constant("none"), "base")
        self.assertEqual(none["final"]["E5"]["accuracy"], 1.0)
        self.assertEqual(none["final"]["E2"]["accuracy"], 0.0)
        self.assertEqual(none["final"]["E5"]["false_recall"], 0.0)
        w = generate_world("base")
        person = w["early_pool"]["people"][0]
        guess = run_world(_Constant(person), "base")
        self.assertEqual(guess["final"]["E5"]["accuracy"], 0.0)
        self.assertLess(guess["final"]["E2"]["accuracy"], 0.5)


if __name__ == "__main__":
    unittest.main()
