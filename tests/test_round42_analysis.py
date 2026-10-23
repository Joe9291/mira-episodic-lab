"""Round 4.2 model-free analysis on synthetic encodings: an oracle encoding must give
E == G; injected errors must be classified and repaired."""
from __future__ import annotations

import unittest

from episodic_lab import analysis42 as A
from episodic_lab import cands42 as C
from episodic_lab import encoder42 as E
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
        enc = oracle_encoding(E.candidate_text(n["header"], n["text"], E.CURRENT), ctx, tr, (wrong_for or {}).get(n["note_id"]))
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



def correction_encoding(change, value_scores=None, since_scores=None, change_margin=5.0):
    """A synthetic correction note: type correction, aspect place, the given change winning
    by change_margin; value / since candidates with the given scores."""
    lab = {"value": "the place or person", "date": "the day", "both": "both"}
    return {"type": [[t, t, 0.0 if t == "correction" else -9.0] for t in C.TYPES],
            "subject": [["red box", "red box", 0.0]],
            "attribute": [["at a place", "location", 0.0], ["with a person", "holder", -9.0]],
            "change": [[s, c, 0.0 if c == change else -change_margin] for s, c in
                       [(s, C.CHANGE_LABELS[s]) for s in C.CHANGE_LABELS]],
            "value": value_scores or [["Elm Yard", "Elm Yard", 0.0], ["Oak Pier", "Oak Pier", -9.0]],
            "valid_from": since_scores or [["7", 7, 0.0], ["9", 9, -9.0]],
            "ref_source": [["Ola", "Ola", 0.0], ["my", "self", -9.0]],
            "ref_day": [["9", 9, 0.0], ["7", 7, -9.0]]}


class ChangePaths(unittest.TestCase):
    """Astra's improvement idea: the three field paths of a correction, an uncertain change
    and a wrong change (the skipped required field must not vanish from the report)."""
    TAUS = {s: 1.0 for s in C.SLOTS}

    def test_three_paths(self):
        for change, value, since in (("value", "Elm Yard", C.KEEP), ("date", C.KEEP, 7), ("both", "Elm Yard", 7)):
            d = A.decide_note(correction_encoding(change), self.TAUS)
            self.assertEqual(d["status"], "ok", change)
            self.assertEqual((d["fields"]["change"], d["fields"]["value"], d["fields"]["valid_from"]), (change, value, since))
            asked = set(d["decisions"])
            self.assertEqual("value" in asked, change != "date")
            self.assertEqual("valid_from" in asked, change != "value")

    def test_uncertain_change_declines(self):
        d = A.decide_note(correction_encoding("value", change_margin=0.5), self.TAUS)
        self.assertEqual((d["status"], d["reason"]), ("declined", "change uncertain"))

    def test_wrong_change_is_reported(self):
        truth = {"type": "correction", "subject": "red box", "attribute": "location", "change": "both",
                 "value": "Elm Yard", "valid_from": 7, "ref_source": "Ola", "ref_day": 9}
        enc = correction_encoding("value")                    # the day change is missed
        d = A.decide_note(enc, self.TAUS)
        self.assertFalse(A.fields_correct(d, truth))
        rep = A.slot_report([{"key": "k", "truth": truth}], {"k": enc}, self.TAUS)
        self.assertEqual(rep["change"]["wrong"], 1)
        self.assertEqual(rep["valid_from"]["wrongly_skipped"], 1)
        cases = A.calibration_cases([{"key": "k", "truth": truth}], {"k": enc})
        self.assertNotIn("valid_from", cases)                 # not asked on the predicted path ...
        self.assertEqual(cases["change"], [(5.0, False)])     # ... the error sits in change
        truth_v = dict(truth, change="value", valid_from=C.KEEP)
        cases = A.calibration_cases([{"key": "k", "truth": truth_v}], {"k": correction_encoding("both")})
        self.assertEqual(cases["valid_from"], [(9.0, False)])  # a "keep" field asked counts as wrong


