"""Round 3.4 step 1: history goals with an identical final state, current-state baseline,
independent reference, one store per world, collector with verdict and milestone."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench" / "m3"))

import collect_round34  # noqa: E402
import run_round34  # noqa: E402
from episodic_lab import env_agent  # noqa: E402
from episodic_lab.env_agent import derive_variant, write_store  # noqa: E402
from episodic_lab.history_agent import (decide, history_place, parse_goal, state_decide,  # noqa: E402
                                        state_only_encode)
from episodic_lab.history_env import GOAL_NAMES, KINDS, generate_pair  # noqa: E402
from episodic_lab.history_reference import apply_to_events, plan, predictions  # noqa: E402
from episodic_lab.memory import EpisodeStore  # noqa: E402

SERIES, N = "hist-test", 3
ORIGINAL = env_agent.env_encode


class DesignTests(unittest.TestCase):
    def test_pairs_identical_final_state_and_truth_pattern(self):
        self.assertEqual(collect_round34.design_problems(SERIES, 10), [])

    def test_baseline_state_cannot_tell_the_worlds_apart(self):
        for kind in KINDS:
            for i in range(6):
                pair = generate_pair(f"{SERIES}-{i}", kind)
                a, b = (state_only_encode(pair["worlds"][w]["experiences"]) for w in "AB")
                self.assertEqual(a, b)
                for goal in GOAL_NAMES:
                    da, db = (state_decide(a, pair["worlds"][w]["decisions"][goal])["action"] for w in "AB")
                    self.assertEqual(da, db)

    def test_goal_texts_parse(self):
        for kind in KINDS:
            pair = generate_pair(f"{SERIES}-0", kind)
            for goal, d in pair["worlds"]["A"]["decisions"].items():
                self.assertEqual(parse_goal(d["goal"]), (kind, pair["target"], goal))


class OperatorTests(unittest.TestCase):
    def store(self, rows):
        s = EpisodeStore()
        for i, (day, place) in enumerate(rows):
            s.append(f"r{i}", {"actor": "Ana Bell", "partner": None, "action": "hid", "object": "red cup",
                               "place": place, "event_day": day})
        return s.records

    def test_order_and_ambiguity(self):
        recs = self.store([(5, "Oak Mill"), (2, "Ash Mill"), (9, "Elm Mill")])
        self.assertEqual([history_place(recs, "object", "red cup", w).value for w in ("first", "previous", "current")],
                         ["Ash Mill", "Oak Mill", "Elm Mill"])
        self.assertEqual(history_place(self.store([(5, "Oak Mill"), (None, "Ash Mill")]), "object", "red cup",
                                       "first").status, "ambiguous")
        self.assertEqual(history_place(self.store([(5, "Oak Mill"), (5, "Ash Mill")]), "object", "red cup",
                                       "current").status, "ambiguous")
        one = self.store([(5, "Oak Mill")])
        self.assertEqual(history_place(one, "object", "red cup", "previous").status, "no_observation")
        self.assertEqual(history_place(one, "person", "Ana Bell", "current").value, "Oak Mill")


class ReferenceTests(unittest.TestCase):
    def test_memory_side_and_reference_side_agree(self):
        for kind in KINDS:
            for i in range(4):
                pair = generate_pair(f"{SERIES}-{i}", kind)
                for name in "AB":
                    w = pair["worlds"][name]
                    store = write_store(None, w["experiences"])
                    for spec in plan(pair, name).values():
                        if spec is not None:
                            self.assertEqual(derive_variant(spec, store.records),
                                             apply_to_events(spec, w["truth_content"]))

    def test_every_planned_swap_changes_the_first_goal_only(self):
        for kind in KINDS:
            for i in range(10):
                pair = generate_pair(f"{SERIES}-{i}", kind)
                for name in "AB":
                    pred = predictions(pair, name)
                    self.assertIsNotNone(pred["old_swapped"])
                    self.assertNotEqual(pred["old_swapped"]["first"], pred["intact"]["first"])
                    self.assertEqual({g: pred["old_swapped"][g] for g in ("current", "previous")},
                                     {g: pred["intact"][g] for g in ("current", "previous")})

    def test_an_encoding_error_cannot_change_a_prediction(self):
        pair = generate_pair(f"{SERIES}-1", "object")
        w = pair["worlds"]["A"]
        old_text = w["experiences"][pair["critical"]]["text"]
        before = predictions(pair, "A")

        def faulty(text):
            c = ORIGINAL(text)
            return dict(c, place="Wrong Place") if text == old_text else c
        with mock.patch.object(env_agent, "env_encode", faulty):
            store = write_store(None, w["experiences"])
        self.assertEqual(predictions(pair, "A"), before)
        self.assertEqual(store.records[pair["critical"]]["place"], "Wrong Place")
        first = decide(store.records, w["decisions"]["first"])["action"]["go"]
        current = decide(store.records, w["decisions"]["current"])["action"]["go"]
        self.assertNotEqual(first, before["intact"]["first"])
        self.assertEqual(current, before["intact"]["current"])  # the old episode does not control "current"


class JobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calls = 0
        original = run_round34.fresh_decision

        def counting(item, workdir):
            cls.calls += 1
            return original(item, workdir)
        cls.tmp = tempfile.TemporaryDirectory()
        with mock.patch.object(run_round34, "fresh_decision", counting):
            cls.result = run_round34.run(SERIES, N, Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_one_fresh_process_per_case_and_one_store_per_world(self):
        cases = sum(r["available"] for r in self.result["rows"])
        self.assertEqual(self.calls, cases + 2)  # plus the cut-off and changed-store probes
        self.assertTrue(collect_round34.one_store_per_world(self.result["rows"]))
        rows = json.loads(json.dumps(self.result["rows"]))
        r = next(x for x in rows if x["system"] == "episodic" and x["available"] and x["goal"] == "first")
        r["seal"] = "other"
        self.assertFalse(collect_round34.one_store_per_world(rows))

    def test_baseline_answers_only_the_current_goal(self):
        rows = [r for r in self.result["rows"] if r["system"] == "state_only"]
        self.assertTrue(all(r["policy"] == ("memory" if r["goal"] == "current" else "explore") for r in rows))

    def test_criteria_pass_and_detect_failures(self):
        s = self.result["summary"]
        self.assertTrue(all(ok for _, ok in collect_round34.criteria(s, N)), collect_round34.criteria(s, N))
        for key, field, value in (("object:state_only:intact:first", "pair_success", 0.5),
                                  ("person:episodic:old_removed:current", "unchanged", 0.9),
                                  ("object:episodic:last_removed:first", "unchanged", 0.9),
                                  ("person:episodic:old_swapped:first", "as_predicted_informative", 0.5),
                                  ("object:episodic:irrelevant_removed:previous", "success", 0.9),
                                  ("person:episodic:intact:first", "n", 1),
                                  ("object:episodic:none:first", "pair_success", 0.5)):
            bad = json.loads(json.dumps(s))
            bad[key][field] = value
            self.assertFalse(all(ok for _, ok in collect_round34.criteria(bad, N)), key)

    def test_collector_verdict_and_milestone(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            req = d / "req.json"
            req.write_text(json.dumps({"series": SERIES, "pairs_per_kind": N}))
            data = dict(self.result, schema=run_round34.SCHEMA, series=SERIES, pairs_per_kind=N, status="OK",
                        provenance={"code_commit": "c1",
                                    "request_sha256": hashlib.sha256(req.read_bytes()).hexdigest()})

            def collect(x, commit="c1"):
                (d / "r.json").write_text(json.dumps(x))
                collect_round34.main(str(req), str(d / "r.json"), str(d), commit)
                return ((d / "VERDICT").read_text().strip(), (d / "MILESTONE").read_text().strip(),
                        (d / "CHECK.txt").read_text())
            verdict, milestone, check = collect(data)
            self.assertEqual((verdict, milestone), ("COMPLETE", "PASS"), check)
            for change, reason in (
                    (lambda x: next(r for r in x["rows"] if r["available"]).update(action="Nowhere"), "rerun_rows_differ"),
                    (lambda x: x["stored"].update(extra={"records": 1, "state_entries": 1}),
                     "rerun_summary_hashes_or_stored_differ"),
                    (lambda x: x["provenance"].update(request_sha256="0"), "provenance:request"),
                    (lambda x: x.update(schema="other"), "schema"),
                    (lambda x: x.update(refused={"cut": True, "changed": False}), "store_integrity")):
                bad = json.loads(json.dumps(data))
                change(bad)
                verdict, milestone, check = collect(bad)
                self.assertIn(reason, check)
                self.assertEqual((verdict, milestone), ("INCOMPLETE", "FAIL"))
            self.assertIn("provenance:commit", collect(data, "c2")[2])
            # the collector's own re-run of the integrity probes must agree with the stored flags
            real_run = run_round34.run
            with mock.patch.object(collect_round34.run_round34, "run",
                                   lambda *a: dict(real_run(*a), refused={"cut": True, "changed": False})):
                self.assertIn("store_integrity", collect(data)[2])
            with mock.patch.object(collect_round34, "criteria", lambda s, n: [("forced failure", False)]):
                self.assertEqual(collect(data)[:2], ("COMPLETE", "FAIL"))

    def test_design_failure_is_reported(self):
        with mock.patch.object(collect_round34, "generate_pair",
                               lambda seed, kind: _broken(generate_pair(seed, kind))):
            self.assertTrue(collect_round34.design_problems(SERIES, 2))


def _broken(pair):
    pair["worlds"]["B"]["final_state"]["objects"][pair["object"]] = "Elsewhere Place"
    return pair


if __name__ == "__main__":
    unittest.main()
