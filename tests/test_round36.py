"""Round 3.6: question wordings, worlds, parser decision table q1, calibration, baseline,
analysis, jobs and collector (docs/ROUND_3_6.md, design v3)."""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench" / "m3"))

from episodic_lab import analysis36 as A  # noqa: E402
from episodic_lab import env36  # noqa: E402
from episodic_lab.baseline36 import parse_baseline, provenance  # noqa: E402
from episodic_lab.env36 import ORDER, check_conditions, split_pairs, split_questions  # noqa: E402
from episodic_lab.parser36 import (NONE, admissible, calibrate, decide_question, target_candidates)  # noqa: E402
from episodic_lab.questions36 import (AMBIGUOUS, INTENTS, SETS, TYPES, UNSUPPORTED_FAMILIES, is_constant,  # noqa: E402
                                      parse, render, wordings)


def enc(intent: dict, target: dict) -> dict:
    """A recorded encoding with given scores (missing intent labels get -9)."""
    return {"intent": [[k, k, intent.get(k, -9.0), None, 1] for k in INTENTS],
            "target": [[k, k, v, None, 1] for k, v in target.items()]}


class WordingTests(unittest.TestCase):
    def test_roundtrip_and_families_in_every_group(self):
        fills = {"o": "red cup", "x": "Ana Bell", "noun": "cup", "first": "Ana", "p": "Oak Mill"}
        for fam in list(TYPES) + list(AMBIGUOUS) + list(UNSUPPORTED_FAMILIES):
            for group in ("dev", "holdout", "reserve"):
                ws = wordings(fam, group)
                self.assertTrue(ws, (fam, group))   # every family has a wording in every group
                for w in ws:
                    self.assertEqual(parse(render(w, fills), w), {k: fills[k] for k in re.findall(r"\{(\w+)\}", w)})

    def test_splits_texts_gold_and_constants(self):
        seen = {}
        for split in ORDER:
            q = split_questions(split, new_only=False)          # raises on inconsistent gold
            seen[split] = set(q)
            for p in split_pairs(split):
                for x in p["questions"]:
                    fam, group, idx = x["wording"].split(":")
                    self.assertIn(group, SETS[env36.GROUP[split]])
                    if is_constant(wordings(fam, group)[int(idx)]):
                        self.assertIn(split, env36.FIRST_OF_GROUP)
                    w = wordings(fam, group)[int(idx)]
                    self.assertIsNotNone(parse(x["text"], w))
        for a in ("dev", "cal", "aud"):
            for b in ("ho", "res"):
                self.assertFalse(seen[a] & seen[b])
        self.assertFalse(seen["ho"] & seen["res"])
        # first-occurrence counting: a text counts only in its first split
        for i, s in enumerate(ORDER):
            for e in ORDER[:i]:
                self.assertFalse(set(split_questions(s)) & set(split_questions(e)))

    def test_pairs_share_questions_and_conditions_per_kind(self):
        for split in ("dev", "cal"):
            for p in split_pairs(split):
                self.assertEqual(check_conditions(p), [])
                self.assertEqual(len(p["questions"]), len(env36.goals(p)) + 3)
        giver = [p for p in split_pairs("dev") if p["kind"] == "giver"][0]
        self.assertEqual(check_conditions(giver), [])            # a giver world passes its own audit
        broken = json.loads(json.dumps(giver))
        broken["worlds"]["A"]["truth_content"].append(dict(broken["worlds"]["A"]["truth_content"][0],
                                                           action="gave", object=giver["object"], partner="You"))
        self.assertTrue(check_conditions(broken))

    def test_calibration_counts_and_coverage(self):
        gold = split_questions("cal")
        tc = [t for t, g in gold.items() if g["outcome"] in ("OK", "CLARIFY")
              and sum(1 for _, c in target_candidates(t) if c != NONE and admissible(g["intent"], c)) >= 1]
        self.assertGreaterEqual(len(tc), 300)
        self.assertGreaterEqual(len(gold), 300)
        for split in ("dev", "cal", "aud"):
            for t, g in split_questions(split).items():
                if g["outcome"] != "REFUSE":
                    self.assertIn(g["target"], {c for _, c in target_candidates(t)}, t)


