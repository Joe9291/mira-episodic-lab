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


# ----------------------------------------------------------------- model-free analysis and the jobs
import json  # noqa: E402
import tempfile  # noqa: E402
from unittest import mock  # noqa: E402

import collect_round35  # noqa: E402
import run_round35  # noqa: E402
from episodic_lab import analysis35 as A  # noqa: E402
from episodic_lab.cands35 import SLOTS, truth_value  # noqa: E402
from episodic_lab.encoder35 import QUESTIONS, encode_text  # noqa: E402


def fake_scorer(truth, prefer=None):
    """Scores the true canonical value highest; `prefer(slot, surface, want)` may override."""
    def scorer(msgs, surfaces):
        text = msgs[1]["content"].split("Note: ", 1)[1].split("\n\nQuestion: ")[0]
        q = msgs[1]["content"].split("\n\nQuestion: ")[1]
        slot = next(s for s, qq in QUESTIONS.items() if qq == q)
        want = truth_value(slot, truth[text])
        out = []
        for i, s in enumerate(surfaces):
            good = canonical(slot, s) == want
            if prefer is not None:
                good = prefer(slot, s, want, good)
            out.append(0.0 if good else -3.0 - 0.01 * i)
        return out
    return scorer


class FakeModel:
    def __init__(self, slug, pins, **_):
        self.truth = {}
        for split in ("dev", "cal", "ho"):
            self.truth.update(A.truths(split))
        self.scorer = fake_scorer(self.truth)

    def weights_digest(self, recompute=False):
        return "w"

    def score_candidates_cached(self, msgs, surfaces):
        return self.scorer(msgs, surfaces)

    def score_candidates(self, msgs, surfaces):
        return self.scorer(msgs, surfaces)


class AnalysisTests(unittest.TestCase):
    def test_env_decisions_equal_round33_on_template_stores(self):
        from episodic_lab.env import generate_pair
        from episodic_lab.env_agent import decide, write_store
        for kind in ("hidden", "moved", "giver"):
            for i in range(6):
                p = generate_pair(f"t35-{i}", kind)
                for w in p["worlds"].values():
                    recs = write_store(None, w["experiences"]).records
                    self.assertEqual(A.decide_env(recs, w["decision"])["action"], decide(recs, w["decision"])["action"])

    def test_giver_with_unknown_fields(self):
        from episodic_lab.memory import EpisodeStore
        s = EpisodeStore()
        s.append("a", {"actor": "Ana Bell", "partner": "You", "action": "gave", "object": "red cup", "place": "Oak Mill", "event_day": 1})
        self.assertEqual(A.giver_of(s.records, "red cup").value, "Ana Bell")
        s.append("b", {"actor": "Cal Dorr", "partner": "You", "action": "gave", "object": None, "place": "Ash Mill", "event_day": 2},
                 extra={"unknown": ["object"]})
        self.assertEqual(A.giver_of(s.records, "red cup").status, "ambiguous")   # could be another gave of the cup

    def test_swap_carries_unknown_flags(self):
        rows = [({"place": None, "x": 1}, ["place"]), ({"place": "Oak Mill", "x": 2}, [])]
        out = A.variant({"op": "swap", "field": "place", "i": 0, "j": 1}, rows)
        self.assertEqual(out, [({"place": "Oak Mill", "x": 1}, []), ({"place": None, "x": 2}, ["place"])])

    def test_calibration_rule(self):
        truth = {f"t{i}": {"actor": "Ana Bell", "partner": None, "action": "hid", "object": "red cup",
                           "place": "Oak Mill", "event_day": 1} for i in range(400)}
        enc = {}
        for i, t in enumerate(truth):
            right = i % 50 != 0                       # 2% wrong, all with small margins
            m = 0.5 if not right else 1.0 + (i % 7)
            best, other = ("Ana Bell", "Cal Dorr") if right else ("Cal Dorr", "Ana Bell")
            enc[t] = {s: [["x", "v", 0.0]] for s in SLOTS}
            enc[t]["actor"] = [[best, best, 0.0], [other, other, -m]]
        cal = A.calibrate(enc, truth)["actor"]
        self.assertGreater(cal["tau"], 0.5)          # excludes the wrong small-margin answers
        self.assertGreaterEqual(cal["precision"], 0.99)
        self.assertGreaterEqual(cal["accepted"], 200)
        few = {t: enc[t] for t in list(enc)[:150]}
        self.assertIsNone(A.calibrate(few, truth)["actor"]["tau"])   # fewer than 200 accepted: no tau

    def test_perfect_and_adjective_dropping_encoders(self):
        truth = A.truths("dev")
        enc = {t: encode_text(fake_scorer(truth), t) for t in truth}
        taus = {s: 1.0 for s in SLOTS}
        q = A.quality(enc, truth, taus)
        c = A.cells(A.tasks("dev", enc, taus)["intact"])
        self.assertEqual(q["complete_records"], 1.0)
        self.assertTrue(all(ok for _, ok in A.encoder_qualified(q, c)))
        drop = fake_scorer(truth, lambda slot, s, want, good: (len(s.split()) == 1 and isinstance(want, str)
                                                               and want.endswith(" " + s)) if slot == "object" else good)
        enc2 = {t: encode_text(drop, t) for t in truth}
        q2 = A.quality(enc2, truth, taus)
        c2 = A.cells(A.tasks("dev", enc2, taus)["intact"])
        self.assertLess(q2["complete_records"], 0.95)
        self.assertFalse(all(ok for _, ok in A.encoder_qualified(q2, c2)))


