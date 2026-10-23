"""Round 4.2 extractor contract (model-free): with the CURRENT prompt's candidate text the
true value of every slot of the true note type is a candidate (development split; the
audit script covers all splits), and the current worked examples answer with a
candidate of their own text and use no word of the world vocabulary."""
from __future__ import annotations

import re
import unittest

from episodic_lab import cands42 as C
from episodic_lab import encoder42 as E
from episodic_lab import r40_world as W40
from episodic_lab import r42_world as W


def coverage_misses(split):
    misses, n = [], 0
    for pair in W.iter_pairs(split):
        for inst in pair["instances"]:
            for world in "AB":
                reps = inst[world]["reports"]
                by_id = {r["report_id"]: r for r in reps}
                for r, note in zip(reps, inst[world]["notes"]):
                    ctx = {"author": note["author"], "report_day": note["report_day"], "sources": pair["sources"]}
                    tr = C.truth(note, r, by_id)
                    full = E.candidate_text(note["header"], note["text"], E.CURRENT)
                    n += 1
                    for slot in C.used_slots(tr["type"], tr):
                        val = tr[slot]
                        cands = [c for s, c in C.candidates(slot, full, ctx) if C.allowed_surface(slot, s, tr["type"])]
                        if val not in cands:
                            misses.append((slot, val, note["text"]))
    return misses, n


class Extractor(unittest.TestCase):
    def test_true_values_are_candidates_on_dev(self):
        misses, n = coverage_misses("dev")
        self.assertGreater(n, 1000)
        self.assertEqual(misses[:5], [])

    def test_current_examples_answer_with_their_own_candidates(self):
        ctx = {"author": "self", "report_day": 12, "sources": ["Kai", "Ola", "Pim", "self"]}
        for header, text, answers in {"p4": E.EXAMPLES_P4, "p5": E.EXAMPLES_P5, "p6": E.EXAMPLES_P6}[E.CURRENT]:
            full = E.candidate_text(header, text, E.CURRENT)
            for slot, ans in answers.items():
                self.assertIn(ans, [s for s, _ in C.candidates(slot, full, ctx)], (slot, text))

    def test_examples_outside_the_world_vocabulary(self):
        vocab = {w.lower() for lst in (W40.FIRST, W40.LAST, W40.PLACE_STEM, W40.PLACE_KIND, W40.OBJ_ADJ, W40.OBJ_NOUN)
                 for x in lst for w in x.split()}
        for _, text, answers in E.EXAMPLES_P4 + E.EXAMPLES_P5 + E.EXAMPLES_P6:
            for slot in ("subject", "value", "person", "place", "ref_source"):
                for w in str(answers.get(slot, "")).split():
                    self.assertNotIn(w.lower(), vocab, (slot, text))
            for name in re.findall(r"\b[A-Z][a-z]+\b", text):
                if name not in ("Update", "Correction", "My", "Please", "Withdraw", "Forget", "According", "As",
                                "You", "On", "Your", "I", "The"):
                    self.assertNotIn(name.lower(), vocab, text)

    def test_current_examples_are_balanced_per_type(self):
        import collections
        ex = E.EXAMPLES_P6
        for t in ("statement", "repeated statement", "correction", "retraction"):
            asp = collections.Counter(a["attribute"] for _, _, a in ex if a["type"] == t)
            self.assertEqual(len(asp), 2, t)
            self.assertEqual(len(set(asp.values())), 1, (t, asp))
        corr = collections.Counter((a["attribute"], a["change"]) for _, _, a in ex if a["type"] == "correction")
        self.assertEqual(corr, collections.Counter({(x, c): 1 for x in C.ASPECT_LABELS for c in C.CHANGE_LABELS}))
        self.assertTrue(all("keep" not in a.values() for _, _, a in ex))
        self.assertEqual(E.CURRENT, "p6")

    def test_messages_hide_the_header(self):
        msgs = E.messages("ref_source", "Day 17, your own note.", "Forget Gorvin's report of day 14 about who has the blue ledger.", E.CURRENT)
        self.assertTrue(all("your own note" not in m["content"] for m in msgs))


if __name__ == "__main__":
    unittest.main()