class DecisionTableTests(unittest.TestCase):
    T = {"intent": 0.0, "target": 0.0}

    def test_outcomes(self):
        d = decide_question(enc({"object_current": 0.0, "giver": 0.0}, {"red cup": 0.0, NONE: -1.0}), self.T)
        self.assertEqual((d["outcome"], d["reason"]), ("CLARIFY", "low_confidence"))       # intent tie
        d = decide_question(enc({"unsupported": 0.0}, {NONE: 0.0}), self.T)
        self.assertEqual(d["outcome"], "REFUSE")                                          # no target needed
        d = decide_question(enc({"object_current": 0.0}, {"cup": 0.0, NONE: -1.0}), self.T)
        self.assertEqual((d["outcome"], d["reason"]), ("CLARIFY", "no_referent"))          # no admissible value
        d = decide_question(enc({"object_current": 0.0}, {"red cup": -2.0, NONE: 0.0}), self.T)
        self.assertEqual((d["outcome"], d["reason"]), ("CLARIFY", "no_referent"))          # none accepted
        d = decide_question(enc({"object_current": 0.0}, {"red cup": 0.0, "old map": 0.0, NONE: -3.0}), self.T)
        self.assertEqual((d["outcome"], d["reason"]), ("CLARIFY", "low_confidence"))       # target tie
        d = decide_question(enc({"object_current": 0.0}, {"red cup": 0.0, "Ana Bell": 1.0, NONE: -3.0}), self.T)
        self.assertEqual((d["outcome"], d["intent"], d["target"]), ("OK", "object_current", "red cup"))
        d = decide_question(enc({"person_first": 0.0}, {"red cup": 1.0, "Ana Bell": 0.0, NONE: -3.0}), self.T)
        self.assertEqual((d["outcome"], d["target"]), ("OK", "Ana Bell"))                 # typed admissibility
        d = decide_question(enc({"giver": 0.0}, {"Ana Bell": 1.0, "red cup": 0.0, NONE: -3.0}), self.T)
        self.assertEqual((d["outcome"], d["target"]), ("OK", "red cup"))                  # giver needs an object

    def test_missing_thresholds(self):
        no_target = {"intent": 0.0, "target": None}
        self.assertEqual(decide_question(enc({"unsupported": 0.0}, {NONE: 0.0}), no_target)["outcome"], "REFUSE")
        d = decide_question(enc({"object_current": 0.0}, {"cup": 0.0, NONE: -1.0}), no_target)
        self.assertEqual((d["outcome"], d["reason"]), ("CLARIFY", "no_referent"))
        d = decide_question(enc({"object_current": 0.0}, {"red cup": 0.0, NONE: -5.0}), no_target)
        self.assertEqual((d["outcome"], d["reason"]), ("CLARIFY", "low_confidence"))
        for e in (enc({"unsupported": 0.0}, {NONE: 0.0}), enc({"object_current": 0.0}, {"red cup": 0.0, NONE: -5.0})):
            d = decide_question(e, {"intent": None, "target": 0.0})
            self.assertEqual((d["outcome"], d["reason"]), ("CLARIFY", "low_confidence"))

    def test_threshold_boundaries(self):
        e = enc({"object_current": 0.0, "giver": -0.5}, {"red cup": 0.0, NONE: -1.0})
        self.assertEqual(decide_question(e, {"intent": 0.5, "target": 0.0})["outcome"], "OK")       # margin == tau
        self.assertEqual(decide_question(e, {"intent": 0.5000001, "target": 0.0})["reason"], "low_confidence")
        e2 = enc({"object_current": 0.0, "giver": 0.0}, {"red cup": 0.0, NONE: -1.0})
        self.assertEqual(decide_question(e2, {"intent": 0.0, "target": 0.0})["reason"], "low_confidence")  # tie at 0

    def test_calibration_contract(self):
        gold, encs = {}, {}
        for i in range(250):   # supported, right
            t = f"Find the red cup {i}."
            gold[t] = {"intent": "object_current", "target": "red cup", "outcome": "OK"}
            encs[t] = enc({"object_current": 0.0}, {"red cup": 0.0, NONE: -2.0})
        for i in range(30):    # gold-unsupported accepted as supported: an intent error, never a target item
            t = f"Why is the red cup {i}?"
            gold[t] = {"intent": "unsupported", "target": None, "outcome": "REFUSE"}
            encs[t] = enc({"object_current": 0.0, "unsupported": -0.1}, {"red cup": 0.0, NONE: -2.0})
        cal = calibrate(encs, gold)
        self.assertEqual(cal["flow"]["target_calibratable"], 250)
        self.assertEqual(cal["target"]["items"], 250)
        self.assertEqual(cal["intent"]["items"], 280)
        self.assertGreater(cal["intent"]["tau"], 0.1 - 1e-9)       # the 30 errors at margin 0.1 must be excluded
        # calibration and application agree at the chosen thresholds
        taus = {"intent": cal["intent"]["tau"], "target": cal["target"]["tau"]}
        self.assertEqual(decide_question(encs["Why is the red cup 0?"], taus)["outcome"], "CLARIFY")
        self.assertEqual(decide_question(encs["Find the red cup 0."], taus)["outcome"], "OK")


