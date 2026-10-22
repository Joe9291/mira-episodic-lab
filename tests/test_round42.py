"""Round 4.2 (phase B) model-free checks: wordings, inverse parsers, worlds."""
from __future__ import annotations

import itertools
import re
import unittest

from episodic_lab import r42_wordings as WD
from episodic_lab import r42_world as W


def expected_meaning(r, by_id, t, sub):
    if t == "meeting":
        m = re.fullmatch(r"event:met (.+) at (.+)", r["subject"])
        return {"person": m[1], "place": m[2], "day": r["value"]}
    if t == "statement":
        return {"subject": r["subject"], "value": r["value"], "valid_from": r["valid_from"]}
    ref = W.reference_of(r, by_id)
    if t == "repeat":
        return {"subject": r["subject"], "value": r["value"], "valid_from": r["valid_from"],
                "ref_source": ref["source"], "ref_day": ref["report_day"]}
    if t == "correction":
        return {"subject": r["subject"], "value": r["value"] or "keep",
                "valid_from": r["valid_from"] if r["valid_from"] is not None else "keep",
                "ref_source": ref["source"], "ref_day": ref["report_day"]}
    return {"subject": r["subject"], "ref_source": ref["source"], "ref_day": ref["report_day"]}


class Wordings(unittest.TestCase):
    def test_every_frame_round_trips_on_dev_reports(self):
        n = 0
        seen = set()
        for pair in W.iter_pairs("dev"):
            for inst in pair["instances"]:
                reps = inst["A"]["reports"]
                by_id = {r["report_id"]: r for r in reps}
                for pos, r in enumerate(reps):
                    t, sub = WD.note_type(r, by_id)
                    for frame in range(10):
                        text = WD.render(r, by_id, frame, f"t|{pair['pair']}|{pos}")
                        got = WD.inverse(text, t, None if t == "meeting" else r["attribute"], frame, sub,
                                         r["source"], r["report_day"])
                        if t == "statement" and got["valid_from"] == "not stated":
                            got["valid_from"] = r["report_day"]
                        self.assertEqual(got, expected_meaning(r, by_id, t, sub), text)
                        seen.add((t, None if t == "meeting" else r["attribute"], sub, frame))
                        n += 1
        self.assertGreater(n, 10000)
        needed = {(t, a, s, f) for f in range(10) for (t, a, s) in
                  [("statement", "location", None), ("statement", "holder", None), ("meeting", None, None)]
                  + [(t, a, None) for t in ("repeat", "retraction") for a in ("location", "holder")]
                  + [("correction", a, s) for a in ("location", "holder") for s in ("value", "date", "both")]}
        self.assertEqual(needed - seen, set())


class Worlds(unittest.TestCase):
    def test_references_unique_pairs_invariant_splits_disjoint(self):
        texts = {}
        for split in ("dev", "cal", "audit", "holdout"):
            texts[split] = set()
            for pair in W.iter_pairs(split):
                for inst in pair["instances"]:
                    for world in "AB":
                        self.assertEqual(W.ambiguous_references(inst[world]["reports"]), [])
                        texts[split] |= {n["header"] + " " + n["text"] for n in inst[world]["notes"]}
                    diff = [a["note_id"] for a, b in zip(inst["A"]["notes"], inst["B"]["notes"]) if a != b]
                    self.assertLessEqual(len(diff), 1)
                    self.assertTrue(set(diff) <= {inst["crit_id"]})
                    frames = {n["frame"] for n in inst["A"]["notes"]}
                    self.assertTrue(frames <= set(WD.SPLIT_FRAMES[split]))
        for a, b in itertools.combinations(texts, 2):
            self.assertEqual(texts[a] & texts[b], set(), (a, b))


if __name__ == "__main__":
    unittest.main()
