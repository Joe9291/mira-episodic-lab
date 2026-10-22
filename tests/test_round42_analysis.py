"""Round 4.2 model-free analysis on synthetic encodings: an oracle encoding must give
E == G; injected errors must be classified and repaired."""
from __future__ import annotations

import unittest

from episodic_lab import analysis42 as A
from episodic_lab import cands42 as C
from episodic_lab import r40_world as W40
from episodic_lab import r42_world as W

TAUS = {s: 1.0 for s in C.SLOTS}


def oracle_encoding(note_full, ctx, tr, wrong=None):
    """Gold value scores 0, everything else -5; `wrong` = {slot: value} makes that value win."""
    enc = {}
    for slot in C.SLOTS:
        rows = []
        for s, c in C.candidates(slot, note_full, ctx):
            target = (wrong or {}).get(slot, tr.get(slot))
            rows.append([s, c, 0.0 if c == target else -5.0])
        enc[slot] = rows
    return enc


def world_inputs(pair, inst, world, wrong_for=None):
    reps = inst[world]["reports"]
    by_id = {r["report_id"]: r for r in reps}
    notes, decisions, truths = [], {}, {}
    for r, n in zip(reps, inst[world]["notes"]):
        ctx = {"author": n["author"], "report_day": n["report_day"], "sources": pair["sources"]}
        tr = C.truth(n, r, by_id)
        enc = oracle_encoding(n["header"] + " " + n["text"], ctx, tr, (wrong_for or {}).get(n["note_id"]))
        decisions[n["note_id"]] = A.decide_note(enc, TAUS)
        truths[n["note_id"]] = tr
        notes.append({"note_id": n["note_id"], "author": n["author"], "report_day": n["report_day"]})
    return reps, notes, decisions, truths


class OracleAndFaults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = W.generate_split("dev")

    def test_oracle_encodings_reproduce_gold(self):
        for pair in self.pairs:
            for inst in pair["instances"]:
                for world in "AB":
                    gold, notes, decisions, truths = world_inputs(pair, inst, world)
                    stored, log = A.collect(notes, decisions, pair["ranks"])
                    self.assertEqual(stored, gold, pair["pair"])
                    self.assertEqual(A.collector_errors(notes, decisions, stored, pair["ranks"]), [])

    def test_faults_are_classified_and_repaired(self):
        checked = 0
        for pair in self.pairs[::3]:
            inst = pair["instances"][1]
            gold = inst["A"]["reports"]
            qs = inst["A"]["questions"]
            rel = sorted(A.relevant_note_ids(gold, pair["fact"], pair["anchor"]))
            first = rel[0]
            # decline the first relevant note: make its type uncertain (two equal top scores)
            gold_, notes, decisions, truths = world_inputs(pair, inst, "A")
            decisions[first] = {"status": "declined", "type": None, "fields": {}, "reason": "type uncertain",
                                "decisions": {}}
            stored, _ = A.collect(notes, decisions, pair["ranks"])
            c = A.causes(gold, stored, notes, decisions, truths, pair["fact"], pair["anchor"])
            self.assertIn(first, c["direct"])
            fixed = A.repair(gold, stored, set(c["repair_scope"]) | set(), pair["fact"], pair["anchor"])
            self.assertEqual(W40.audit_world(fixed, pair["ranks"], pair["anchor"], pair["fact"], False), [])
            m_fixed, r_gold = A.answer_all(fixed, qs)[0], A.answer_all(gold, qs)[1]
            self.assertEqual(m_fixed, r_gold)
            checked += 1
        self.assertGreater(checked, 10)


if __name__ == "__main__":
    unittest.main()
