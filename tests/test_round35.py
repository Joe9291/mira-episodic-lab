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
        self.assertIsNone(canonical("object", "Oak Mill"))           # typed candidates (c2)
        self.assertIsNone(canonical("actor", "red cup"))
        self.assertIsNone(canonical("place", "you"))
        self.assertEqual(canonical("actor", "you"), SELF)
        self.assertEqual(canonical("partner", "I"), SELF)
        self.assertEqual(canonical("partner", "me"), SELF)
        self.assertEqual(canonical("object", "the red cup"), "red cup")
        self.assertIsNone(canonical("object", "the Red cup"))
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
import freeze35  # noqa: E402
import subprocess  # noqa: E402
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
        if text not in truth:          # the prompt without a note: no preference
            return [-1.0] * len(surfaces)
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

    def count_tokens(self, text):
        return len(text.split())


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
        # the job records GITHUB_SHA as its code commit; the tests' collector expects "local"
        with mock.patch("sys.argv", argv), mock.patch("episodic_lab.models.PinnedModel", FakeModel), \
                mock.patch.dict("os.environ", {"GITHUB_SHA": "local"}):
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

    def test_probe_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "pins.json").write_text("{}")
            (d / "req.json").write_text(json.dumps({"phase": "probe", "models": ["m"], "splits": ["dev"], "chunks": 1}))
            r = self.run_job(d, "probe", "m")
            self.assertEqual((r["status"], r["texts"]), ("OK", len(run_round35.probe_texts())))
            self.assertEqual(r["candidate_version"], "c2")
            collect_round35.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            self.assertEqual((d / "VERDICT").read_text().strip(), "COMPLETE", (d / "CHECK.txt").read_text())
            summary = (d / "SUMMARY.md").read_text()
            self.assertIn("scoring sum: complete records 1.000", summary)
            self.assertIn("scoring pmi", summary)
            self.assertTrue(all(len(x) == 5 and x[4] >= 2 for enc in r["encodings"].values() for x in enc["actor"]))

    def test_variant_with_few_shot_prompt(self):
        from episodic_lab.encoder35 import EXAMPLES, messages
        from episodic_lab.world import FIRST, LAST
        msgs = messages("actor", "Day 6: you walked to Oak Mill.", "p3")
        self.assertEqual(len(msgs), 1 + 2 * len(EXAMPLES) + 1)
        for note, answers in EXAMPLES:      # examples outside the world vocabulary
            self.assertFalse(any(n in note for n in list(FIRST) + list(LAST)))
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "pins.json").write_text("{}")
            (d / "req.json").write_text(json.dumps({"phase": "probe", "models": ["m+p3"], "splits": ["dev"], "chunks": 1}))
            r = self.run_job(d, "probe", "m+p3")
            self.assertEqual((r["status"], r["prompt_version"], r["model"]), ("OK", "p3", "m+p3"))

    def test_decoding_options(self):
        from episodic_lab.cands35 import STRUCTURAL
        from episodic_lab.encoder35 import decide_record
        enc = {s: [["x", "v", 0.0, None, 1]] for s in SLOTS}
        enc["actor"] = [["You", "You", 0.0, None, 1], ["Ana Bell", "Ana Bell", -2.0, None, 2]]
        enc["partner"] = [["You", "You", 0.0, None, 1], ["none", "none", -1.0, None, 1]]
        taus = {s: 0.0 for s in SLOTS}
        try:
            self.assertEqual(decide_record(enc, taus)[0]["partner"], "You")
            A.DECODING["receiver_differs_from_actor"] = True
            self.assertIsNone(decide_record(enc, taus)[0]["partner"])          # "none": absent
            self.assertEqual(decide_record(enc, taus)[1], [])
        finally:
            A.DECODING["receiver_differs_from_actor"] = False
        # a structurally fixed slot: single values accepted, a choice is unknown
        from episodic_lab.cands35 import decide
        self.assertEqual(decide([("3", 3, -0.1)], STRUCTURAL)[2], "single")
        self.assertEqual(decide([("3", 3, -0.1), ("4", 4, -2.0)], STRUCTURAL)[2], "unknown")
        def single_day(n, day_value=1):
            truth = {f"t{i}": {"actor": "Ana Bell", "partner": None, "action": "hid", "object": "red cup",
                               "place": "Oak Mill", "event_day": 1} for i in range(n)}
            enc = {t: {s: [["x", "v", 0.0, None, 1]] for s in SLOTS} for t in truth}
            for e in enc.values():
                e["event_day"] = [[str(day_value), day_value, -0.1, None, 1]] if day_value is not None else []
            return enc, truth
        try:
            A.DECODING["structural_slots"] = True
            cal = A.calibrate(*single_day(200))["event_day"]
            self.assertEqual((cal["tau"], cal["basis"], cal["singles"], cal["items"]), (STRUCTURAL, "single_only", 200, 0))
            self.assertIsNone(A.calibrate(*single_day(199))["event_day"]["tau"])           # too little evidence
            self.assertIsNone(A.calibrate(*single_day(200, 2))["event_day"]["tau"])        # single values wrong
            cal = A.calibrate(*single_day(200, None))["event_day"]                         # no evaluable case
            self.assertEqual((cal["tau"], cal["basis"], cal["singles"]), (None, "none", 0))
        finally:
            A.DECODING["structural_slots"] = False
        self.assertIsNone(A.calibrate(*single_day(200))["event_day"]["tau"])

    def test_calibration_uses_earlier_calibrated_thresholds(self):
        """Calibration runs in the decision order with the EARLIER slots decided by THEIR
        calibrated thresholds (same procedure as application). Here the action has no
        qualifying threshold ("was" ahead but always wrong) -> unknown -> the narrator
        constraint stays inactive -> the actor is a real choice (You vs Ada Stone). Deciding
        the action with threshold 0 instead would accept "was", exclude You and leave the
        actor a single value."""
        truth = {f"t{i}": {"actor": "You", "partner": None, "action": "went", "object": None,
                           "place": "Oak Mill", "event_day": 1} for i in range(200)}
        enc = {}
        for t in truth:
            e = {s: [["x", "v", 0.0, None, 1]] for s in SLOTS}
            e["action"] = [["was", "was", 0.0, None, 1], ["went", "went", -1.0, None, 1]]
            e["actor"] = [["You", "You", 0.0, None, 1], ["Ada Stone", "Ada Stone", -1.0, None, 1]]
            e["partner"] = [["none", "none", 0.0, None, 1]]
            enc[t] = e
        try:
            A.DECODING.update(joint_roles=True, structural_slots=True)
            cal = A.calibrate(enc, truth)
            self.assertIsNone(cal["action"]["tau"])
            self.assertEqual((cal["actor"]["basis"], cal["actor"]["items"], cal["actor"]["singles"], cal["actor"]["tau"]),
                             ("multi", 200, 0, 0.0))
        finally:
            A.DECODING.update(A.DECODING_OFF)

    def test_decoder_d3_schema_rules(self):
        """Round 3.5b: F1 object values adjective + noun (or none); F2 an accepted "gave" has
        the receiver You, inside the feasible role pairs; an unknown action keeps every receiver."""
        from episodic_lab.encoder35 import decide_record
        def enc(actor, partner, action, obj):
            e = {s: [["x", "v", 0.0, None, 1]] for s in SLOTS}
            for slot, vals in (("actor", actor), ("partner", partner), ("action", action), ("object", obj)):
                e[slot] = [[k, k, v, None, 1] for k, v in vals.items()]
            return e
        taus = {s: 0.0 for s in SLOTS}
        e = enc({"Ada Stone": 0.0, "You": -3.0}, {"none": 0.0, "You": -0.5}, {"gave": 0.0, "was": -4.0},
                {"ledger": 0.0, "heavy ledger": -0.2, "none": -5.0, "the heavy ledger": -9.0})
        try:
            A.DECODING.update(joint_roles=True, structural_slots=True)
            r, unk, det = decide_record(e, taus)                      # d2: the errors of the holdout
            self.assertEqual((r["object"], r["partner"]), ("ledger", None))
            A.DECODING.update(object_two_tokens=True, gave_receiver_self=True)
            r, unk, det = decide_record(e, taus)                      # d3
            self.assertEqual((r["object"], r["partner"], r["actor"]), ("heavy ledger", "You", "Ada Stone"))
            self.assertEqual((det["partner"]["status"], det["partner"]["origin"]), ("single", "schema"))
            r, unk, det = decide_record(dict(e, object=[["none", "none", 0.0, None, 1], ["ledger", "ledger", 1.0, None, 1]]), taus)
            self.assertIsNone(r["object"])                            # "none" stays, a bare noun never wins
            self.assertEqual((det["object"]["value"], det["object"]["status"]), ("none", "single"))
            r, unk, det = decide_record(dict(e, object=[["heavy ledger there", "heavy ledger there", 0.0, None, 1],
                                                        ["heavy ledger", "heavy ledger", -0.5, None, 1]]), taus)
            self.assertEqual(r["object"], "heavy ledger")             # exactly two tokens, not three
            # unknown action ("gave" and "put" tie): F2 inactive, the receiver stays open
            r, unk, det = decide_record(dict(e, action=[["gave", "gave", 0.0, None, 1], ["put", "put", 0.0, None, 1]]), taus)
            self.assertEqual((det["action"]["status"], r["partner"], det["partner"]["status"]), ("unknown", None, "ok"))
            # F2 inside the feasible pairs: actor You and receiver You can never both hold;
            # with "gave" accepted and the actor "You" far ahead, the pair (You, You) is excluded
            r, unk, det = decide_record(enc({"You": 0.0, "Ada Stone": -2.0}, {"You": 0.0, "none": -0.1},
                                            {"gave": 0.0, "was": -4.0}, {"heavy ledger": 0.0}), taus)
            self.assertEqual((r["actor"], r["partner"]), ("Ada Stone", "You"))
        finally:
            A.DECODING.update(A.DECODING_OFF)

    def test_joint_role_decoding(self):
        from episodic_lab.encoder35 import decide_record
        def enc(actor, partner, action):
            e = {s: [["x", "v", 0.0, None, 1]] for s in SLOTS}
            e["actor"] = [[k, k, v, None, 1] for k, v in actor.items()]
            e["partner"] = [[k, k, v, None, 1] for k, v in partner.items()]
            e["action"] = [[k, k, v, None, 1] for k, v in action.items()]
            return e
        taus = {s: 0.0 for s in SLOTS}
        try:
            A.DECODING["joint_roles"] = True
            # "You got the key from Juno": actor You slightly ahead, receiver You far ahead -> (Juno, You)
            r = decide_record(enc({"You": -0.5, "Juno Brack": -1.0}, {"You": -0.2, "none": -3.0}, {"gave": 0.0, "was": -4.0}), taus)[0]
            self.assertEqual((r["actor"], r["partner"]), ("Juno Brack", "You"))
            # "You met Dorran": a person seen is never the narrator
            r = decide_record(enc({"You": -0.1, "Dorran Vesk": -2.0}, {"none": -0.1, "You": -1.0}, {"was": 0.0, "went": -3.0}), taus)[0]
            self.assertEqual((r["actor"], r["partner"]), ("Dorran Vesk", None))
            # own placing: actor You, receiver must differ -> none
            r = decide_record(enc({"You": -0.1, "Ana Bell": -3.0}, {"You": -0.1, "none": -0.5}, {"put": 0.0, "was": -4.0}), taus)[0]
            self.assertEqual((r["actor"], r["partner"]), ("You", None))
            # regression (review B1, first point): "was" and "went" tie -> the action is unknown and
            # its narrator constraint must not apply: actor You stays possible and wins
            r, unk, det = decide_record(enc({"You": -0.1, "Dorran Vesk": -2.0}, {"none": -0.1, "You": -3.0},
                                            {"was": 0.0, "went": 0.0}), taus)
            self.assertEqual(det["action"]["status"], "unknown")
            self.assertEqual((r["actor"], r["partner"]), ("You", None))
            # ... and a "was" below its threshold is not accepted either: same outcome
            r, unk, det = decide_record(enc({"You": -0.1, "Dorran Vesk": -2.0}, {"none": -0.1, "You": -3.0},
                                            {"was": 0.0, "went": -0.5}), dict(taus, action=1.0))
            self.assertEqual((det["action"]["status"], r["actor"]), ("unknown", "You"))
            # while an accepted "was" excludes the narrator (the actor becomes a single value from the schema)
            r, unk, det = decide_record(enc({"You": -0.1, "Dorran Vesk": -2.0}, {"none": -0.1, "You": -3.0},
                                            {"was": 0.0, "went": -0.5}), taus)
            self.assertEqual((r["actor"], det["actor"]["status"], det["actor"]["origin"]), ("Dorran Vesk", "single", "schema"))
            self.assertEqual((det["object"]["status"], det["object"]["origin"]), ("single", "text"))
            # regression (review B1, second point): two equally good feasible pairs (You, none) and
            # (Ada Stone, You) with different components -> both components unknown
            r, unk, det = decide_record(enc({"You": -1.0, "Ada Stone": -1.0}, {"none": -1.0, "You": -1.0},
                                            {"gave": 0.0, "was": -4.0}), taus)
            self.assertEqual(sorted(x for x in unk if x in ("actor", "partner")), ["actor", "partner"])
            self.assertEqual((det["actor"]["margin"], det["partner"]["margin"]), (0.0, 0.0))
            # tied pairs that share the actor: the actor stays decided, only the receiver is unknown
            r, unk, det = decide_record(enc({"You": -0.1, "Ada Stone": -3.0}, {"Tom Reed": -1.0, "Ben Cole": -1.0},
                                            {"gave": 0.0, "was": -4.0}), taus)
            self.assertEqual((r["actor"], "partner" in unk, "actor" in unk), ("You", True, False))
            # the pair-level margin, not the margin after filtering by the chosen counterpart:
            # pairs (You, Ada) 0.0 and (Ada, You) -0.15; d1 filtered the competitor away and
            # accepted both slots as single values, d2 keeps margin 0.15 (unknown at tau 0.2)
            e = enc({"You": 0.0, "Ada Stone": -0.1}, {"Ada Stone": 0.0, "You": -0.05}, {"gave": 0.0, "was": -4.0})
            r, unk, det = decide_record(e, taus)
            self.assertAlmostEqual(det["actor"]["margin"], 0.15)
            self.assertAlmostEqual(det["partner"]["margin"], 0.15)
            self.assertEqual((r["actor"], r["partner"]), ("You", "Ada Stone"))
            r, unk, det = decide_record(e, dict(taus, actor=0.2, partner=0.2))
            self.assertEqual(sorted(x for x in unk if x in ("actor", "partner")), ["actor", "partner"])
        finally:
            A.DECODING["joint_roles"] = False

    def test_freeze_binding_covers_the_import_closure(self):
        """Every local module the jobs and the collector import is hash-bound by a freeze."""
        code = ("import os, sys; sys.path[:0] = ['.', 'bench/m3']; import collect_round35, run_round35, "
                "episodic_lab.models; r = os.path.abspath('.'); print('\\n'.join(sorted(os.path.relpath(m.__file__, r) "
                "for m in list(sys.modules.values()) if getattr(m, '__file__', None) and "
                "os.path.abspath(m.__file__).startswith(r))))")
        root = Path(__file__).resolve().parents[1]
        out = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, check=True).stdout
        self.assertEqual(set(out.split()) - set(freeze35.FROZEN_CODE), set())
        self.assertEqual(freeze35.check(None), [])
        cfg = json.loads((root / "config" / "round35b_reserve_proposal.json").read_text())   # the active freeze
        self.assertEqual(freeze35.check(cfg["frozen"]), [], "the proposed freeze must match the code")

    def test_reserve_qualification_phase(self):
        """Round 3.5b: the reserve is a qualification split with comparisons, class
        diagnostics and error consequences."""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "pins.json").write_text("{}")
            req = {"phase": "encode", "models": ["m"], "splits": ["res"], "chunks": 2,
                   "decoding": {"joint_roles": True, "structural_slots": True, "object_two_tokens": True,
                                "gave_receiver_self": True},
                   "frozen": {"model": "m", "decoder_version": freeze35.decoder_version(),
                              "code_sha256": freeze35.code_hashes(), "taus": {s: 1.0 for s in SLOTS}}}
            (d / "req.json").write_text(json.dumps(req))
            for chunk in range(2):
                self.run_job(d, "encode", "m", "res", chunk, 2)
            collect_round35.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            self.assertEqual((d / "VERDICT").read_text().strip(), "COMPLETE", (d / "CHECK.txt").read_text())
            dec = json.loads((d / "DECISIONS.json").read_text())["m"]
            self.assertIn(dec["ENCODER_QUALIFIED"], ("YES", "NO"))
            self.assertIn("consequences", dec)
            summary = (d / "SUMMARY.md").read_text()
            for part in ("Comparison decodings", "- d2 (no schema rules F1/F2):", "- F1 only:", "- F2 only:",
                         "Class diagnostics", "adjective:heavy", "Original round 3.3 / 3.4 milestone rules on the LM system (res)"):
                self.assertIn(part, summary)
            self.assertEqual(A.DECODING["object_two_tokens"], True)   # comparisons restore the frozen decoding
            (d / "r35_encode_m_res_1.json").unlink()
            collect_round35.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            dec = json.loads((d / "DECISIONS.json").read_text())["m"]
            self.assertEqual((dec["ENCODER_QUALIFIED"], dec["MILESTONE_ORIGINAL_RULES"]), ("UNDECIDABLE", "FAIL"))
        A.DECODING.update(A.DECODING_OFF)

    def test_holdout_phase_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "pins.json").write_text("{}")
            req = {"phase": "encode", "models": ["m"], "splits": ["ho"], "chunks": 3,
                   "frozen": {"model": "m", "decoder_version": freeze35.decoder_version(), "code_sha256": freeze35.code_hashes(),
                              "taus": {s: 1.0 for s in SLOTS}}}
            (d / "req.json").write_text(json.dumps(req))
            for chunk in range(3):
                self.run_job(d, "encode", "m", "ho", chunk, 3)
            collect_round35.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            self.assertEqual((d / "VERDICT").read_text().strip(), "COMPLETE", (d / "CHECK.txt").read_text())
            dec = json.loads((d / "DECISIONS.json").read_text())["m"]
            self.assertEqual((dec["ENCODER_QUALIFIED"], dec["MILESTONE_ORIGINAL_RULES"]), ("YES", "PASS"))
            # the frozen decoder version and code hashes must match the running code
            with mock.patch.object(freeze35, "decoder_version", lambda root=None: "d9"), \
                    mock.patch.object(freeze35, "code_hashes", lambda root=None: {p: "0" for p in freeze35.FROZEN_CODE}):
                collect_round35.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
                # ... and every encode job stops before loading a model
                r = self.run_job(d, "encode", "m", "ho", 0, 3)
                self.assertEqual(r["status"], "ERROR")
                self.assertIn("frozen configuration does not match the code", r["error"])
                self.assertNotIn("encodings", r)
            self.run_job(d, "encode", "m", "ho", 0, 3)   # restore the valid chunk report
            check = (d / "CHECK.txt").read_text()
            self.assertIn(f"FAILED decoder_version:{freeze35.decoder_version()}:d9", check)
            self.assertIn("FAILED code_sha256:episodic_lab/__init__.py,episodic_lab/wordings35.py", check)
            self.assertEqual(json.loads((d / "DECISIONS.json").read_text())["m"]["ENCODER_QUALIFIED"], "UNDECIDABLE")
            (d / "r35_encode_m_ho_2.json").unlink()
            collect_round35.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            dec = json.loads((d / "DECISIONS.json").read_text())["m"]
            self.assertEqual((dec["ENCODER_QUALIFIED"], dec["MILESTONE_ORIGINAL_RULES"]), ("UNDECIDABLE", "FAIL"))
