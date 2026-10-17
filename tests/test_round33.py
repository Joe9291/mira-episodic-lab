"""Round 3.3: environment pairs, agent, interventions, fresh-process decisions, collector."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench" / "m3"))

import collect_round33  # noqa: E402
import run_round33  # noqa: E402
from episodic_lab.env import KINDS, env_encode, generate_pair, render_content  # noqa: E402
from episodic_lab.env_agent import INTERVENTIONS, decide, intervene, write_store  # noqa: E402

SERIES, N = "env-test", 6


class EnvTests(unittest.TestCase):
    def test_pairs_differ_only_in_the_critical_episode(self):
        self.assertEqual(collect_round33.design_problems(SERIES, N), [])

    def test_encoder_and_renderer_agree(self):
        for kind in KINDS:
            pair = generate_pair(f"{SERIES}-0", kind)
            for world in pair["worlds"].values():
                for exp, truth in zip(world["experiences"], world["truth_content"]):
                    self.assertEqual(env_encode(exp["text"]), truth)
                    self.assertEqual(render_content(truth), exp["text"])

    def test_memoryless_policy_cannot_win_both_worlds(self):
        for kind in KINDS:
            for i in range(N):
                pair = generate_pair(f"{SERIES}-{i}", kind)
                a = decide([], pair["worlds"]["A"]["decision"])["action"]
                b = decide([], pair["worlds"]["B"]["decision"])["action"]
                self.assertEqual(a, b)
                self.assertFalse(a["go"] == pair["worlds"]["A"]["truth"] and b["go"] == pair["worlds"]["B"]["truth"])

    def test_intervened_records_keep_text_and_fields_consistent(self):
        pair = generate_pair(f"{SERIES}-1", "giver")
        for name, v in intervene(pair, "A").items():
            if v is None or name == "intact":
                continue
            store = write_store(None, v[0], v[1])
            for r in store.records:
                self.assertEqual(env_encode(r["text"]), {k: r[k] for k in env_encode(r["text"])})


class JobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.result = run_round33.run(SERIES, N, Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_expected_causal_pattern(self):
        s = self.result["summary"]
        for kind in KINDS:
            self.assertEqual(s[f"{kind}:intact"]["pair_success"], 1.0)
            self.assertEqual(s[f"{kind}:none"]["pair_success"], 0.0)
            self.assertEqual(s[f"{kind}:irrelevant_removed"]["success"], 1.0)
            for name in ("swapped_binding", "relevant_removed"):
                self.assertEqual(s[f"{kind}:{name}"]["as_predicted"], 1.0, (kind, name))
        self.assertEqual(self.result["refused"], {"cut": True, "changed": True})

    def test_decision_process_sees_only_store_and_decision(self):
        self.assertNotIn("truth", run_round33.DECIDE)
        self.assertIn("-I", Path(run_round33.__file__).read_text())

    def test_collector(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            req = d / "req.json"
            req.write_text(json.dumps({"series": SERIES, "pairs_per_kind": N}))
            data = dict(self.result, series=SERIES, pairs_per_kind=N, status="OK")
            (d / "r.json").write_text(json.dumps(data))
            collect_round33.main(str(req), str(d / "r.json"), str(d))
            self.assertEqual((d / "VERDICT").read_text().strip(), "COMPLETE", (d / "CHECK.txt").read_text())
            self.assertNotIn("FAIL ", (d / "CHECK.txt").read_text())
            bad = json.loads(json.dumps(data))
            row = next(r for r in bad["rows"] if r["available"])
            row["success"] = not row["success"]
            (d / "r.json").write_text(json.dumps(bad))
            collect_round33.main(str(req), str(d / "r.json"), str(d))
            self.assertIn("rerun_rows_differ", (d / "CHECK.txt").read_text())


if __name__ == "__main__":
    unittest.main()
