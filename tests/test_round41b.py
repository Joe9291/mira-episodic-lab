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
    """ONE instance, started EMPTY; the reports arrive day by day. Before each day block
    the instance is queried at that day (a warmed cache for that query time); each check
    is answered as soon as all reports up to its prefix day have arrived - at its own time
    and at its prefix day (in these worlds no claim starts between the two, so both must
    equal the hand-computed answer)."""
    live = cls(ReportStore())
    got = {}
    days = sorted({r["report_day"] for r in reps})
    todo = list(checks)
    for day in days:
        for cid, last, now, exp, _ in [c for c in todo if c[1] < day]:
            got[cid] = (live.answer(q(now)), live.answer(q(last)))
        todo = [c for c in todo if c[1] >= day]
        live.answer(q(day))
        live.ingest([r for r in reps if r["report_day"] == day])
    for cid, last, now, exp, _ in todo:
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

    def test_duplicate_id_is_refused_without_side_effects(self):
        name, reps, checks = next(worlds())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            live = LiveMemory(ReportStore(path))
            live.ingest(reps)
            seal, before = live.store.seal(), live.answer(q(20))
            later = dict(reps[0], report_day=30, subject="other", valid_from=30)   # same id, later day, other fact
            with self.assertRaises(ValueError):
                live.ingest([later])
            with self.assertRaises(ValueError):                                   # duplicate inside one batch
                live.ingest([dict(later, report_id="r00090"), dict(later, report_id="r00090", report_day=31)])
            self.assertEqual(live.store.seal(), seal)
            self.assertEqual(live.answer(q(20)), before)
            self.assertEqual(Memory(ReportStore(path, expect=seal).reports).answer(q(20)), before)

    def test_restart_then_ingest(self):
        name, reps, checks = next(worlds())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            first = LiveMemory(ReportStore(path))
            first.ingest(reps)
            seal = first.store.seal()
            again = LiveMemory(ReportStore(path, expect=seal))                   # reload as a live instance
            self.assertEqual(again.answer(q(9))["value"], "Z")
            new = dict(zip(FIELDS, ["r00009", 9, "self", 3, "key", "loc", "assert", "W", 9, None]), origin="o-r00009")
            again.ingest([new])
            self.assertEqual(again.answer(q(9)), {"status": "value", "value": "W", "ids": ["r00009"]})
            self.assertEqual(Memory(ReportStore(path).reports).answer(q(9)), again.answer(q(9)))

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
