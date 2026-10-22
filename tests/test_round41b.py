"""Round 4.1b: one long-running instance receives reports after it was queried."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from episodic_lab.r40_memory import Memory, ReportStore
from episodic_lab.r41b_memory import LiveMemory

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("report_id", "report_day", "source", "rank", "subject", "attribute", "kind", "value",
          "valid_from", "target_report_id")


def worlds():
    d = json.loads((ROOT / "tests/fixtures/r41_conformance.json").read_text())
    for name, w in d["worlds"].items():
        reps = sorted((dict(zip(FIELDS, row), origin="o-" + row[0]) for row in w["reports"]),
                      key=lambda r: (r["report_day"], r["report_id"]))
        yield name, reps, sorted(w["checks"], key=lambda c: (c[1], c[2]))


def q(now):
    return {"qid": "q", "op": "current", "now": now, "subject": "key", "attribute": "loc"}


class NoInvalidation(LiveMemory):
    """A deliberately broken instance: new reports are indexed, but caches are kept."""

    def ingest(self, reports):
        for r in reports:
            self.store.extend([r])
            self._by_fact.setdefault((r["subject"], r["attribute"]), []).append(dict(r))


def run_live(cls, reps, checks):
    """Feed the reports day by day into ONE instance; before each new report day, ask the
    question at the day of the coming report, and ask every check both at its own time and
    at that same earlier query time (in these worlds no claim starts between the two, so
    both answers must equal the hand-computed one)."""
    first_day = checks[0][1]
    live = cls(ReportStore())
    live.ingest([r for r in reps if r["report_day"] <= first_day])
    got = {}
    pending = [r for r in reps if r["report_day"] > first_day]
    for cid, last, now, exp, _ in checks:
        while pending and pending[0]["report_day"] <= last:
            day = pending[0]["report_day"]
            live.answer(q(day))                        # warms the cache for this query time
            batch = [r for r in pending if r["report_day"] == day]
            pending = pending[len(batch):]
            live.ingest(batch)
        got[cid] = (live.answer(q(now)), live.answer(q(last)))
    return got


class LiveInstance(unittest.TestCase):
    def test_hand_cases_through_one_instance(self):
        for name, reps, checks in worlds():
            got = run_live(LiveMemory, reps, checks)
            for cid, last, now, exp, _ in checks:
                with self.subTest(case=cid):
                    self.assertEqual(got[cid], (exp, exp))

    def test_same_query_time_after_ingest(self):
        reps = [dict(zip(FIELDS, row), origin="o-" + row[0]) for row in (
            ["r00001", 1, "self", 3, "key", "loc", "assert", "X", 1, None],
            ["r00002", 2, "ana", 2, "key", "loc", "assert", "Y", 2, None],
            ["r00003", 4, "bo", 2, "key", "loc", "correct", "Z", None, "r00002"])]
        for cls, expect_after in ((LiveMemory, "Z"), (NoInvalidation, "Y")):
            live = cls(ReportStore())
            live.ingest(reps[:2])
            self.assertEqual(live.answer(q(4))["value"], "Y")     # c not yet received
            live.ingest(reps[2:])
            self.assertEqual(live.answer(q(4))["value"], expect_after)

    def test_broken_instance_is_caught_by_the_hand_cases(self):
        caught = 0
        for name, reps, checks in worlds():
            got = run_live(NoInvalidation, reps, checks)
            caught += any(got[c[0]] != (c[3], c[3]) for c in checks)
        self.assertGreater(caught, 0)

    def test_store_on_disk_matches_and_rejects_disorder(self):
        name, reps, checks = next(worlds())
        with tempfile.TemporaryDirectory() as tmp:
            live = LiveMemory(ReportStore(Path(tmp) / "s.jsonl"))
            live.ingest(reps)
            reloaded = Memory(ReportStore(Path(tmp) / "s.jsonl", expect=live.store.seal()).reports)
            self.assertEqual(reloaded.answer(q(9)), live.answer(q(9)))
            with self.assertRaises(ValueError):
                live.ingest([reps[0]])


if __name__ == "__main__":
    unittest.main()
