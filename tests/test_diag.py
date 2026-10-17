"""Round 3.1 battery: gold answers re-derived by an independent solver; design properties
(matched note counts, both orders, unique short forms); runner and collector logic with a
fake model (no PyTorch)."""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench" / "diag"))

from episodic_lab.diagnostics import build_battery, summarise  # noqa: E402
import collect_diag  # noqa: E402
import run_diag  # noqa: E402

BATTERY = build_battery()
CASES = BATTERY["cases"]
NOTE = re.compile(r"(?:(You saw it yourself|\w+ \w+ told you): )?On day (\d+), (\w+ \w+) (\w+) the (\w+ \w+) at (\w+ \w+)\.")
BASE = {"repair": "repaired", "paint": "painted", "sell": "sold", "hide": "hid", "find": "found",
        "measure": "measured", "clean": "cleaned", "carry": "carried"}


def facts(case):
    out = []
    for note in case["notes"]:
        m = NOTE.fullmatch(note)
        assert m, note
        src, day, who, verb, obj, place = m.groups()
        source = None if src is None else ("self" if src == "You saw it yourself"
                                           else src[:-len(" told you")])
        out.append(dict(source=source, day=int(day), who=who, verb=verb, obj=obj, place=place))
    return out


def solve(case):
    """Independent solver: reads only the note texts and the question text."""
    f, q = facts(case), case["question"]
    if m := re.fullmatch(r"Where did (\w+ \w+) (\w+) the (\w+ \w+)\?", q):
        hits = [x for x in f if (x["who"], x["verb"], x["obj"]) == (m[1], BASE[m[2]], m[3])]
        return hits[0]["place"] if len(hits) == 1 else "none"
    if m := re.fullmatch(r"What did (\w+ \w+) (\w+) at (\w+ \w+)\?", q):
        hits = [x for x in f if (x["who"], x["verb"], x["place"]) == (m[1], BASE[m[2]], m[3])]
        return hits[0]["obj"] if len(hits) == 1 else "none"
    if m := re.fullmatch(r"Who (\w+) the (\w+ \w+) at (\w+ \w+)\?", q):
        hits = [x for x in f if (x["verb"], x["obj"], x["place"]) == (m[1], m[2], m[3])]
        return hits[0]["who"] if len(hits) == 1 else "none"
    if m := re.fullmatch(r"On which day did (\w+ \w+) (\w+) the (\w+ \w+) at (\w+ \w+)\?", q):
        hits = [x for x in f if (x["who"], x["verb"], x["obj"], x["place"]) == (m[1], BASE[m[2]], m[3], m[4])]
        return f"Day {hits[0]['day']}" if len(hits) == 1 else "none"
    if m := re.fullmatch(r"Which object was handled first, the (\w+ \w+) or the (\w+ \w+)\?", q):
        days = {x["obj"]: x["day"] for x in f}
        return min((m[1], m[2]), key=days.get)
    if m := re.fullmatch(r"Which happened first\? \(A\) (\w+ \w+) (\w+) the (\w+ \w+) at (\w+ \w+)\. "
                         r"\(B\) (\w+ \w+) (\w+) the (\w+ \w+) at (\w+ \w+)\. Answer A or B\.", q):
        def day(who, verb, obj, place):
            return next(x["day"] for x in f if (x["who"], x["verb"], x["obj"], x["place"]) == (who, verb, obj, place))
        return "A" if day(*m.groups()[:4]) < day(*m.groups()[4:]) else "B"
    if m := re.fullmatch(r"Where did the person who (\w+) the (\w+ \w+) (\w+) the (\w+ \w+)\?", q):
        people = {x["who"] for x in f if (x["verb"], x["obj"]) == (m[1], m[2])}
        hits = [x for x in f if x["who"] in people and (x["verb"], x["obj"]) == (BASE[m[3]], m[4])]
        return hits[0]["place"] if len(hits) == 1 else "none"
    if m := re.fullmatch(r"According to (what you saw yourself|\w+ \w+), where did (\w+ \w+) (\w+) the (\w+ \w+)\?", q):
        src = "self" if m[1] == "what you saw yourself" else m[1]
        hits = [x for x in f if x["source"] == src and (x["who"], x["verb"], x["obj"]) == (m[2], BASE[m[3]], m[4])]
        return hits[0]["place"] if len(hits) == 1 else "none"
    raise AssertionError(f"unsolved question: {q}")


