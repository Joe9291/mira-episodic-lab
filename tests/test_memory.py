"""Round 3.2 memory: store integrity, operators, three-valued negatives, restart."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from episodic_lab.memory import (EpisodeStore, MemoryAgent, StoreCorrupted, answer_query,  # noqa: E402
                                 parse_question, regex_encode)
from episodic_lab.questions import make_world  # noqa: E402
from episodic_lab.runner import run_world  # noqa: E402

PAIR = make_world("memory-test", 0)[1]

RESTART = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from episodic_lab.memory import EpisodeStore, answer_query, parse_question
store = EpisodeStore(sys.argv[2])
questions = json.loads(open(sys.argv[3]).read())
print(json.dumps({q["qid"]: answer_query(store.records, *parse_question(q["text"])).answer()
                  for q in questions}))
"""


def encoded_store(path, world):
    store = EpisodeStore(path)
    for e in world["episodes"]:
        store.append(e["text"], regex_encode(e["text"]))
    return store


class StoreTests(unittest.TestCase):
    def test_round_trip_and_tamper_detection(self):
        world, _ = PAIR["high"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "store.jsonl"
            store = encoded_store(path, world)
            again = EpisodeStore(path)
            self.assertEqual(again.records, store.records)
            lines = path.read_text().splitlines()
            for broken in (lines[:3] + lines[4:],                                   # removed
                           [lines[1], lines[0]] + lines[2:],                         # reordered
                           [lines[0].replace('"Day', '"day')] + lines[1:]
                           if '"Day' in lines[0] else
                           [json.dumps(dict(json.loads(lines[0]), place="Elsewhere"), sort_keys=True)] + lines[1:]):
                path.write_text("\n".join(broken) + "\n")
                with self.assertRaises(StoreCorrupted):
                    EpisodeStore(path)

    def test_append_only_interface(self):
        store = EpisodeStore()
        rec = store.append("x", {"actor": "A B", "partner": None, "action": "hid", "object": "c d",
                                 "place": "E F", "event_day": 1})
        rec["place"] = "changed"
        self.assertEqual(store.records[0]["place"], "E F")
        with self.assertRaises(ValueError):
            store.append("y", {"actor": "A B"})
        content = {k: rec[k] for k in ("actor", "partner", "action", "object", "place", "event_day")}
        with self.assertRaises(ValueError):
            store.append("y", content, source={"kind": "dream", "by": None})
        store.append("y", content, source={"kind": "reported", "by": "C D"})
        self.assertEqual(store.records[1]["source"], {"kind": "reported", "by": "C D"})


class OperatorTests(unittest.TestCase):
    def test_full_system_solves_the_template_worlds(self):
        for overlap, (world, questions) in PAIR.items():
            result = run_world(MemoryAgent(EpisodeStore()), world, questions)
            self.assertTrue(all(r["correct"] for r in result["rows"]), overlap)

    def test_three_valued_negatives(self):
        world, questions = PAIR["high"]
        store = encoded_store(None, world)
        recs = store.records
        lure = next(q for q in questions["public"]["final"]
                    if questions["gold"][q["qid"]]["criterion"] == "E5")
        self.assertEqual(answer_query(recs, *parse_question(lure["text"])).status, "none_in_scope")
        unknown = answer_query(recs, "place", {"cue": {"person": "Nobody Known", "action": "hid",
                                                       "obj": recs[0]["object"]}})
        self.assertEqual((unknown.status, unknown.answer()), ("no_observation", "unknown"))
        r0 = recs[0]
        amb = answer_query(recs, "object", {"cue": {"person": r0["actor"]}})
        self.assertEqual(amb.status, "ambiguous")

    def test_every_answer_carries_its_trace(self):
        world, questions = PAIR["low"]
        recs = encoded_store(None, world).records
        ids = {r["id"] for r in recs}
        for q in questions["public"]["final"]:
            res = answer_query(recs, *parse_question(q["text"]))
            self.assertTrue(res.trace)
            self.assertTrue(set(res.ids) <= ids)
            if res.status == "ok":
                self.assertTrue(res.ids)

    def test_misbound_store_breaks_binding_items(self):
        import random
        world, questions = PAIR["high"]
        recs = encoded_store(None, world).records
        rnd = random.Random(0)
        places = [r["place"] for r in recs]
        rnd.shuffle(places)
        misbound = [dict(r, place=p) for r, p in zip(recs, places)]
        def acc(rs):
            ok = 0
            for q in questions["public"]["final"]:
                g = questions["gold"][q["qid"]]
                ok += answer_query(rs, *parse_question(q["text"])).answer() in g["gold"]
            return ok / len(questions["public"]["final"])
        self.assertEqual(acc(recs), 1.0)
        self.assertLess(acc(misbound), 0.8)


class RestartTests(unittest.TestCase):
    def test_fresh_process_answers_from_the_store_only(self):
        world, questions = PAIR["high"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            store = encoded_store(tmp / "store.jsonl", world)
            (tmp / "q.json").write_text(json.dumps(questions["public"]["final"]))
            (tmp / "restart.py").write_text(RESTART)
            out = subprocess.run([sys.executable, "-I", str(tmp / "restart.py"), str(ROOT),
                                  str(tmp / "store.jsonl"), str(tmp / "q.json")],
                                 capture_output=True, text=True, check=True)
            after = json.loads(out.stdout)
            before = {q["qid"]: answer_query(store.records, *parse_question(q["text"])).answer()
                      for q in questions["public"]["final"]}
            self.assertEqual(after, before)
            self.assertTrue(all(after[q] in questions["gold"][q]["gold"] for q in after))
            empty = subprocess.run([sys.executable, "-I", str(tmp / "restart.py"), str(ROOT),
                                    str(tmp / "none.jsonl"), str(tmp / "q.json")],
                                   capture_output=True, text=True, check=True)
            blank = json.loads(empty.stdout)
            positives = [q for q in blank if questions["gold"][q]["gold"] != ["none"]]
            self.assertTrue(all(blank[q] not in questions["gold"][q]["gold"] for q in positives))


if __name__ == "__main__":
    unittest.main()
