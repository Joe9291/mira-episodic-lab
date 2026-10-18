"""Round 3.2 cells, job and collector with fake models (no PyTorch)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench" / "m3"))
sys.path.insert(0, str(ROOT / "tests"))

import collect_round32  # noqa: E402
import run_round32  # noqa: E402
from episodic_lab.cells import CELLS, INVALID, LMEncoder, _clean, bm25_top, struct_select  # noqa: E402
from episodic_lab.memory import EpisodeStore, parse_question, regex_encode  # noqa: E402
from episodic_lab.questions import make_world  # noqa: E402
from episodic_lab.runner import StateChangedWhileAnswering, run_world  # noqa: E402
from test_arms import FakeModel  # noqa: E402

SERIES = "round32-test"
ATTEMPT, PAIR = make_world(SERIES, 0, order_both=True)


class SlotModel(FakeModel):
    """Reads story notes like FakeModel; answers encoder slot questions from the note."""
    slug = "fake"

    def generate(self, messages):
        user = messages[1]["content"]
        if user.startswith("Coverage:"):
            return self.contract_reader(user)
        if not user.startswith("Note:\n"):
            return super().generate(messages)
        self.stats["calls"] += 1
        note, question = user[len("Note:\n"):].split("\n\nQuestion: ")
        f = regex_encode(note)
        for key, slot in (("day", "event_day"), ("do?", "action"), ("second person", "partner"),
                          ("first person", "actor"), ("object", "object"), ("place", "place")):
            if key in question:
                v = f[slot]
                return "none" if v is None else (f"Day {v}" if slot == "event_day" else str(v))
        return "unknown"


def _contract_reader(self, user):
    """An ideal reader that follows the round 3.2 contract: reads only its notes, says
    "none" only for complete coverage with all names known, "unknown" otherwise."""
    from episodic_lab.symbolic import SymbolicMemory
    self.stats["calls"] += 1
    head, rest = user.split("\n\nMemory notes:\n")
    notes, question = rest.split("\n\nQuestion: ")
    covered = "Coverage: complete" in head
    all_known = "Every person, place and object" in head
    memory = SymbolicMemory()
    if notes != "(no notes)":
        for line in notes.split("\n"):
            memory.encode(line)
    reply = memory.answer(question, None)
    qtype = parse_question(question)[0]
    if reply in ("none", "unknown") or (not covered and qtype in ("latest", "act", "find")):
        return "none" if (reply == "none" and covered and all_known) else "unknown"
    return reply


SlotModel.contract_reader = _contract_reader


def job(model=None):
    data = {"schema": run_round32.SCHEMA, "model": "m", "series": SERIES, "index": 0, "status": "OK",
            "attempt": ATTEMPT, "conditions": {},
            "provenance": {"code_commit": "c", "request_sha256": None, "pins_sha256": None}}
    with tempfile.TemporaryDirectory() as tmp:
        for overlap, (world, questions) in PAIR.items():
            cond = data["conditions"][overlap] = {
                "seed": world["seed"], "world_sha256": run_round32.canonical_sha256(world),
                "questions_sha256": run_round32.canonical_sha256(questions), "cells": {}}
            run_round32.run_condition(model or SlotModel(), world, questions, cond, Path(tmp))
    return json.loads(json.dumps(data))


DATA = job()


class CellTests(unittest.TestCase):
    def test_same_selection_within_a_retrieval_method(self):
        world, questions = PAIR["low"]
        for reader, ops in (("lex3+reader", "lex3+ops"), ("struct3+reader", "struct3+ops")):
            a, b = CELLS[reader](SlotModel()), CELLS[ops]()
            for e in world["episodes"]:
                a.encode(e["text"])
                b.encode(e["text"])
            for q in questions["public"]["final"]:
                ea, eb = a.explain(q["text"], a.store._records), b.explain(q["text"], b.store._records)
                self.assertEqual((ea["selected"], ea["covered"], ea["entity_note"]),
                                 (eb["selected"], eb["covered"], eb["entity_note"]))
                # what the reader is told equals what the operators use
                prompt = a.reader_prompt(q["text"], q["answer_type"], a.store._records)[1]["content"]
                self.assertEqual("Coverage: complete" in prompt, eb["covered"])
                self.assertEqual(eb["entity_note"] is not None and eb["entity_note"] in prompt, eb["covered"])
                notes = prompt.split("Memory notes:\n")[1].split("\n\nQuestion: ")[0].split("\n")
                texts = {r["id"]: r["text"] for r in b.store._records}
                self.assertEqual(notes, [texts[i] for i in eb["selected"]] or ["(no notes)"])

    def test_incomplete_scope_never_gives_a_negative_or_latest(self):
        world, questions = PAIR["high"]
        cell = CELLS["lex3+ops"]()
        for e in world["episodes"]:
            cell.encode(e["text"])
        for q in questions["public"]["final"]:
            res = cell.explain(q["text"], cell.store._records)["result"]
            qtype = parse_question(q["text"])[0]
            self.assertNotIn(res["status"], ("none_in_scope", "no_observation"))
            if qtype in ("latest", "act", "find"):
                self.assertEqual(res["status"], "insufficient_evidence")

    def test_struct_selection_certifies_only_what_fits(self):
        store = EpisodeStore()
        for day, place in enumerate(("Ash Mill", "Oak Mill", "Elm Mill", "Fir Mill"), start=1):
            store.append(f"n{day}", {"actor": "Ana Bell", "partner": None, "action": "hid",
                                     "object": "red cup", "place": place, "event_day": day})
        recs = store.records
        got, ok = struct_select(recs, "place", {"cue": {"person": "Ana Bell", "action": "hid", "obj": "red cup"}})
        self.assertEqual((len(got), ok), (3, False))  # 4 full matches do not fit into 3
        cell = CELLS["struct3+ops"]()
        cell.store = store
        self.assertEqual(cell.explain("Where did Ana Bell hide the red cup?", recs)["result"]["status"], "ambiguous")
        # no full match anywhere: the scan covered the whole store, so the negative is certified
        got, ok = struct_select(recs, "place", {"cue": {"person": "Ana Bell", "action": "sold", "obj": "red cup"}})
        self.assertTrue(ok)
        res = cell.explain("Where did Ana Bell sell the red cup?", recs)["result"]
        self.assertEqual(res["status"], "none_in_scope")

    def test_weight_check(self):
        class Drift(SlotModel):
            def weights_digest(self, recompute=False):
                return "w2" if recompute else "w1"
        run_round32.check_weights(SlotModel(), SlotModel().weights_digest())
        with self.assertRaises(RuntimeError):
            run_round32.check_weights(Drift(), "w1")

    def test_link_stops_when_the_first_event_is_not_unique(self):
        from episodic_lab.memory import link_latest
        world, _ = PAIR["high"]
        recs = EpisodeStore()
        for e in world["episodes"]:
            recs.append(e["text"], regex_encode(e["text"]))
        r0 = recs.records[0]
        none = link_latest(recs.records, {"action": r0["action"], "place": "Nowhere Place", "obj": r0["object"]})
        self.assertEqual((none.status, none.value), ("no_observation", None))  # place never recorded
        amb = link_latest(recs.records, {"obj": r0["object"]})
        self.assertIn(amb.status, ("ambiguous", "ok"))
        if amb.status == "ambiguous":
            self.assertIsNone(amb.value)

    def test_unknown_values_give_uncertainty_not_answers(self):
        from episodic_lab.memory import last_handler_latest, latest, state_at
        def rec(store, actor, day, place, obj="red cup", action="hid"):
            store.append(f"{actor}{day}{place}", {"actor": actor, "partner": None, "action": action,
                                                   "object": obj, "place": place, "event_day": day})
        s = EpisodeStore()
        rec(s, "Ana Bell", 7, "Oak Mill")
        rec(s, "Ana Bell", None, "Ash Mill")
        self.assertEqual(latest(s.records, "Ana Bell").status, "ambiguous")
        self.assertEqual(state_at(s.records, "Ana Bell", 9).status, "insufficient_evidence")
        self.assertEqual(last_handler_latest(s.records, "red cup").status, "ambiguous")
        # an undated record with the SAME place, or of another person, does not block the answer
        s2 = EpisodeStore()
        rec(s2, "Ana Bell", 7, "Oak Mill")
        rec(s2, "Ana Bell", None, "Oak Mill")
        rec(s2, "Cal Dorr", None, "Ash Mill", obj="blue map")
        self.assertEqual((latest(s2.records, "Ana Bell").status, latest(s2.records, "Ana Bell").value), ("ok", "Oak Mill"))
        self.assertEqual(state_at(s2.records, "Ana Bell", 7).value, "Oak Mill")
        # a missing place is never an ok answer
        s3 = EpisodeStore()
        rec(s3, "Ana Bell", 7, None)
        r = latest(s3.records, "Ana Bell")
        self.assertEqual((r.status, r.answer()), ("ambiguous", "unknown"))
        # an unknown field can make a lure undecidable, never a confident "none"
        s4 = EpisodeStore()
        rec(s4, "Ana Bell", 3, None)
        from episodic_lab.memory import find
        res = find(s4.records, {"person": "Ana Bell", "action": "hid", "place": "Oak Mill"}, "object")
        self.assertEqual(res.status, "insufficient_evidence")
        # the index certifies a selection only if it holds every record that could be the
        # latest (here both), so the operators on it give the full-store answer
        got, ok = struct_select(s.records, "latest", {"person": "Ana Bell"})
        self.assertEqual((ok, len(got)), (True, 2))
        self.assertEqual(latest(got, "Ana Bell").status, "ambiguous")

    def test_unknown_values_in_handlers_index_and_encoder(self):
        from episodic_lab.cells import postprocess
        from episodic_lab.memory import last_handler_latest
        s = EpisodeStore()
        for actor, day, place in (("Ana Bell", 5, "Oak Mill"), ("Cal Dorr", None, "Ash Mill")):
            s.append(actor + str(day), {"actor": actor, "partner": None, "action": "hid",
                                        "object": "red cup", "place": place, "event_day": day})
        self.assertEqual(last_handler_latest(s.records, "red cup").status, "ambiguous")
        # possible matches (unknown place) count against the budget of the index
        s2 = EpisodeStore()
        for i in range(4):
            s2.append(f"p{i}", {"actor": "Ana Bell", "partner": None, "action": "hid",
                                "object": "red cup", "place": None, "event_day": i + 1})
        got, ok = struct_select(s2.records, "object", {"cue": {"person": "Ana Bell", "action": "hid", "place": "Oak Mill"}})
        self.assertFalse(ok)
        # a required slot answered with "none" is an invalid slot
        raw = {"event_day": "Day 3", "actor": "Ana Bell", "partner": "none", "action": "hid",
               "object": "red cup", "place": "none"}
        content, bad = postprocess(raw)
        self.assertEqual((content["place"], bad), (None, ["place"]))

    def test_unknown_person_object_and_comparison(self):
        """v4 (Astra's review of v3): unknown actors/partners, unknown objects and second
        possible matches; and the cases in which the unknown cannot change the answer."""
        from episodic_lab.memory import compare_time, find, last_handler_latest, latest, state_at
        def store(*rows):
            s = EpisodeStore()
            for i, (actor, partner, action, obj, place, day, unk) in enumerate(rows):
                s.append(f"r{i}", {"actor": actor, "partner": partner, "action": action, "object": obj,
                                   "place": place, "event_day": day}, extra={"unknown": unk} if unk else None)
            return s.records
        # Astra's counterexample: a later record with an unknown actor could be Ana Bell
        recs = store(("Ana Bell", None, "hid", "red cup", "Oak Mill", 7, []),
                     (None, None, "hid", "red cup", "Ash Mill", 9, ["actor"]))
        self.assertEqual(latest(recs, "Ana Bell").status, "ambiguous")
        self.assertEqual(state_at(recs, "Ana Bell", 9).status, "insufficient_evidence")
        got, ok = struct_select(recs, "latest", {"person": "Ana Bell"})
        self.assertTrue(ok and {r["seq"] for r in got} == {0, 1})  # the possible record is selected
        # ... but an EARLIER unknown-actor record, or a later one at the same place, cannot change it
        for day, place in ((5, "Ash Mill"), (9, "Oak Mill")):
            recs = store(("Ana Bell", None, "hid", "red cup", "Oak Mill", 7, []),
                         (None, None, "hid", "red cup", place, day, ["actor"]))
            r = latest(recs, "Ana Bell")
            self.assertEqual((r.status, r.value), ("ok", "Oak Mill"))
        # an unknown partner could be the person as well
        recs = store(("Ana Bell", None, "hid", "red cup", "Oak Mill", 7, []),
                     ("Cal Dorr", None, "gave", "red cup", "Ash Mill", 8, ["partner"]))
        self.assertEqual(latest(recs, "Ana Bell").status, "ambiguous")
        # without the declaration a missing partner means "no second person"
        recs = store(("Ana Bell", None, "hid", "red cup", "Oak Mill", 7, []),
                     ("Cal Dorr", None, "gave", "red cup", "Ash Mill", 8, []))
        self.assertEqual(latest(recs, "Ana Bell").value, "Oak Mill")
        # unknown object: a later event whose object is unknown, by another actor
        recs = store(("Ana Bell", None, "hid", "red cup", "Oak Mill", 5, []),
                     ("Cal Dorr", None, "hid", None, "Ash Mill", 6, ["object"]))
        self.assertEqual(last_handler_latest(recs, "red cup").status, "ambiguous")
        got, ok = struct_select(recs, "act", {"obj": "red cup"})
        self.assertFalse(ok)
        recs = store(("Ana Bell", None, "hid", "red cup", "Oak Mill", 5, []),
                     ("Cal Dorr", None, "hid", None, "Ash Mill", 4, ["object"]))  # earlier: no effect
        self.assertEqual(last_handler_latest(recs, "red cup").value, "Oak Mill")
        # comparison: a second POSSIBLE match makes a side non-unique
        a = {"person": "Ana Bell", "action": "hid", "obj": "red cup", "place": "Oak Mill"}
        b = {"person": "Cal Dorr", "action": "gave", "obj": "blue map", "place": "Ash Mill"}
        base = (("Ana Bell", None, "hid", "red cup", "Oak Mill", 2, []), ("Cal Dorr", None, "gave", "blue map", "Ash Mill", 5, []))
        self.assertEqual(compare_time(store(*base), a, b).value, "A")
        self.assertEqual(compare_time(store(*base, ("Ana Bell", None, "hid", "red cup", None, 6, ["place"])), a, b).status,
                         "ambiguous")
        # ... also when the other side is missing (the answer could be "ambiguous" or "none")
        self.assertEqual(compare_time(store(base[0], ("Ana Bell", None, "hid", "red cup", None, 6, ["place"])), a, b).status,
                         "ambiguous")
        # a record whose KNOWN fields contradict the cue is no possible match
        self.assertEqual(compare_time(store(*base, ("Ana Bell", None, "hid", "blue map", None, 6, ["place"])), a, b).value,
                         "A")
        # find: an unknown field in an otherwise matching record blocks a confident "none"
        res = find(store(("Ana Bell", None, "hid", None, "Oak Mill", 3, ["object"])),
                   {"person": "Ana Bell", "action": "hid", "obj": "red cup"}, "place")
        self.assertEqual(res.status, "insufficient_evidence")

    def test_invalid_encoder_values_become_declared_unknowns(self):
        from episodic_lab.cells import postprocess
        from episodic_lab.memory import find
        raw = {"event_day": "Day 3", "actor": "Ana Bell", "partner": "someone", "action": "hid",
               "object": "red cup", "place": "unclear"}
        content, bad = postprocess(raw)
        self.assertEqual((content["place"], content["partner"], bad), (None, None, ["partner", "place"]))

        class Fixed:
            def __call__(self, text):
                return postprocess(raw)
        cell = CELLS["full+ops"](encoder=Fixed(), encoder_name="lm:fixed")
        cell.encode("Ana Bell hid the red cup at Oak Mill on day 3.")
        rec = cell.store.records[0]
        self.assertEqual(rec["extra"], {"unknown": ["partner", "place"]})
        # the invalid place is no evidence that Ana Bell hid nothing at Elm Mill
        res = find(cell.store.records, {"person": "Ana Bell", "action": "hid", "place": "Elm Mill"}, "object")
        self.assertEqual(res.status, "insufficient_evidence")

    def test_soundness_against_every_completion_of_the_unknowns(self):
        """An answer other than "unknown" (full store, or a certified struct3 selection)
        must equal the answer under EVERY completion of the unknown fields; and a certified
        selection gives the full-store answer."""
        import itertools
        import random
        from episodic_lab.memory import answer_query
        P, O, L, A = ["Ana Bell", "Ben Cole", "Cal Dorr"], ["red cup", "blue map"], ["Oak Mill", "Ash Mill"], ["hid", "gave"]
        dom = {"actor": P + ["Zed Fox"], "partner": [None] + P + ["Zed Fox"], "action": A + ["sold"],
               "object": O + ["old key"], "place": L + ["Elm Mill"], "event_day": [1, 2, 3, 4, 5]}
        fields = tuple(dom)
        rng = random.Random("v4-soundness")

        def build(rows):
            s = EpisodeStore()
            for i, (c, u) in enumerate(rows):
                s.append(f"t{i}", dict(c), extra={"unknown": u} if u else None)
            return s.records
        checked = 0
        for _ in range(400):
            rows = []
            for _ in range(rng.randint(1, 4)):
                c = {"actor": rng.choice(P), "partner": rng.choice([None, None] + P), "action": rng.choice(A),
                     "object": rng.choice(O), "place": rng.choice(L), "event_day": rng.randint(1, 4)}
                unk = [f for f in fields if rng.random() < 0.12]
                for f in unk:
                    c[f] = None
                if c["partner"] == c["actor"]:
                    c["partner"] = None
                rows.append((c, unk if rng.random() < 0.6 else [f for f in unk if f != "partner" and f != "object"]))
            slots = [(i, f) for i, (_, u) in enumerate(rows) for f in u]
            if not slots or len(slots) > 3:
                continue
            real = build(rows)
            comps = []
            for vals in itertools.product(*[dom[f] for _, f in slots]):
                done = [(dict(c), []) for c, _ in rows]
                for (i, f), v in zip(slots, vals):
                    done[i][0][f] = v
                if all(c["partner"] != c["actor"] for c, _ in done):
                    comps.append(build(done))
            ev = lambda: {"person": rng.choice(P), "action": rng.choice(A), "obj": rng.choice(O), "place": rng.choice(L)}
            cue = {k: v for k, v in {"person": rng.choice(P + [None]), "action": rng.choice(A + [None]),
                                     "obj": rng.choice(O + [None]), "place": rng.choice(L + [None])}.items() if v}
            for qtype, query in ((rng.choice(["object", "place", "person", "day"]), {"cue": cue or {"obj": "red cup"}}),
                                 ("order", {"a": ev(), "b": ev()}), ("latest", {"person": rng.choice(P)}),
                                 ("at_day", {"person": rng.choice(P), "day": rng.randint(1, 4)}),
                                 ("act", {"obj": rng.choice(O)}),
                                 ("find", {"cue": {"action": rng.choice(A), "place": rng.choice(L), "obj": rng.choice(O)}})):
                full = answer_query(real, qtype, query)
                answers = [full.answer()]
                sel, ok = struct_select(real, qtype, query)
                if ok:
                    part = answer_query(sel, qtype, query, True, real)
                    self.assertEqual((part.status, part.answer()), (full.status, full.answer()), (qtype, query))
                    answers.append(part.answer())
                for given in answers:
                    if given != "unknown":
                        checked += 1
                        self.assertEqual({answer_query(c, qtype, query).answer() for c in comps}, {given},
                                         (qtype, query, rows))
        self.assertGreater(checked, 500)

    def test_encoder_error_categories(self):
        sys.path.insert(0, str(ROOT / "bench" / "m3"))
        from encoder_errors import classify, normalisation_applied
        # Astra's counterexample: no partner in truth, reply "someone" (invalid) -> unknown,
        # not a helpful normalisation and not correct
        raw = {"actor": "Ana Bell", "partner": "someone"}
        self.assertFalse(normalisation_applied(raw))
        self.assertEqual(classify("partner", "someone", None, None, set(), "Ana Bell", ["partner"], False),
                         ("unknown", "other"))
        # the normalisation actually applied: helped / hid a role error
        raw = {"actor": "Ana Bell", "partner": "Ana Bell"}
        self.assertTrue(normalisation_applied(raw))
        self.assertEqual(classify("partner", "Ana Bell", None, None, set(), "Ana Bell", [], True),
                         ("correct", "partner_norm_ok"))
        self.assertEqual(classify("partner", "Ana Bell", "Cal Dorr", None, set(), "Ana Bell", [], True),
                         ("wrong", "partner_norm_bad"))
        # reasons are kept for declared unknowns
        self.assertEqual(classify("event_day", "Wednesday", 3, None, set(), "", ["event_day"]), ("unknown", "weekday"))
        self.assertEqual(classify("object", "umbrella", "tiny umbrella", None, set(), "", ["object"]),
                         ("unknown", "noun_only"))
        self.assertEqual(classify("action", "Painted", "painted", None, set(), "", ["action"]), ("unknown", "case_only"))

    def test_env_object_location_with_an_undated_placing(self):
        from episodic_lab.env_agent import object_location
        s = EpisodeStore()
        for day, place in ((4, "Oak Mill"), (None, "Ash Mill")):
            s.append(f"x{day}", {"actor": "Ana Bell", "partner": None, "action": "hid",
                                  "object": "red cup", "place": place, "event_day": day})
        self.assertEqual(object_location(s.records, "red cup").status, "ambiguous")

    def test_in_memory_change_during_answer_is_detected(self):
        class Sneaky(CELLS["full+ops"]):
            def answer(self, text, answer_type):
                self.store._records[0]["place"] = "Changed Place"
                return super().answer(text, answer_type)
        world, questions = PAIR["high"]
        with self.assertRaises(StateChangedWhileAnswering):
            run_world(Sneaky(), world, questions)

    def test_lexical_selection_does_not_depend_on_the_hash_seed(self):
        # GitHub run 39113777648: BM25 summed its term scores in set order, so near-ties
        # depended on PYTHONHASHSEED and the collector could not replay two worlds
        import os
        import subprocess
        script = ("import json, sys\nsys.path.insert(0, sys.argv[1])\nsys.path.insert(0, sys.argv[1] + '/bench/m3')\n"
                  "import collect_round32 as c\nfrom episodic_lab.questions import make_world\n"
                  "world, qs = make_world('dev-m3', 5, order_both=True)[1]['low']\n"
                  "raws, cell = c.replay('lex3+ops', world, qs)\n"
                  "n_early = sum(e['block'] == 'early' for e in world['episodes'])\n"
                  "recs = {'final': cell.store._records, 'phase1': [r for r in cell.store._records if r['seq'] < n_early]}\n"
                  "print(json.dumps({ph: [cell.explain(q['text'], recs[ph])['selected'] for q in qs['public'][ph]] "
                  "for ph in ('phase1', 'final')}))\n")
        outs = set()
        for seed in ("0", "2", "3"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            out = subprocess.run([sys.executable, "-c", script, str(ROOT)], capture_output=True, text=True, env=env)
            self.assertEqual(out.returncode, 0, out.stderr)
            outs.add(out.stdout)
        self.assertEqual(len(outs), 1)

    def test_retrievers_return_presentation_order_and_at_most_k(self):
        world, questions = PAIR["low"]
        store = EpisodeStore()
        for e in world["episodes"]:
            store.append(e["text"], regex_encode(e["text"]))
        recs = store.records
        for q in questions["public"]["final"]:
            qtype, query = parse_question(q["text"])
            for got in (bm25_top(recs, q["text"]), struct_select(recs, qtype, query)[0]):
                self.assertLessEqual(len(got), 3)
                self.assertEqual([r["seq"] for r in got], sorted(r["seq"] for r in got))

    def test_encoder_cleaning_and_invalid_values(self):
        self.assertIs(_clean("sometime last week", "day"), INVALID)
        self.assertEqual(_clean("Day 7.", "day"), 7)

        class Bad(SlotModel):
            def generate(self, messages):
                reply = super().generate(messages)
                return "a while ago" if "which day" in messages[1]["content"] else reply
        enc = LMEncoder(Bad())
        world, questions = PAIR["low"]
        cell = CELLS["full+ops"](encoder=enc, encoder_name="lm:bad")
        result = run_world(cell, world, questions)  # must not crash on missing days
        self.assertTrue(all(r[:1] == ["event_day"] or "event_day" in r for r in enc.invalid))
        self.assertTrue(all(rec["event_day"] is None for rec in cell.store.records))
        self.assertLess(result["final"]["E4"]["accuracy"], 0.5)


class JobTests(unittest.TestCase):
    def test_ideal_contract_reader_equals_the_operators(self):
        # same selection, same coverage and entity information, same abstention contract:
        # a reader that follows the contract perfectly answers exactly like the operators
        for c in DATA["conditions"].values():
            for reader, ops in (("lex3+reader", "lex3+ops"), ("struct3+reader", "struct3+ops")):
                a = {(r["phase"], r["qid"]): r["raw"] for r in c["cells"][reader]["rows"]}
                b = {(r["phase"], r["qid"]): r["raw"] for r in c["cells"][ops]["rows"]}
                self.assertEqual(a, b, reader)

    def test_condition_results(self):
        c = DATA["conditions"]["high"]
        cells = c["cells"]
        self.assertTrue(all(x["status"] == "OK" for x in cells.values()))
        for name in ("full+ops", "struct3+ops", "full+ops/lm-encoder"):
            self.assertTrue(all(r["correct"] for r in cells[name]["rows"]), name)
        self.assertLess(cells["random3+ops"]["final"]["E2"]["accuracy"], 0.5)
        self.assertEqual(cells["lex3+ops"]["final"]["E5"]["accuracy"], 0.0)  # cannot certify
        self.assertLess(c["misbound"]["summary"]["E2"]["accuracy"], 0.5)
        r = c["restart"]
        self.assertEqual((r["same_as_in_process"], r["accuracy_after_restart"], r["truncated_store_refused"],
                          r["changed_store_refused"], r["empty_store_positive_accuracy"]),
                         (True, 1.0, True, True, 0.0))
        support = [row["diag"]["gold_support_selected"] for row in cells["struct3+reader"]["rows"]
                   if row["diag"]["gold_support_selected"] is not None]
        self.assertTrue(support and all(support))
        self.assertTrue(all(isinstance(row["diag"]["result"]["status"], str) for row in cells["full+ops"]["rows"]))
        self.assertGreater(cells["A1"]["cost"]["calls"], 0)


class CollectorTests(unittest.TestCase):
    def run_collect(self, data, planned=(0,), commit=None, decision=False):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            req, pins = dest / "req.json", dest / "pins.json"
            req.write_text(json.dumps({"model": "m", "worlds": {SERIES: list(planned)}}))
            pins.write_text("{}")
            data = json.loads(json.dumps(data))
            data["provenance"].update(request_sha256=collect_round32.sha256_file(req),
                                      pins_sha256=collect_round32.sha256_file(pins))
            (dest / f"r32_{SERIES}_0.json").write_text(json.dumps(data))
            collect_round32.main(str(req), str(dest), str(pins), commit)
            out = ((dest / "VERDICT").read_text().strip(), (dest / "CHECK.txt").read_text(),
                   (dest / "SUMMARY.md").read_text())
            return out + ((dest / "ENCODER_DECISION").read_text().strip(),) if decision else out

    def test_complete(self):
        verdict, check, summary, decision = self.run_collect(DATA, commit="c", decision=True)
        self.assertEqual(verdict, "COMPLETE", check)
        self.assertIn("| full+ops | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 |", summary)
        self.assertIn("ADOPT the LM encoder for the round 3.2 template episode formats", summary)
        self.assertEqual(decision, "ADOPT")
        self.assertIn("truncated refused 2/2", summary)
        self.assertNotIn("acc|cov", summary)
        self.assertIn("partner normalised to none |", summary)

    def test_declared_unknowns_are_replayed(self):
        # an LM encoder with invalid slots: the collector must rebuild the same records
        # (declared unknowns included) and reproduce every answer and diagnostic
        class Vague(SlotModel):
            def generate(self, messages):
                reply = super().generate(messages)
                if "second person" in messages[1]["content"]:
                    return "someone"
                return reply
        data = job(Vague())
        recs = data["conditions"]["low"]["encoder"]["records"]
        self.assertTrue(recs and all(r["invalid"] == ["partner"] and r["lm"]["partner"] is None for r in recs))
        verdict, check, summary = self.run_collect(data)
        self.assertEqual(verdict, "COMPLETE", check)
        self.assertIn("keep the template encoder", summary)

    def test_incomplete_evaluation_gives_no_adoption(self):
        # one good world report, a second planned report missing: INCOMPLETE, no ADOPT
        verdict, check, summary, decision = self.run_collect(DATA, planned=(0, 1), decision=True)
        self.assertEqual((verdict, decision), ("INCOMPLETE", "UNDECIDABLE"), check)
        self.assertIn("FAILED r32_round32-test_1.json", check)
        self.assertNotIn("ADOPT", summary)
        self.assertIn("NOT DECIDABLE", summary)
        # a report from another code commit than the run's
        verdict, check, _, decision = self.run_collect(DATA, commit="other", decision=True)
        self.assertEqual((verdict, decision), ("INCOMPLETE", "UNDECIDABLE"))
        self.assertIn("provenance:commit", check)

    def test_damage_is_detected(self):
        def edit(f):
            d = json.loads(json.dumps(DATA))
            f(d)
            return d
        low = lambda d: d["conditions"]["low"]["cells"]
        first = lambda rows, crit: next(r for r in rows if r["criterion"] == crit and r["phase"] == "final")
        cases = [
            (lambda d: low(d)["lex3+ops"]["final"]["E2"].update(accuracy=1.0), "summary:low:lex3+ops:final"),
            (lambda d: first(low(d)["A0"]["rows"], "E2").update(correct=True, category="correct"), "rows_vs_rescore:low:A0"),
            (lambda d: low(d)["A1"]["rows"].pop(), "items:low:A1"),
            (lambda d: first(low(d)["full+ops"]["rows"], "E2").update(raw="nothing"), "replay:low:full+ops"),
            (lambda d: first(low(d)["struct3+reader"]["rows"], "E2")["diag"].update(selected=[]), "diag_replay:low:struct3+reader"),
            (lambda d: d["conditions"]["low"]["encoder"]["records"][0]["lm"].update(place="Elsewhere Place"), "encoder:low"),
            (lambda d: d["conditions"]["low"].update(world_sha256="0" * 64), "world_hash:low"),
            (lambda d: d["conditions"]["low"]["misbound"]["summary"]["E2"].update(accuracy=0.9), "misbound:low"),
            (lambda d: d["conditions"]["low"]["restart"].update(changed_store_refused="yes"), "restart:low"),
            (lambda d: low(d)["A0"]["cost"].update(calls=-1), "cost:low:A0"),
            (lambda d: d.update(series="other"), "identity:series"),
            (lambda d: d["provenance"].update(code_commit="d"), None),
            (lambda d: low(d).pop("random3+ops"), "cells:low"),
            (lambda d: low(d)["lex3+reader"].update(status="ERROR"), "cell_status:low:lex3+reader"),
            (lambda d: first(low(d)["struct3+ops"]["rows"], "E2")["diag"].update(gold_support_selected=False),
             "diag_replay:low:struct3+ops"),
            (lambda d: first(low(d)["full+ops"]["rows"], "E5")["diag"]["result"].update(status="ambiguous"),
             "diag_replay:low:full+ops"),
            (lambda d: first(low(d)["lex3+ops"]["rows"], "E2")["diag"]["result"].update(trace=[]),
             "diag_replay:low:lex3+ops"),
            (lambda d: first(low(d)["lex3+reader"]["rows"], "E2")["diag"].update(covered=True),
             "diag_replay:low:lex3+reader"),
            (lambda d: d["conditions"]["low"]["encoder"]["records"][0]["truth"].update(place="Elsewhere Place"),
             "encoder:low"),
            (lambda d: d["conditions"]["low"]["encoder"]["records"][0]["raw"].update(place="Elsewhere Place"),
             "encoder:low"),
            (lambda d: d["conditions"]["low"]["encoder"]["records"][0].update(invalid=["day"]), "encoder:low"),
        ]
        for change, reason in cases:
            verdict, check, _ = self.run_collect(edit(change))
            if reason is None:
                continue
            self.assertEqual(verdict, "INCOMPLETE", reason)
            self.assertIn(reason, check)


if __name__ == "__main__":
    unittest.main()