class BaselineTests(unittest.TestCase):
    def test_provenance_and_rules(self):
        self.assertEqual(provenance(), [])
        r = parse_baseline("Go to the place the red cup was in before it was last put somewhere.")
        self.assertEqual((r["outcome"], r["intent"], r["target"]), ("OK", "object_previous", "red cup"))
        r = parse_baseline("Where was Ana Bell the time before you last saw them?")
        self.assertEqual((r["intent"], r["target"]), ("person_previous", "Ana Bell"))
        self.assertEqual(parse_baseline("Where was Ana Bell right before they gave you the red cup?")["outcome"], "REFUSE")
        r = parse_baseline("Who gave you the red cup? Go to them.")
        self.assertEqual((r["intent"], r["target"]), ("giver", "red cup"))
        self.assertEqual(parse_baseline("Who put the red cup at Oak Mill?")["outcome"], "REFUSE")
        self.assertEqual(parse_baseline("Find the cup.")["outcome"], "CLARIFY")
        self.assertEqual(parse_baseline("Go to Ana.")["outcome"], "CLARIFY")

    def test_baseline_dev_group_complete(self):
        for split in ("dev", "cal"):
            g = split_questions(split)
            self.assertEqual(sum(A.right(parse_baseline(t), x) for t, x in g.items()), len(g))


class AnalysisTests(unittest.TestCase):
    def test_gold_parses_pass_everything(self):
        import collect_round33
        import collect_round34
        import run_round33
        import run_round34
        from episodic_lab.analysis35 import cells
        texts = {q["text"]: q["gold"] for p in split_pairs("dev") for q in p["questions"]}
        po = {t: A.gold_parse(g) for t, g in texts.items()}
        T = A.tasks("dev", po)
        self.assertTrue(all(ok for _, ok in A.task_criteria(cells(T["intact"]))))
        orig = (collect_round33.criteria(run_round33.summarise(T["rows33"]), env36.SIZES["dev"])
                + collect_round34.criteria(run_round34.summarise(T["rows34"]), env36.SIZES["dev"]))
        self.assertTrue(all(ok for _, ok in orig))
        ctl = A.control_outcomes("dev", po)
        self.assertEqual(set(ctl["absent"]), {"explore"})
        self.assertEqual(set(ctl["ambiguous"]), {"clarify"})
        self.assertEqual(set(ctl["unsupported"]), {"refuse"})
        g = split_questions("dev")
        self.assertTrue(all(ok for _, ok in A.parser_criteria(A.parser_metrics({t: po[t] for t in g}, g))))

    def test_wrong_parse_counts(self):
        g = split_questions("dev")
        po = {t: A.gold_parse(x) for t, x in g.items()}
        amb = next(t for t, x in g.items() if x["outcome"] == "CLARIFY")
        po[amb] = {"outcome": "OK", "intent": "object_current", "target": "red cup", "reason": None}
        m = A.parser_metrics(po, g)
        self.assertEqual(m["false_ok:CLARIFY"][0], 1)
        self.assertEqual(m["wrong_accepted"][0], 1)
        self.assertEqual(m["wrong_accepted"][1], sum(1 for x in g.values() if x["outcome"] == "OK") + 1)


GOLD = {}
for _s in ORDER:
    GOLD.update(split_questions(_s, new_only=False))


class FakeModel:
    """Scores the gold answer 0 and everything else -5 (target 'none' for controls)."""
    def __init__(self, slug, pins, **_):
        pass

    def weights_digest(self, recompute=False):
        return "w"

    def _score(self, msgs, surfaces):
        last = msgs[-1]["content"]
        text = re.match(r"Request: (.*)\n\nQuestion: Field '(\w+)'", last, re.S)
        req, field = text.group(1), text.group(2)
        g = GOLD[req]
        want = g["intent"] if field == "intent" else (g["target"] if g["outcome"] == "OK" else NONE)
        canon = (lambda s: " ".join(w[:-2] if w.endswith("'s") else w for w in s.split()))
        return [0.0 if canon(s) == want else -5.0 for s in surfaces]

    score_candidates_cached = _score
    score_candidates = _score

    def count_tokens(self, text):
        return len(text.split())


