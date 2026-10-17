"""Round 3.3: environment pairs, reference path, memory-side variants, per-case fresh
decision processes, collector with separate verdict and milestone."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench" / "m3"))

import collect_round33  # noqa: E402
import run_round33  # noqa: E402
from episodic_lab import env_agent  # noqa: E402
from episodic_lab.env import KINDS, env_encode, generate_pair, render_content  # noqa: E402
from episodic_lab.env_agent import decide, derive_variant, write_store  # noqa: E402
from episodic_lab.env_reference import INTERVENTIONS, apply_to_events, plan, predictions  # noqa: E402

SERIES, N = "env-test", 3


class EnvTests(unittest.TestCase):
    def test_pairs_differ_only_in_the_critical_episode(self):
        self.assertEqual(collect_round33.design_problems(SERIES, 8), [])

    def test_encoder_and_renderer_agree(self):
        for kind in KINDS:
            pair = generate_pair(f"{SERIES}-0", kind)
            for world in pair["worlds"].values():
                for exp, truth in zip(world["experiences"], world["truth_content"]):
                    self.assertEqual(env_encode(exp["text"]), truth)
                    self.assertEqual(render_content(truth), exp["text"])

    def test_memoryless_policy_cannot_win_both_worlds(self):
        for kind in KINDS:
            for i in range(8):
                pair = generate_pair(f"{SERIES}-{i}", kind)
                a = decide([], pair["worlds"]["A"]["decision"])["action"]
                b = decide([], pair["worlds"]["B"]["decision"])["action"]
                self.assertEqual(a, b)
                self.assertFalse(a["go"] == pair["worlds"]["A"]["truth"] and b["go"] == pair["worlds"]["B"]["truth"])

    def test_memory_side_and_reference_side_agree_on_a_correct_encoding(self):
        for kind in KINDS:
            pair = generate_pair(f"{SERIES}-1", kind)
            for name in ("A", "B"):
                w = pair["worlds"][name]
                store = write_store(None, w["experiences"])
                for spec in plan(pair, name).values():
                    if spec is not None:
                        self.assertEqual(derive_variant(spec, store.records), apply_to_events(spec, w["truth_content"]))

    def test_an_encoding_error_cannot_change_a_prediction(self):
        pair = generate_pair(f"{SERIES}-2", "hidden")
        crit_text = pair["worlds"]["A"]["experiences"][pair["critical"]]["text"]
        before = predictions(pair, "A")

        def faulty(text):
            c = env_encode(text)
            return dict(c, place="Wrong Place") if text == crit_text else c
        with mock.patch.object(env_agent, "env_encode", faulty):
            store = write_store(None, pair["worlds"]["A"]["experiences"])
            self.assertEqual(predictions(pair, "A"), before)
            self.assertEqual(store.records[pair["critical"]]["place"], "Wrong Place")
            self.assertNotEqual(decide(store.records, pair["worlds"]["A"]["decision"])["action"]["go"],
                                before["intact"])


class ReferenceTests(unittest.TestCase):
    def test_reference_rules(self):
        from episodic_lab.env_reference import reference_decision
        dec = {"goal": "Find the person who gave you the red cup.", "options": ["A Place", "B Place", "C Place"]}
        gave = lambda who, day, place: {"actor": who, "partner": "You", "action": "gave", "object": "red cup",
                                        "place": place, "event_day": day}
        seen = lambda who, day, place: {"actor": who, "partner": None, "action": "was", "object": None,
                                        "place": place, "event_day": day}
        self.assertEqual(reference_decision([gave("Ana Bell", 1, "B Place"), seen("Ana Bell", 2, "C Place")], dec), "C Place")
        self.assertEqual(reference_decision([gave("Ana Bell", 1, "B Place"), gave("Cal Dorr", 2, "C Place")], dec),
                         "A Place")  # two givers: no unique answer, explore
        self.assertEqual(reference_decision([], dec), "A Place")


class JobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calls = 0
        original = run_round33.fresh_decision

        def counting(item, workdir):
            cls.calls += 1
            return original(item, workdir)
        cls.tmp = tempfile.TemporaryDirectory()
        with mock.patch.object(run_round33, "fresh_decision", counting):
            cls.result = run_round33.run(SERIES, N, Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_one_fresh_process_per_case(self):
        cases = sum(r["available"] for r in self.result["rows"])
        self.assertEqual(self.calls, cases + 2)  # plus the cut-off and changed-store probes
        self.assertEqual(cases, len({(r["kind"], r["seed"], r["world"], r["intervention"])
                                     for r in self.result["rows"] if r["available"]}))

    def test_expected_causal_pattern_and_traces(self):
        s = self.result["summary"]
        for kind in KINDS:
            self.assertEqual(s[f"{kind}:intact"]["pair_success"], 1.0)
            self.assertEqual(s[f"{kind}:none"]["pair_success"], 0.0)
            self.assertEqual(s[f"{kind}:irrelevant_removed"]["success"], 1.0)
            for name in ("swapped_binding", "relevant_removed"):
                self.assertEqual(s[f"{kind}:{name}"]["as_predicted"], 1.0, (kind, name))
        self.assertEqual(self.result["refused"], {"cut": True, "changed": True})
        memory_rows = [r for r in self.result["rows"] if r.get("policy") == "memory"]
        self.assertTrue(memory_rows and all(r["result"]["status"] == "ok" and r["result"]["ids"] for r in memory_rows))

    def test_criteria_check_the_numbers_of_cases(self):
        s = json.loads(json.dumps(self.result["summary"]))
        self.assertTrue(all(ok for _, ok in collect_round33.criteria(s, N)))
        s["hidden:relevant_removed"]["n"] -= 1
        self.assertFalse(dict(collect_round33.criteria(s, N))[
            "every case planned for intact, none, random, relevant_removed is available"])
        s = json.loads(json.dumps(self.result["summary"]))
        s["giver:swapped_binding"]["n_informative"] = 0
        self.assertFalse(all(ok for _, ok in collect_round33.criteria(s, N)))

    def test_collector_verdict_and_milestone(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            req = d / "req.json"
            req.write_text(json.dumps({"series": SERIES, "pairs_per_kind": N}))
            import hashlib
            data = dict(self.result, schema=run_round33.SCHEMA, series=SERIES, pairs_per_kind=N, status="OK",
                        provenance={"code_commit": "c1",
                                    "request_sha256": hashlib.sha256(req.read_bytes()).hexdigest()})
            (d / "r.json").write_text(json.dumps(data))
            collect_round33.main(str(req), str(d / "r.json"), str(d), "c1")
            self.assertEqual(((d / "VERDICT").read_text().strip(), (d / "MILESTONE").read_text().strip()),
                             ("COMPLETE", "PASS"), (d / "CHECK.txt").read_text())
            for change, reason in (
                    (lambda x: next(r for r in x["rows"] if r["available"]).update(success=False), "rerun_rows_differ"),
                    (lambda x: x["provenance"].update(request_sha256="0"), "provenance:request"),
                    (lambda x: x.update(schema="other"), "schema"),
                    (lambda x: x.update(refused={"cut": True, "changed": False}), "store_integrity")):
                bad = json.loads(json.dumps(data))
                change(bad)
                (d / "r.json").write_text(json.dumps(bad))
                collect_round33.main(str(req), str(d / "r.json"), str(d), "c1")
                self.assertIn(reason, (d / "CHECK.txt").read_text())
                self.assertEqual((d / "MILESTONE").read_text().strip(), "FAIL")
            (d / "r.json").write_text(json.dumps(data))
            with mock.patch.object(collect_round33, "criteria", lambda s, n: [("forced failure", False)]):
                collect_round33.main(str(req), str(d / "r.json"), str(d), "c1")
            self.assertEqual(((d / "VERDICT").read_text().strip(), (d / "MILESTONE").read_text().strip()),
                             ("COMPLETE", "FAIL"))
            collect_round33.main(str(req), str(d / "r.json"), str(d), "c2")
            self.assertIn("provenance:commit", (d / "CHECK.txt").read_text())


if __name__ == "__main__":
    unittest.main()