class JobTests(unittest.TestCase):
    def run_job(self, d, phase, model, split="dev", chunk=0, chunks=1):
        out = d / f"r35_{phase}_{model}_{split}_{chunk}.json"
        argv = ["run_round35.py", "--phase", phase, "--model", model, "--split", split, "--chunk", str(chunk),
                "--chunks", str(chunks), "--pins", str(d / "pins.json"), "--request", str(d / "req.json"), "--out", str(out)]
        with mock.patch("sys.argv", argv), mock.patch("episodic_lab.models.PinnedModel", FakeModel):
            run_round35.main()
        return json.loads(out.read_text())

    def test_timing_and_encode_phases_with_the_collector(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "pins.json").write_text("{}")
            req = {"phase": "timing", "models": ["m"], "splits": ["dev"], "chunks": 1}
            (d / "req.json").write_text(json.dumps(req))
            r = self.run_job(d, "timing", "m")
            self.assertEqual(r["status"], "OK", r.get("traceback"))
            self.assertTrue(r["cache_check"]["ok"])
            collect_round35.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            self.assertEqual((d / "VERDICT").read_text().strip(), "COMPLETE", (d / "CHECK.txt").read_text())
            self.assertIn("seconds per text", (d / "SUMMARY.md").read_text())
            # encode phase for dev and cal in two chunks; then a missing chunk
            req = {"phase": "encode", "models": ["m"], "splits": ["dev", "cal"], "chunks": 2}
            (d / "req.json").write_text(json.dumps(req))
            for split in ("dev", "cal"):
                for chunk in (0, 1):
                    self.run_job(d, "encode", "m", split, chunk, 2)
            collect_round35.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            self.assertEqual((d / "VERDICT").read_text().strip(), "COMPLETE", (d / "CHECK.txt").read_text())
            dec = json.loads((d / "DECISIONS.json").read_text())["m"]
            self.assertEqual(set(dec["taus"]), set(SLOTS))
            (d / "r35_encode_m_cal_1.json").unlink()
            collect_round35.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            self.assertEqual((d / "VERDICT").read_text().strip(), "INCOMPLETE")
            self.assertIn("missing:r35_encode_m_cal_1.json", (d / "CHECK.txt").read_text())
            collect_round35.main(str(d / "req.json"), str(d), str(d / "pins.json"), "other-commit")
            self.assertIn("provenance:commit", (d / "CHECK.txt").read_text())
