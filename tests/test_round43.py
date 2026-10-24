"""Round 4.3 hand cases (docs/ROUND_4_3.md section 8): every equivalence of proof
obligation 1, every citation role, composition, tamper and interrupted writes, the lost
distractor fact, the digest grouping, the test-only control path, and the world module."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from episodic_lab import r43_consolidate as X
from episodic_lab import r43_reference as RF
from episodic_lab import r43_world as W
from episodic_lab.r40_memory import Memory, StoreCorrupted
from episodic_lab.r40_reference import reference_answers


def rep(i, day, src, rank, kind, value=None, vf=None, target=None, subject="key", attribute="loc", origin=None):
    return {"report_id": f"r{i:05d}", "report_day": day, "source": src, "rank": rank,
            "origin": origin or f"o-r{i:05d}", "subject": subject, "attribute": attribute, "kind": kind,
            "value": value, "valid_from": vf, "target_report_id": target}


def questions(now, days, vfs):
    qs = [{"op": "current"}, {"op": "history"}, {"op": "conflicts"}, {"op": "digest"}]
    qs += [{"op": "valid_at", "v": v} for v in vfs] + [{"op": "believed_at", "t": t} for t in days]
    qs += [{"op": "digest_at", "t": t} for t in days]
    qs += [{"op": "why_changed", "v": v, "k1": t, "k2": now} for v in vfs for t in days if t < now]
    return [dict(q, qid=f"q{n}", now=now, subject="key", attribute="loc") for n, q in enumerate(qs)]


def gold(reps, qs):
    m = Memory(reps)
    out = {}
    for q in qs:
        if q["op"] in ("digest", "digest_at"):
            out[q["qid"]] = X.full_digest(m, ("key", "loc"), q["now"] if q["op"] == "digest" else q["t"])
        else:
            out[q["qid"]] = m.answer(q)
    return out


# worlds for proof obligation 1: a correction / retraction whose target is withdrawn,
# claimless (an ineffective correction) or missing; plus effective ones
WORLDS = {
    "target_withdrawn": [rep(1, 1, "ana", 2, "assert", "mill", 1), rep(2, 2, "ana", 2, "retract", target="r00001"),
                         rep(3, 4, "self", 3, "correct", "bridge", None, "r00001"),
                         rep(4, 5, "ana", 2, "retract", target="r00001"), rep(5, 6, "self", 3, "assert", "forge", 6)],
    "target_claimless": [rep(1, 1, "self", 3, "assert", "mill", 1), rep(2, 2, "ben", 1, "correct", "harbour", None, "r00001"),
                         rep(3, 4, "self", 3, "correct", "bridge", None, "r00002"),
                         rep(4, 5, "ben", 1, "retract", target="r00002"), rep(5, 6, "ana", 2, "assert", "forge", 6)],
    "target_missing": [rep(1, 1, "self", 3, "assert", "mill", 1), rep(2, 3, "self", 3, "correct", "bridge", None, "r00099"),
                       rep(3, 4, "ana", 2, "retract", target="r00099"), rep(4, 6, "ana", 2, "assert", "forge", 6)],
    "effective_across_cut": [rep(1, 1, "ana", 2, "assert", "mill", 1), rep(2, 2, "ben", 1, "assert", "harbour", 1),
                             rep(3, 3, "cara", 2, "assert", "dock", 1, origin="o-x"),
                             rep(4, 5, "self", 3, "correct", "bridge", 2, "r00001"),
                             rep(5, 6, "cara", 2, "retract", target="r00003"), rep(6, 7, "ben", 1, "assert", "mill", 7),
                             rep(7, 8, "self", 3, "assert", "mill", 7, origin="o-r00006")],
}


class ProofObligations(unittest.TestCase):
    def test_every_cut_mode_t_equals_m_and_r(self):
        for name, reps in WORLDS.items():
            recs = X.chain_records(reps)
            now = reps[-1]["report_day"] + 1
            days = sorted({r["report_day"] for r in reps})
            vfs = sorted({r["valid_from"] for r in reps if r["valid_from"] is not None})
            qs = questions(now, days, vfs)
            g = gold(reps, qs)
            plain = [q for q in qs if not q["op"].startswith("digest")]
            r = reference_answers(reps, plain)[0]
            for q in plain:
                self.assertEqual(r[q["qid"]], g[q["qid"]], (name, q))
            for q in qs:
                if q["op"].startswith("digest"):
                    k = q["now"] if q["op"] == "digest" else q["t"]
                    self.assertEqual(RF.reference_digest(reps, "key", "loc", k), g[q["qid"]], (name, q))
            ref = RF.reference_state(reps, range(0, now + 1))
            for c in range(0, now + 1):
                cp = X.build_checkpoint(reps, recs, c)
                self.assertEqual(X.normalised(X.checkpoint_claims(cp)), ref[c], (name, c))
                h = X.mode_t(cp, reps, recs, X.trust_record(cp, X.seal_of(recs, len(reps))))
                for q in qs:
                    got = h.answer(q)
                    if X.needed_time(q) < c:
                        self.assertIn(got, ("compacted", X.COMPACTED), (name, c, q))
                    else:
                        self.assertEqual(got, g[q["qid"]], (name, c, q))
                for k in range(c, now + 1):
                    self.assertEqual(X.normalised(h.state_at(k)), ref[k], (name, c, k))
                # effectiveness of the tail's corrections / retractions = R's
                tail = reps[X.prefix_len(reps, c):]
                r_eff = RF.effectiveness(reps)
                self.assertEqual(h.effectiveness(),
                                 {x["report_id"]: r_eff[x["report_id"]] for x in tail if x["kind"] != "assert"})

    def test_withdrawn_claimless_missing_are_all_ineffective(self):
        eff = RF.effectiveness(WORLDS["target_withdrawn"])
        self.assertEqual((eff["r00002"], eff["r00003"], eff["r00004"]), (True, False, False))
        eff = RF.effectiveness(WORLDS["target_claimless"])
        self.assertEqual((eff["r00002"], eff["r00003"], eff["r00004"]), (False, False, False))
        eff = RF.effectiveness(WORLDS["target_missing"])
        self.assertEqual((eff["r00002"], eff["r00003"]), (False, False))

    def test_highest_id_belongs_to_a_withdrawn_or_ineffective_report(self):
        # Astra's idea: the highest prefix id is a retraction / an ineffective correction
        for name, cut in (("target_withdrawn", 2), ("target_claimless", 2)):
            reps = WORLDS[name]
            cp = X.build_checkpoint(reps, X.chain_records(reps), cut)
            self.assertEqual(cp["highest_id"], "r00002")
            self.assertNotIn("r00002", {x["id"] for x in X.checkpoint_claims(cp)})
            tail = reps[X.prefix_len(reps, cut):]
            with self.assertRaises(StoreCorrupted):
                X.Hot({cut: cp}, [dict(tail[0], report_id="r00002")] + tail[1:], floor=cut, highest_id=cp["highest_id"])


class Citations(unittest.TestCase):
    def test_roles(self):
        reps = WORLDS["effective_across_cut"]
        recs = X.chain_records(reps)
        cp = X.build_checkpoint(reps, recs, 4)
        h = X.mode_t(cp, reps, recs, X.trust_record(cp, X.seal_of(recs, len(reps))))
        q = {"qid": "w", "op": "why_changed", "v": 2, "k1": 4, "k2": 9, "now": 9, "subject": "key", "attribute": "loc"}
        ids = h.answer(q)                                   # change evidence: reports of (k1, k2]
        self.assertEqual(ids, ["r00004"])
        self.assertTrue(all(4 < next(r for r in reps if r["report_id"] == i)["report_day"] <= 9 for i in ids))
        cur = h.answer(dict(q, op="current"))               # value evidence: standing at now
        standing = {t[2] for t in RF.reference_state(reps, [9])[9]}
        self.assertTrue(set(cur["ids"]) <= standing)
        eff = h.effectiveness()                             # target references
        self.assertEqual(eff, {"r00004": True, "r00005": True})


class Digest(unittest.TestCase):
    def test_grouping(self):
        reps = WORLDS["effective_across_cut"]
        d = X.full_digest(Memory(reps), ("key", "loc"), 9)
        self.assertEqual(d, RF.reference_digest(reps, "key", "loc", 9))
        self.assertEqual(d["segments"][0]["value"], "harbour")   # day 1 at k = 9: mill corrected, dock retracted
        d4 = X.full_digest(Memory(reps), ("key", "loc"), 4)       # k = 4: mill (ana) and dock (cara) conflict
        self.assertEqual(d4, RF.reference_digest(reps, "key", "loc", 4))
        seg1 = d4["segments"][0]
        self.assertEqual((seg1["status"], seg1["values"]), ("conflict", ["dock", "mill"]))
        self.assertEqual([e["id"] for e in seg1["dissent"]], ["r00002"])     # harbour, outranked
        self.assertEqual([g["value"] for g in seg1["support"]], ["dock", "mill"])
        last = d["segments"][-1]                            # day 7: own mill decides, ben's mill agrees
        self.assertEqual([g["claims"][0]["id"] for g in last["agree"]], ["r00006"])
        self.assertEqual(last["independent_origins"], [{"value": "mill", "n": 1}])   # same origin
        entries = X.digest_entries(d)
        self.assertEqual(sorted(e["id"] for e in entries),
                         sorted(t[2] for t in RF.reference_state(reps, [9])[9]))   # partition
        # a conflict segment and merged versions
        reps2 = [rep(1, 1, "ana", 2, "assert", "A", 1), rep(2, 1, "ben", 2, "assert", "B", 1),
                 rep(3, 2, "ana", 2, "assert", "A", 3), rep(4, 2, "ben", 2, "assert", "B", 3),
                 rep(5, 3, "self", 3, "assert", "C", 5), rep(6, 3, "self", 3, "assert", "C", 6, origin="o-y")]
        d2 = X.full_digest(Memory(reps2), ("key", "loc"), 4)
        self.assertEqual(d2, RF.reference_digest(reps2, "key", "loc", 4))
        self.assertEqual([(s["status"], s["valid_from"], s["valid_to"]) for s in d2["segments"]],
                         [("conflict", 1, 4), ("value", 5, None)])
        self.assertEqual([g["value"] for g in d2["segments"][0]["support"]], ["A", "B"])


class IntegrityAndComposition(unittest.TestCase):
    def setUp(self):
        self.reps = WORLDS["effective_across_cut"]
        self.recs = X.chain_records(self.reps)

    def test_composition_and_parent(self):
        c1 = X.build_checkpoint(self.reps, self.recs, 3)
        c2 = X.extend_checkpoint(c1, self.reps, self.recs, 6)
        self.assertEqual(X.canonical(c2), X.canonical(X.build_checkpoint(self.reps, self.recs, 6, c1["hash"])))
        self.assertNotEqual(c2["hash"], X.build_checkpoint(self.reps, self.recs, 6)["hash"])   # other parent
        self.assertEqual(c2["facts"], X.build_checkpoint(self.reps, self.recs, 6)["facts"])

    def test_tamper_and_interrupted(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench/m3"))
        import run_round43 as RUN
        cp = X.build_checkpoint(self.reps, self.recs, 3)
        tail = self.reps[X.prefix_len(self.reps, 3):]
        with tempfile.TemporaryDirectory() as tmp:
            res = RUN.tamper_cases(cp, tail, X.build_checkpoint(self.reps, self.recs, 0), self.reps, tmp)
            self.assertEqual(len(res), RUN_TAMPER_CASES)
            self.assertTrue(all(res.values()), res)
            cp_b = X.extend_checkpoint(cp, self.reps, self.recs, 6)
            res = RUN.interrupted_writes(cp, tail, cp_b, self.reps[X.prefix_len(self.reps, 6):], tmp)
            self.assertTrue(all(res.values()), res)

    def test_full_state_check_sees_every_field(self):
        # Astra's idea: change origin, source, rank of one claim - the normalised comparison differs
        cp = X.build_checkpoint(self.reps, self.recs, 9)
        ref = RF.reference_state(self.reps, [9])[9]
        for field, val in (("origin", "o-other"), ("source", "zed"), ("rank", 2), ("value", "zz"), ("valid_from", 99)):
            bad = json.loads(json.dumps(cp))
            bad["facts"][0]["claims"][0][field] = val
            self.assertNotEqual(X.normalised(X.checkpoint_claims(bad)), ref, field)

    def test_lost_unasked_fact(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench/m3"))
        import run_round43 as RUN
        reps = self.reps + [rep(8, 9, "ana", 2, "assert", "x", 9, subject="other", attribute="loc")]
        recs = X.chain_records(reps)
        cp = X.build_checkpoint(reps, recs, 9)
        ref = RF.reference_state(reps, [9])[9]
        self.assertTrue(RUN.lost_fact_detected(cp, {("key", "loc")}, ref))

    def test_control_path_is_not_a_mode(self):
        claims = RF.control_claims(self.reps, 4, "K3")
        pseudo = {"facts": [], "cut": 4}
        with self.assertRaises(Exception):
            X.mode_t(pseudo, self.reps, self.recs, X.trust_record({"hash": "x", "archive_seal": {}}, {}))
        h = X.control_memory(claims, 4, self.reps)          # the test path itself works
        self.assertEqual(h.floor, 4)


RUN_TAMPER_CASES = 12


class WorldModule(unittest.TestCase):
    def test_counts_file_and_contract(self):
        frozen = json.loads((Path(__file__).resolve().parents[1] / "config/round43_counts.json").read_text())
        self.assertEqual(frozen["seeds"], W.SEEDS)
        pairs = list(W.iter_pairs("dev"))
        self.assertEqual(len(pairs), 140)
        self.assertTrue(all(W.ids_monotonic(i[w]["reports"]) for p in pairs for i in p["instances"] for w in "AB"))
        self.assertEqual(sum(len(i[w]["cuts"]) for p in pairs for i in p["instances"] for w in "AB"),
                         frozen["splits"]["dev"]["total"]["cuts"])


if __name__ == "__main__":
    unittest.main()