class Offsets(unittest.TestCase):
    def test_fit_removes_a_label_bias_and_prefers_small_offsets(self):
        # every note prefers "b" by 1.5 although the truth is "a" when its own evidence says so
        rows = [({"a": 0.0, "b": 1.0}, "a")] * 6 + [({"a": 0.0, "b": 3.0}, "b")] * 4
        r = A.fit_offsets(rows, ["a", "b"])
        self.assertEqual((r["right_raw"], r["right"]), (4, 10))
        self.assertEqual(r["offsets"], {"a": 0.0, "b": -1.25})      # smallest |b| in (-3, -1)
        self.assertEqual(r["at_grid_edge"], [])
        self.assertEqual(A.fit_offsets([({"a": 0.0, "b": -1.0}, "a")], ["a", "b"])["offsets"], {"a": 0.0, "b": 0.0})

    def test_grid_edge_reported_and_application(self):
        r = A.fit_offsets([({"a": 0.0, "b": 99.0}, "a")], ["a", "b"])
        self.assertEqual(r["right"], 0)
        enc = {"attribute": [["at a place", "location", -1.0], ["with a person", "holder", -2.0]], "value": [["X", "X", 0.0]]}
        out = A.apply_offsets(enc, {"attribute": {"at a place": 0.0, "with a person": 2.0}})
        self.assertEqual(out["attribute"][1][2], 0.0)
        self.assertEqual(out["value"], enc["value"])

class Rule6(unittest.TestCase):
    """Synthetic cells with 12 questions per world, one of them critical: answering every
    non-critical question right and every critical one wrong gives 11 / 12 = 91.7 % of all
    questions - the overall rate alone would pass; rule 6 must reject it (Astra's test)."""
    FAMS, Q = ("P1", "P2"), 12

    def rows(self):
        rows = []
        for f in self.FAMS:
            for p in range(10):
                for d in (0, 20):
                    for w in "AB":
                        for qn in range(self.Q):
                            crit = qn == 0
                            gold = {"status": "value", "value": "X" if (w == "A" or not crit) else "Y", "ids": []}
                            rows.append({"qid": f"dev-{f}-{p:02d}-{w}-{d}-q{qn}", "pair": f"dev-{f}-{p:02d}",
                                         "family": f, "delay": d, "world": w, "op": "current", "gold": gold, "e2e": True})
        A.mark_critical(rows)
        return rows

    def run_rule(self, rows):
        return A.rule6(rows, self.FAMS, (0, 20), 10, {f: self.Q for f in self.FAMS})

    def test_all_right_passes(self):
        self.assertTrue(self.run_rule(self.rows())["ok"])

    def test_all_critical_wrong_fails_although_the_overall_rate_passes(self):
        rows = self.rows()
        for r in rows:
            if r["critical"]:
                r["e2e"] = False
        res = self.run_rule(rows)
        for cell in res["cells"].values():
            self.assertGreaterEqual(cell["all"][0] * 10, 9 * cell["all"][1])     # overall >= 90 %
            self.assertEqual(cell["critical"][0], 0)
            self.assertFalse(cell["ok"])
        self.assertFalse(res["ok"])

    def test_pair_success_needs_both_worlds(self):
        rows = self.rows()
        for r in rows:                                   # one wrong critical answer in world B of 2 pairs
            if r["critical"] and r["world"] == "B" and r["pair"] in ("dev-P1-01", "dev-P1-02") and r["delay"] == 0:
                r["e2e"] = False
        cell = self.run_rule(rows)["cells"]["P1|0"]
        self.assertEqual(cell["pairs"], [8, 10])
        self.assertFalse(cell["ok"])

    def test_unexpected_denominator_fails(self):
        rows = [r for r in self.rows() if r["pair"] != "dev-P1-03"]
        self.assertFalse(self.run_rule(rows)["ok"])


if __name__ == "__main__":
    unittest.main()