class FakeModel:
    """Free channel: answers with the independent solver's answer or a fixed bias;
    candidate channel: gives the highest score to `prefer(case)`."""
    max_new_tokens = 16

    def __init__(self, answer=None):
        self.answer = answer or (lambda case: solve(case))
        self.by_question = {c["question"]: c for c in CASES}

    def _case(self, messages):
        return self.by_question[messages[1]["content"].split("\n\nQuestion: ")[1]]

    def generate(self, messages):
        return self.answer(self._case(messages))

    def generate_reasoning(self, messages, seed):
        return {"answer": self.answer(self._case(messages)), "new_tokens": 100, "finished": True}

    def score_candidates(self, messages, candidates):
        want = self.answer(self._case(messages))
        return [0.0 if c == want else -5.0 for c in candidates]


class BatteryTests(unittest.TestCase):
    def test_gold_equals_independent_solver(self):
        for case in CASES:
            self.assertEqual(solve(case), case["gold"], case["question"])

    def test_counts_and_balance(self):
        from collections import Counter
        c = Counter((x["skill"], x["kind"]) for x in CASES)
        self.assertEqual(c[("S3", "positive")], c[("S3", "lure")])
        self.assertEqual(c[("S5", "observed")], c[("S5", "reported")])
        self.assertEqual(c[("S5", "reported")], c[("S5", "missing")])
        self.assertEqual(c[("S2", "content")], c[("S2", "letter")])
        self.assertEqual(sum(x["skill"] == "S2" and x.get("aligned") for x in CASES),
                         sum(x["skill"] == "S2" and not x.get("aligned") for x in CASES))

    def test_note_count_never_signals_the_answer(self):
        for skill in ("S3", "S5"):
            counts = {(len(x["notes"]), x["gold"] == "none") for x in CASES if x["skill"] == skill}
            self.assertEqual({n for n, _ in counts}, {3 if skill == "S3" else 2})

    def test_lures_have_every_pair_but_no_full_match(self):
        for case in CASES:
            if case["skill"] != "S3":
                continue
            m = re.fullmatch(r"What did (\w+ \w+) (\w+) at (\w+ \w+)\?", case["question"])
            cue = (m[1], BASE[m[2]], m[3])
            rows = [(x["who"], x["verb"], x["place"]) for x in facts(case)]
            full = sum(r == cue for r in rows)
            self.assertEqual(full, 0 if case["kind"] == "lure" else 1)
            self.assertTrue(all(sum(a == b for a, b in zip(r, cue)) >= 2 for r in rows))

    def test_link_is_needed(self):
        for case in CASES:
            if case["skill"] == "S4":
                m = re.fullmatch(r"Where did the person who (\w+) the (\w+ \w+) (\w+) the (\w+ \w+)\?", case["question"])
                without_link = {x["place"] for x in facts(case) if (x["verb"], x["obj"]) == (BASE[m[3]], m[4])}
                self.assertEqual(len(without_link), 2)

    def test_s2_alignment_flag_matches_note_order(self):
        for c in CASES:
            if c["skill"] == "S2":
                d = [x["day"] for x in facts(c)]
                self.assertEqual(c["aligned"], d[0] < d[1])

    def test_s2_pairs_cover_both_orders(self):
        pairs = {}
        for c in CASES:
            if c["skill"] == "S2":
                pairs.setdefault((c["kind"], c["pair"]), []).append(c)
        for (kind, _), two in pairs.items():
            self.assertEqual(len(two), 2)
            if kind == "letter":
                self.assertEqual({t["gold"] for t in two}, {"A", "B"})
            else:
                self.assertEqual(two[0]["candidates"], two[1]["candidates"][::-1])

    def test_short_forms_unique_per_case(self):
        for c in CASES:
            names = [x for x in c["candidates"] if x not in ("none", "A", "B") and not x.startswith("Day")]
            for i in (0, -1):
                self.assertEqual(len({n.split()[i] for n in names}), len(names), c["candidates"])