class JobTests(unittest.TestCase):
    def run_job(self, d, phase, model, split="dev", chunk=0, chunks=1):
        import run_round36
        out = d / f"r36_{phase}_{model}_{split}_{chunk}.json"
        argv = ["run_round36.py", "--phase", phase, "--model", model, "--split", split, "--chunk", str(chunk),
                "--chunks", str(chunks), "--pins", str(d / "pins.json"), "--request", str(d / "req.json"), "--out", str(out)]
        with mock.patch("sys.argv", argv), mock.patch("episodic_lab.models.PinnedModel", FakeModel), \
                mock.patch.dict("os.environ", {"GITHUB_SHA": "local"}):
            run_round36.main()
        return json.loads(out.read_text())

    def test_probe_and_dev_cal(self):
        import collect_round36
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "pins.json").write_text("{}")
            (d / "req.json").write_text(json.dumps({"phase": "probe", "models": ["m+q1"], "splits": ["dev"], "chunks": 1}))
            r = self.run_job(d, "probe", "m+q1")
            self.assertEqual((r["status"], r["prompt_version"]), ("OK", "q1"), r.get("error"))
            collect_round36.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            self.assertEqual((d / "VERDICT").read_text().strip(), "COMPLETE", (d / "CHECK.txt").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "pins.json").write_text("{}")
            req = {"phase": "encode", "models": ["m"], "splits": ["dev", "cal"], "chunks": 2}
            (d / "req.json").write_text(json.dumps(req))
            for split in ("dev", "cal"):
                for c in range(2):
                    self.run_job(d, "encode", "m", split, c, 2)
            collect_round36.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            self.assertEqual((d / "VERDICT").read_text().strip(), "COMPLETE", (d / "CHECK.txt").read_text())
            dec = json.loads((d / "DECISIONS.json").read_text())["m"]
            self.assertTrue(all(dec["criteria"].values()), dec["criteria"])
            self.assertIsNotNone(dec["taus"]["intent"])
            self.assertIn("Paired with the baseline", (d / "SUMMARY.md").read_text())

    def test_qualification_phase(self):
        import collect_round36
        import freeze36
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "pins.json").write_text("{}")
            req = {"phase": "encode", "models": ["m"], "splits": ["ho"], "chunks": 2,
                   "frozen": {"model": "m", "decoder_version": freeze36.decoder_version(),
                              "code_sha256": freeze36.code_hashes(), "taus": {"intent": 1.0, "target": 1.0}}}
            (d / "req.json").write_text(json.dumps(req))
            for c in range(2):
                self.run_job(d, "encode", "m", "ho", c, 2)
            collect_round36.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            self.assertEqual((d / "VERDICT").read_text().strip(), "COMPLETE", (d / "CHECK.txt").read_text())
            dec = json.loads((d / "DECISIONS.json").read_text())["m"]
            self.assertEqual((dec["PARSER_QUALIFIED"], dec["PARSER_MILESTONE_ORIGINAL_RULES"]), ("YES", "PASS"))
            with mock.patch.object(freeze36, "decoder_version", lambda root=None: "q9"):
                collect_round36.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
                r = self.run_job(d, "encode", "m", "ho", 0, 2)
                self.assertEqual(r["status"], "ERROR")
            self.assertIn("FAILED decoder_version", (d / "CHECK.txt").read_text())
            self.assertEqual(json.loads((d / "DECISIONS.json").read_text())["m"]["PARSER_QUALIFIED"], "UNDECIDABLE")
            self.run_job(d, "encode", "m", "ho", 0, 2)
            (d / "r36_encode_m_ho_1.json").unlink()
            collect_round36.main(str(d / "req.json"), str(d), str(d / "pins.json"), "local")
            dec = json.loads((d / "DECISIONS.json").read_text())["m"]
            self.assertEqual((dec["PARSER_QUALIFIED"], dec["PARSER_MILESTONE_ORIGINAL_RULES"]), ("UNDECIDABLE", "FAIL"))

    def test_freeze_binding_covers_the_import_closure(self):
        import subprocess
        import freeze36
        code = ("import os, sys; sys.path[:0] = ['.', 'bench/m3']; import collect_round36, run_round36, "
                "episodic_lab.models; r = os.path.abspath('.'); print('\\n'.join(sorted(os.path.relpath(m.__file__, r) "
                "for m in list(sys.modules.values()) if getattr(m, '__file__', None) and "
                "os.path.abspath(m.__file__).startswith(r))))")
        out = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        self.assertEqual(set(out.split()) - set(freeze36.FROZEN_CODE), set())


if __name__ == "__main__":
    unittest.main()
