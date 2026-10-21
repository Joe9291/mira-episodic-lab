"""Round 4.0 phase A: memory M, reference R, generator, audit, interventions, baselines."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from episodic_lab import r40_analysis as A
from episodic_lab import r40_baselines as B
from episodic_lab import r40_world as W
from episodic_lab.r40_memory import Memory, ReportStore, StoreCorrupted
from episodic_lab.r40_reference import reference_answers
from episodic_lab.r40_schema import ReportError, check_report
from episodic_lab.rng import HashRng

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("report_id", "report_day", "source", "rank", "subject", "attribute", "kind", "value",
          "valid_from", "target_report_id")


def rep(row, origin=None):
    r = dict(zip(FIELDS, row))
    r["origin"] = origin or "o-" + row[0]
    return r


def conformance_worlds():
    d = json.loads((ROOT / "tests/fixtures/r40_conformance.json").read_text())
    for name, w in d["worlds"].items():
        reps = sorted((rep(row) for row in w["reports"]), key=lambda r: (r["report_day"], r["report_id"]))
        yield name, reps, w


class Conformance(unittest.TestCase):
    def test_hand_checked_cases_m_and_r(self):
        n = 0
        for name, reps, w in conformance_worlds():
            by_id = {r["report_id"]: r for r in reps}
            m = Memory(reps)
            qs = [dict(c[1], qid=c[0], subject="key", attribute="loc") for c in w["checks"]]
            gold = reference_answers(reps, qs)[0]          # R on the FULL world (later reports exist)
            for c, q in zip(w["checks"], qs):
                with self.subTest(case=c[0]):
                    self.assertEqual(m.answer(q), c[2])
                    self.assertEqual(gold[c[0]], c[2])
                    if len(c) > 3:
                        prov = [[i, by_id[i]["source"], by_id[i]["rank"]] for i in m.answer(q)["ids"]]
                        self.assertEqual(prov, c[3])
                n += 1
            for c in w.get("interventions", []):
                cf, removed = W.remove_with_cascade(reps, c[1]["remove"])
                q = dict(c[3], qid=c[0], subject="key", attribute="loc")
                self.assertEqual(removed, c[2])
                self.assertEqual(Memory(cf).answer(q), c[4])
                self.assertEqual(reference_answers(cf, [q])[0][c[0]], c[4])
                n += 1
        self.assertGreaterEqual(n, 50)


def random_world(seed):
    rng = HashRng(seed)
    ranks = {"self": 3, "a": 2, "b": 2, "c": 1, "d": 1}
    names = list(ranks)
    facts = [("k", "loc"), ("k", "hold"), ("event:x", "day")]
    reps = []
    for n in range(rng.below(25) + 1):
        day = 1 + n // 2
        s, a = facts[rng.below(3)]
        src = names[rng.below(5)]
        kind = ("assert", "assert", "correct", "retract")[rng.below(4)]
        prior = [r for r in reps if (r["subject"], r["attribute"]) == (s, a)]
        if kind != "assert" and not prior:
            kind = "assert"
        rid = f"r{n + 1:05d}"
        r = {"report_id": rid, "report_day": day, "source": src, "rank": ranks[src], "origin": "o" + rid,
             "subject": s, "attribute": a, "kind": kind, "value": None, "valid_from": None,
             "target_report_id": None}
        vals = ["A", "B", "C"] if s == "k" else [2, 3, 4, 5]
        if kind == "assert":
            r["value"] = vals[rng.below(len(vals))]
            r["valid_from"] = 0 if s.startswith("event") else rng.below(day + 1)
        else:
            r["target_report_id"] = prior[rng.below(len(prior))]["report_id"]
            if kind == "correct":
                ch = rng.below(3)
                if ch != 1:
                    r["value"] = vals[rng.below(len(vals))]
                if ch != 0 and not s.startswith("event"):
                    r["valid_from"] = rng.below(day + 1)
                if r["value"] is None and r["valid_from"] is None:
                    r["value"] = vals[0]
        reps.append(r)
    return reps


class MemoryVsReference(unittest.TestCase):
    def test_random_worlds_agree_on_every_operator(self):
        for i in range(400):
            reps = random_world(f"t{i}")
            now = reps[-1]["report_day"] + 1
            rng = HashRng(f"tq{i}")
            qs = []
            for a in ("loc", "hold"):
                base = {"subject": "k", "attribute": a, "now": now}
                qs += [dict(base, op="current"), dict(base, op="history"), dict(base, op="conflicts"),
                       dict(base, op="before", anchor="x")]
                for _ in range(2):
                    k1 = rng.below(now)
                    qs += [dict(base, op="valid_at", v=rng.below(now + 1)),
                           dict(base, op="believed_at", t=rng.below(now + 1)),
                           dict(base, op="why_changed", v=rng.below(now + 1), k1=k1,
                                k2=k1 + 1 + rng.below(now - k1))]
            for n, q in enumerate(qs):
                q["qid"] = f"q{n}"
            m, gold = Memory(reps), reference_answers(reps, qs)[0]
            for q in qs:
                self.assertEqual(m.answer(q), gold[q["qid"]], (i, q))


class Store(unittest.TestCase):
    def setUp(self):
        _, self.reps, _ = next(conformance_worlds())

    def test_roundtrip_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "s.jsonl"
            st = ReportStore(p)
            st.extend(self.reps)
            seal = st.seal()
            self.assertEqual(ReportStore(p, expect=seal).reports, self.reps)
            lines = p.read_text().splitlines()
            p.write_text("\n".join(lines[:-1]) + "\n")
            with self.assertRaises(StoreCorrupted):
                ReportStore(p, expect=seal)                 # cut-off tail
            p.write_text("\n".join([lines[0].replace("old mill", "old mall")] + lines[1:]) + "\n")
            with self.assertRaises(StoreCorrupted):
                ReportStore(p)                              # changed record
            p.write_text("\n".join([lines[1], lines[0]] + lines[2:]) + "\n")
            with self.assertRaises(StoreCorrupted):
                ReportStore(p)                              # reordered

    def test_order_enforced(self):
        st = ReportStore()
        st.extend(self.reps[:2])
        with self.assertRaises(ValueError):
            st.extend([self.reps[0]])

    def test_report_shape(self):
        good = dict(self.reps[0])
        check_report(good)
        for bad in (dict(good, kind="assert", value=None), dict(good, kind="retract"),
                    dict(good, rank=4), dict(good, report_id="x1"), dict(good, extra=1),
                    dict(good, kind="correct", target_report_id="r00001", value=None, valid_from=None)):
            with self.assertRaises(ReportError):
                check_report(bad)


class Generator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = W.generate_split("dev")

    def test_deterministic(self):
        again = W.generate_split("dev")
        self.assertEqual(W.world_digest(self.pairs), W.world_digest(again))
        self.assertEqual(len(self.pairs), 9 * W.PAIRS["dev"])

    def test_pairs_differ_only_in_the_critical_report(self):
        for pair in self.pairs:
            for inst in pair["instances"]:
                ra, rb = inst["A"]["reports"], inst["B"]["reports"]
                self.assertEqual([r["report_id"] for r in ra], [r["report_id"] for r in rb])
                self.assertEqual([r["report_day"] for r in ra], [r["report_day"] for r in rb])
                self.assertEqual([x["report_id"] for x, y in zip(ra, rb) if x != y], [inst["crit_id"]])
                self.assertEqual(len(inst["A"]["questions"]), len(W.QUESTION_TABLE[pair["family"]]))

    def test_case_table_counts(self):
        kinds = sum(len(v) for v in W.QUESTION_TABLE.values())
        self.assertEqual(kinds, 30)
        self.assertEqual(kinds * 2 * len(W.DELAYS) * W.PAIRS["holdout"], 9600)

    def test_delays_and_audit(self):
        for pair in self.pairs:
            for inst in pair["instances"]:
                n_irrelevant = len(inst["A"]["reports"]) - inst["n_relevant"]
                self.assertEqual(n_irrelevant, inst["delay"])
                for world in ("A", "B"):
                    self.assertEqual(W.audit_world(inst[world]["reports"], pair["ranks"], pair["anchor"],
                                                   pair["fact"], True), [])
                    self.assertTrue(all(r["report_day"] < inst["now"] for r in inst[world]["reports"]))


class Audit(unittest.TestCase):
    ranks = {"self": 3, "ana": 2, "bo": 2, "cy": 1}

    def audit(self, rows, original=True, anchor=None):
        return W.audit_world([rep(r) for r in rows], self.ranks, anchor, ("key", "loc"), original)

    def test_detects_violations(self):
        base = ["r00001", 1, "self", 3, "key", "loc", "assert", "A", 1, None]
        cases = {
            "dangling": [base, ["r00002", 2, "ana", 2, "key", "loc", "retract", None, None, "r00009"]],
            "retract target": [base, ["r00002", 2, "self", 3, "key", "loc", "retract", None, None, "r00001"],
                               ["r00003", 3, "self", 3, "key", "loc", "correct", "B", None, "r00002"]],
            "other fact": [base, ["r00002", 2, "self", 3, "key", "hold", "correct", "B", None, "r00001"]],
            "rank table": [["r00001", 1, "self", 2, "key", "loc", "assert", "A", 1, None]],
            "claimless target": [base, ["r00002", 2, "cy", 1, "key", "loc", "correct", "B", None, "r00001"],
                                 ["r00003", 3, "self", 3, "key", "loc", "correct", "C", None, "r00002"]],
        }
        for name, rows in cases.items():
            with self.subTest(name):
                self.assertNotEqual(self.audit(rows), [])
        # a claimless target is allowed in a counterfactual world
        self.assertEqual(self.audit(cases["claimless target"], original=False), [])
        same_origin = [rep(base), rep(["r00002", 2, "self", 3, "key", "loc", "assert", "B", 1, None], "o-r00001")]
        self.assertNotEqual(W.audit_world(same_origin, self.ranks, None, ("key", "loc"), True), [])
        anchor_clash = [base, ["r00002", 2, "self", 3, "event:met", "day", "assert", 1, 0, None]]
        self.assertNotEqual(self.audit(anchor_clash, anchor="met"), [])
        self.assertEqual(self.audit([base]), [])


class Baselines(unittest.TestCase):
    def test_outputs_and_states(self):
        name, reps, w = next(conformance_worlds())
        qs = [dict(c[1], qid=c[0], subject="key", attribute="loc") for c in w["checks"]]
        hq = [{"qid": "__hist", "op": "history", "subject": "key", "attribute": "loc", "now": 11}]
        gold = reference_answers(reps, qs + hq)[0]
        ctx = {"hist": gold["__hist"], "anchor_hist": []}
        q_now = dict(op="valid_at", v=5, now=11, qid="x", subject="key", attribute="loc")
        self.assertEqual(B.s1(reps, q_now, ctx)["value"], "library")          # last assert received
        self.assertEqual(B.s2(reps, q_now, ctx)["value"], "harbour")          # ignores the correction
        self.assertEqual(B.s3(reps, q_now, ctx)["value"], "bridge")           # first / previous / current (3 versions)
        self.assertEqual(B.s4(reps, q_now, ctx)["value"], "library")          # current only
        for s in B.SYSTEMS:
            for q in qs:
                B.ANSWER[s](reps, q, ctx)                                     # an output for every operator

    def test_hit_ignores_ids_for_value_operators(self):
        g = {"status": "value", "value": "X", "ids": ["r00001"]}
        self.assertTrue(A.hit("current", g, {"status": "value", "value": "X", "ids": []}))
        self.assertFalse(A.hit("history", [g], [dict(g, ids=[])]))
        self.assertFalse(A.hit("current", g, {"status": "conflict", "values": ["X"], "ids": []}))


class Interventions(unittest.TestCase):
    def test_counterfactuals_are_valid_and_cascade(self):
        for pair in W.generate_split("dev")[::7]:
            inst = pair["instances"][1]
            for kind, fams in W.INTERVENTIONS.items():
                if pair["family"] not in fams:
                    continue
                cf = W.counterfactual(pair, inst, kind)
                if cf is None:
                    continue
                self.assertEqual(W.audit_world(cf["reports"], cf["ranks"], pair["anchor"], pair["fact"], False), [])
                ids = {r["report_id"] for r in cf["reports"]}
                self.assertTrue(all(r["target_report_id"] in ids for r in cf["reports"] if r["target_report_id"]))
                self.assertTrue(set(cf["removed"]).isdisjoint(ids))


if __name__ == "__main__":
    unittest.main()