class RunnerAndCollectorTests(unittest.TestCase):
    def rows(self, model):
        return [run_diag.run_case(model, c) for c in CASES]

    def test_perfect_model_scores_one_everywhere(self):
        s = summarise(self.rows(FakeModel()))
        for skill, entry in s.items():
            self.assertEqual((entry["free"], entry["cand"]), (1.0, 1.0), skill)
        self.assertEqual(s["S2"]["free_pairs"], {"content": 1.0, "letter": 1.0})

    def test_constant_letter_and_never_none(self):
        def biased(case):
            if case["answer_type"] == "choice":
                return "A"
            gold = solve(case)
            return gold if gold != "none" else next(x for x in case["candidates"] if x != "none")
        s = summarise(self.rows(FakeModel(biased)))
        self.assertEqual(s["S2"]["free_by_kind"]["letter"], 0.5)
        self.assertEqual(s["S2"]["free_pairs"]["letter"], 0.0)
        self.assertEqual(s["S3"]["free_by_kind"]["lure"], 0.0)
        self.assertEqual(s["S3"]["free_by_kind"]["positive"], 1.0)
        self.assertEqual(s["S5"]["cand_by_kind"]["missing"], 0.0)

    def test_day_answers_parse(self):
        case = next(c for c in CASES if c["answer_type"] == "day")
        for raw in (case["gold"], case["gold"].split()[1], f"On {case['gold'].lower()}"):
            row = run_diag.run_case(FakeModel(lambda c, r=raw: r if c is case else solve(c)), case)
            self.assertTrue(row["free"]["correct"], raw)

    def test_collector(self):
        def result(model_name, rows):
            return {"schema": run_diag.SCHEMA, "model": model_name, "status": "OK", "rows": rows,
                    "summary": summarise(rows)}
        rows = self.rows(FakeModel())
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            for m in ("a", "b"):
                (dest / f"diag_{m}.json").write_text(json.dumps(result(m, rows)))
            collect_diag.main(["a", "b"], str(dest))
            self.assertEqual((dest / "VERDICT").read_text().strip(), "COMPLETE")
            self.assertIn("| a | direct | S3 | 20 | 1.00 | 1.00 |", (dest / "SUMMARY.md").read_text())
            bad = result("b", rows)
            bad["summary"]["S1"]["free"] = 0.5
            (dest / "diag_b.json").write_text(json.dumps(bad))
            collect_diag.main(["a", "b"], str(dest))
            self.assertIn("FAILED diag_b.json summary_vs_rows", (dest / "CHECK.txt").read_text())
            bad = result("b", rows[1:])
            (dest / "diag_b.json").write_text(json.dumps(bad))
            collect_diag.main(["a", "b"], str(dest))
            self.assertIn("FAILED diag_b.json cases", (dest / "CHECK.txt").read_text())
            (dest / "diag_b.json").write_text(json.dumps(result("a", rows)))
            collect_diag.main(["a", "b"], str(dest))
            self.assertIn("FAILED diag_b.json identity", (dest / "CHECK.txt").read_text())
            self.assertEqual((dest / "VERDICT").read_text().strip(), "INCOMPLETE")


class ReasoningModeTests(unittest.TestCase):
    def test_cot_answer_extraction(self):
        self.assertEqual(run_diag.cot_answer("First... then.\nAnswer: Elm Court"), "Elm Court")
        self.assertEqual(run_diag.cot_answer("answer: a\nANSWER: B"), "B")
        self.assertEqual(run_diag.cot_answer("no final line"), "")

    def test_cot_and_think_rows(self):
        class CotModel(FakeModel):
            def generate(self, messages):
                question = messages[1]["content"].split("\n\nQuestion: ")[1]
                case = self.by_question[question]
                assert "Think step by step" in messages[0]["content"]
                return f"Let me look at the notes.\nAnswer: {solve(case)}"
        sub = [c for c in CASES if c["skill"] in ("S2", "S3")]
        for mode, model in (("cot", CotModel()), ("think", FakeModel())):
            rows = [run_diag.run_case(model, c, mode) for c in sub]
            self.assertTrue(all(r["free"]["correct"] for r in rows), mode)
            self.assertTrue(all("cand" not in r for r in rows))
            s = summarise(rows)
            self.assertEqual(set(s), {"S2", "S3"})
            self.assertNotIn("cand", s["S2"])

    def test_collector_accepts_partial_skill_sets_per_mode(self):
        sub = [c for c in CASES if c["skill"] in ("S2", "S3")]
        rows = [run_diag.run_case(FakeModel(), c, "think") for c in sub]
        data = {"schema": run_diag.SCHEMA, "model": "q", "mode": "think", "status": "OK",
                "rows": rows, "summary": summarise(rows)}
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "diag_q_think.json").write_text(json.dumps(data))
            collect_diag.main(["q:think:S2+S3"], str(dest))
            self.assertEqual((dest / "VERDICT").read_text().strip(), "COMPLETE", (dest / "CHECK.txt").read_text())
            self.assertIn("| q | think | S3 | 20 | 1.00 | - |", (dest / "SUMMARY.md").read_text())
            collect_diag.main(["q:think:S2+S3+S4"], str(dest))
            self.assertIn("FAILED diag_q_think.json cases", (dest / "CHECK.txt").read_text())
            collect_diag.main(["q:cot:S2+S3"], str(dest))
            self.assertIn("unreadable", (dest / "CHECK.txt").read_text())


if __name__ == "__main__":
    unittest.main()
