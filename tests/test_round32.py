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
        # and the index does not certify a selection while undated or unknown records could match
        got, ok = struct_select(s.records, "latest", {"person": "Ana Bell"})
        self.assertFalse(ok)

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
    def run_collect(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            req, pins = dest / "req.json", dest / "pins.json"
            req.write_text(json.dumps({"model": "m", "worlds": {SERIES: [0]}}))
            pins.write_text("{}")
            data = json.loads(json.dumps(data))
            data["provenance"].update(request_sha256=collect_round32.sha256_file(req),
                                      pins_sha256=collect_round32.sha256_file(pins))
            (dest / f"r32_{SERIES}_0.json").write_text(json.dumps(data))
            collect_round32.main(str(req), str(dest), str(pins))
            return ((dest / "VERDICT").read_text().strip(), (dest / "CHECK.txt").read_text(),
                    (dest / "SUMMARY.md").read_text())

    def test_complete(self):
        verdict, check, summary = self.run_collect(DATA)
        self.assertEqual(verdict, "COMPLETE", check)
        self.assertIn("| full+ops | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 |", summary)
        self.assertIn("ADOPT the LM encoder", summary)
        self.assertIn("truncated refused 2/2", summary)

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
