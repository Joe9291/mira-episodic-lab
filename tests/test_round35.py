"""Round 3.5 model-free parts: wordings, worlds, candidates and canonical values, audit."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench" / "m3"))

import audit35  # noqa: E402
from episodic_lab.cands35 import NONE, SELF, candidates, canonical, decide, merge, spans  # noqa: E402
from episodic_lab.env35 import KINDS35, generate_pair35, split_pairs  # noqa: E402
from episodic_lab.wordings35 import SETS, WORDINGS, choose, parse, render  # noqa: E402

EXAMPLES = {
    "placing": {"actor": "Mara Lind", "partner": None, "action": "left", "object": "red cup", "place": "Oak Mill", "event_day": 4},
    "own_put": {"actor": "You", "partner": None, "action": "put", "object": "blue map", "place": "Ash Bridge", "event_day": 7},
    "gave": {"actor": "Tom Reed", "partner": "You", "action": "gave", "object": "old key", "place": "Elm Garden", "event_day": 2},
    "seen": {"actor": "Ida Voss", "partner": None, "action": "was", "object": None, "place": "Fir Station", "event_day": 9},
    "went": {"actor": "You", "partner": None, "action": "went", "object": None, "place": "Pine Harbour", "event_day": 5},
}


class WordingTests(unittest.TestCase):
    def test_every_template_roundtrips(self):
        for etype, groups in WORDINGS.items():
            self.assertEqual(sorted(groups), ["dev", "holdout", "reserve", "template"])
            self.assertEqual([len(groups[g]) for g in ("template", "dev", "holdout", "reserve")], [1, 3, 3, 3])
            for group, templates in groups.items():
                for t in templates:
                    for verb in (("hid", "left", "put") if etype == "placing" else (EXAMPLES[etype]["action"],)):
                        c = dict(EXAMPLES[etype], action=verb)
                        self.assertEqual(parse(render(c, t), etype, t), c, t)

    def test_wording_sets_are_separate(self):
        self.assertEqual(SETS, {"dev": ("template", "dev"), "holdout": ("holdout",), "reserve": ("reserve",)})
        for etype in WORDINGS:
            self.assertEqual(choose(etype, "dev", "k")[0] in ("template", "dev"), True)
            self.assertEqual(choose(etype, "holdout", "k")[0], "holdout")


class WorldTests(unittest.TestCase):
    def test_pairs_are_invariant_and_truths_hold(self):
        for split in ("dev", "ho", "res"):
            for kind in KINDS35:
                for i in range(3):
                    p = generate_pair35(split, i, kind)   # check_truths runs inside
                    a, b = p["worlds"]["A"], p["worlds"]["B"]
                    diff = [j for j, (x, y) in enumerate(zip(a["experiences"], b["experiences"])) if x["text"] != y["text"]]
                    self.assertEqual(diff, [p["critical"]])
                    self.assertEqual([e["frame"] for e in a["experiences"]], [e["frame"] for e in b["experiences"]])
                    self.assertTrue(any(c["object"] == p["same_noun_object"] for c in a["truth_content"]))
                    self.assertEqual(p["same_noun_object"].split(" ", 1)[1], p["object"].split(" ", 1)[1])
                    self.assertNotEqual(p["same_noun_object"], p["object"])
                    gave = sum(c["action"] == "gave" for c in a["truth_content"])
                    self.assertGreaterEqual(gave, 1 if kind != "giver" else 2)
                    if p["family"] == "hist":
                        self.assertEqual(a["final_state"], b["final_state"])
                    wset = {"dev": ("template", "dev"), "ho": ("holdout",), "res": ("reserve",)}[split]
                    self.assertTrue(all(e["frame"].split(":")[1] in wset for e in a["experiences"]))

    def test_model_free_audit_of_the_development_splits(self):
        res = audit35.audit(["dev", "cal", "aud"])
        self.assertEqual(res["problems"], [])
        for split in ("dev", "cal", "aud"):
            self.assertEqual(set(res["coverage"][split].values()), {1.0})
        dev = {e["text"] for p in split_pairs("dev") for w in p["worlds"].values() for e in w["experiences"]}
        cal = {e["text"] for p in split_pairs("cal") for w in p["worlds"].values() for e in w["experiences"]}
        self.assertFalse(dev & cal)


class CandidateTests(unittest.TestCase):
    def test_spans_and_canonical_values(self):
        self.assertEqual(spans("Day 4: at Oak Mill, you saw Ana Bell.")[:4], ["Day", "Day 4", "4", "at"])
        self.assertNotIn("4 at", spans("Day 4: at Oak Mill."))      # never across punctuation
        self.assertEqual(canonical("actor", "you"), SELF)
        self.assertEqual(canonical("partner", "I"), SELF)
        self.assertEqual(canonical("partner", "me"), SELF)
        self.assertEqual(canonical("object", "the Red cup"), "red cup")
        self.assertEqual(canonical("event_day", "12"), 12)
        self.assertIsNone(canonical("event_day", "twelve"))
        self.assertIsNone(canonical("actor", "none"))
        self.assertEqual(canonical("object", "none"), NONE)
        surf = [s for s, _ in candidates("partner", "You got the old key from Tom Reed.")]
        self.assertIn("Tom Reed", surf)
        self.assertIn(NONE, surf)
        self.assertEqual(sorted(c for _, c in candidates("action", "x")), sorted(["hid", "left", "put", "gave", "was", "went"]))

    def test_merge_margin_and_uncertainty(self):
        scored = [("you", SELF, -1.0), ("You", SELF, -0.5), ("Tom Reed", "Tom Reed", -2.0)]
        self.assertEqual(merge(scored), {SELF: -0.5, "Tom Reed": -2.0})          # max over variants
        self.assertEqual(decide(scored, 1.0), (SELF, 1.5, "ok"))                   # margin between DIFFERENT values
        self.assertEqual(decide(scored, 2.0)[2], "unknown")
        self.assertEqual(decide(scored, None)[2], "unknown")                       # no qualifying tau
        self.assertEqual(decide([("a", "A", -1.0), ("b", "B", -1.0)], 0.0)[2], "unknown")   # margin 0
        self.assertEqual(decide([("12", 12, -0.3)], 0.5), (12, None, "single"))
        self.assertEqual(decide([("12", 12, -0.3)], None)[2], "unknown")           # precedence rule


if __name__ == "__main__":
    unittest.main()
