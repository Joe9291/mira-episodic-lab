"""Round 4.1 targeted stale test: generator, S5, failure classes, hand cases."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from episodic_lab import r40_world as W40
from episodic_lab import r41_world as W
from episodic_lab.r40_memory import Memory
from episodic_lab.r40_reference import reference_answers
from episodic_lab.r41_baselines import s5, s5_state

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench/m3"))
import run_round41 as RUN  # noqa: E402

FIELDS = ("report_id", "report_day", "source", "rank", "subject", "attribute", "kind", "value",
          "valid_from", "target_report_id")


class HandCases(unittest.TestCase):
    def test_m_r_and_s5(self):
        d = json.loads((ROOT / "tests/fixtures/r41_conformance.json").read_text())
        n = 0
        for name, w in d["worlds"].items():
            reps = sorted((dict(zip(FIELDS, row), origin="o-" + row[0]) for row in w["reports"]),
                          key=lambda r: (r["report_day"], r["report_id"]))
            for cid, last, now, exp, exp5 in w["checks"]:
                pre = [r for r in reps if r["report_day"] <= last]
                q = {"qid": cid, "op": "current", "now": now, "subject": "key", "attribute": "loc"}
                with self.subTest(case=cid):
                    self.assertEqual(Memory(pre).answer(q), exp)
                    self.assertEqual(reference_answers(pre, [q])[0][cid], exp)
                    self.assertEqual(s5(pre, q), exp5)
                n += 1
        self.assertGreaterEqual(n, 10)
        self.assertTrue(all(c["ok"] for c in RUN.conformance41()))


class Generator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = W.generate_split("dev")

    def test_deterministic_and_sizes(self):
        self.assertEqual(W40.world_digest(self.pairs), W40.world_digest(W.generate_split("dev")))
        self.assertEqual(len(self.pairs), 5 * W.PAIRS["dev"])
        self.assertEqual(5 * W.PAIRS["holdout"] * 2 * (1 + len(W.DELAYS)), 2000)

    def test_structure(self):
        for p in self.pairs:
            for world in "AB":
                before = p["before"][world]
                self.assertTrue(all(r["report_day"] <= p["d3"] - 1 for r in before["reports"]))
                self.assertEqual(before["questions"][0]["now"], p["d3"] - 1)
            self.assertEqual(p["before"]["A"]["reports"], p["before"]["B"]["reports"])
            for inst in p["instances"]:
                ra, rb = inst["A"]["reports"], inst["B"]["reports"]
                self.assertEqual([x["report_id"] for x, y in zip(ra, rb) if x != y], [inst["crit_id"]])
                crit = next(r for r in ra if r["report_id"] == inst["crit_id"])
                self.assertEqual(crit["report_day"], p["d3"])
                relevant = [r for r in ra if (r["subject"], r["attribute"]) == tuple(p["fact"])]
                self.assertEqual(max(r["report_day"] for r in relevant), p["d3"])
                self.assertEqual(len(ra) - inst["n_relevant"], inst["delay"])
                for world in "AB":
                    self.assertEqual(W40.audit_world(inst[world]["reports"], p["ranks"], None, p["fact"], True), [])


class Classes(unittest.TestCase):
    def test_priority(self):
        g = {"status": "value", "value": "Z", "ids": []}
        prev = {"status": "conflict", "values": ["Y", "Z"], "ids": []}
        self.assertEqual(RUN.classify(g, dict(g), prev), "right")
        self.assertEqual(RUN.classify(g, {"status": "conflict", "values": ["Z", "Y"], "ids": []}, prev), "stale")
        self.assertEqual(RUN.classify(g, {"status": "conflict", "values": ["Q", "Y"], "ids": []}, prev), "conflict")
        self.assertEqual(RUN.classify(g, {"status": "unknown", "reason": "no_version"}, prev), "abstain")
        self.assertEqual(RUN.classify(g, {"status": "value", "value": "Q", "ids": []}, prev), "other")

    def test_s5_state_determines_answer(self):
        reps = [dict(zip(FIELDS, row), origin="o-" + row[0]) for row in (
            ["r00001", 1, "ana", 2, "key", "loc", "assert", "Y", 1, None],
            ["r00002", 2, "cy", 1, "key", "loc", "retract", None, None, "r00001"])]
        q = {"qid": "x", "op": "current", "now": 3, "subject": "key", "attribute": "loc"}
        self.assertEqual(s5_state(reps, q), ())
        self.assertEqual(s5(reps, q)["status"], "unknown")       # naive: any source retracts


if __name__ == "__main__":
    unittest.main()
