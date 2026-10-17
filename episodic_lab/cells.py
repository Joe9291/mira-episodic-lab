"""Round 3.2 comparison cells (docs/ROUND_3_2.md section 4) and the LM encoder.

All cells share the store (episodes appended once, in presentation order) and the
template question parser. Within one retrieval method, the reader cell and the operator
cell receive exactly the same selected records:

  lex3   BM25 over the raw texts, top 3. Cannot certify completeness (scope incomplete).
  struct3 an index scan over ALL records: per event in the query the records matching
         every cue feature (pattern completion fills up with the best partial matches);
         time-aware for "latest" (the person's most recent records) and two-stage for E7
         (the unique cue match, then its person's most recent records). Because the scan
         covered the whole store, a missing full match or a latest record is certified
         (scope complete for this query) as long as the full matches fit in the budget.
         This processing inside the retriever is part of the "struct" method.
  full   all records (the reference system, operators only).
  random3 3 records chosen by a hash of the question (control, operators only).

Readers get the selected notes as text; operators get the selected records and the scope
flag. Answering never changes a cell's state (runner fingerprint over the actual record
contents).
"""
from __future__ import annotations

import hashlib
import math
import re

from .arms import FORMAT_V1
from .memory import (FIELDS, EpisodeStore, Result, _day, _known, _minus, answer_query, could_be_latest,
                     encode_into, match, parse_question, possible, regex_encode)

K = 3
STYLE = "v1"
_WORD = re.compile(r"[a-z0-9]+")


def bm25_top(records: list[dict], query: str, k: int = K, k1: float = 1.5, b: float = 0.75) -> list[dict]:
    """Lexical retrieval over the raw episode texts; ties by record order."""
    docs = [_WORD.findall(r["text"].lower()) for r in records]
    if not docs:
        return []
    n, avg = len(docs), sum(map(len, docs)) / len(docs)
    terms = set(_WORD.findall(query.lower()))
    df = {t: sum(t in d for d in docs) for t in terms}
    scores = []
    for i, d in enumerate(docs):
        s = 0.0
        for t in terms:
            f = d.count(t)
            if f:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(d) / avg))
        scores.append((-s, i))
    return sorted((records[i] for _, i in sorted(scores)[:k]), key=lambda r: r["seq"])


def _overlap(record: dict, cue: dict) -> int:
    n = 0
    for key, value in cue.items():
        if key == "person":
            n += value in (record["actor"], record["partner"])
        elif key == "obj":
            n += record["object"] == value
        elif key == "day":
            n += _day(record) == value
        else:
            n += record[key] == value
    return n


def _best(records, cue, budget):
    """Full matches first, then records that could be full matches because a needed field
    is unknown, then the best partial matches. Certified only if all full and possible
    matches fit into the budget."""
    full = [r for r in records if _overlap(r, cue) == len(cue)]
    maybe = _minus(possible(records, **cue), full)
    taken = {r["id"] for r in full + maybe}
    partial = sorted((r for r in records if 0 < _overlap(r, cue) < len(cue) and r["id"] not in taken),
                     key=lambda r: (-_overlap(r, cue), r["seq"]))
    return (full + maybe + partial)[:budget], len(full) + len(maybe) <= budget


def _by_recency(rs):
    return sorted(rs, key=lambda r: (-(_day(r) if _day(r) is not None else 10 ** 9), r["seq"]))


def _recent(records, person, budget):
    """The records that could be the person's latest (memory.could_be_latest, including
    possible records with an unknown actor/partner) first, then the person's other dated
    records by recency. Certified if all records that could be the latest fit."""
    if not isinstance(person, str):
        return [], False
    mine = match(records, person=person)
    cands, _ = could_be_latest(mine, _minus(possible(records, person=person), mine))
    rest = _minus(_by_recency([r for r in mine if _day(r) is not None]), cands)
    return (_by_recency(cands) + rest)[:budget], len(cands) <= budget


def struct_select(records: list[dict], qtype: str, query: dict, k: int = K) -> tuple[list[dict], bool]:
    if qtype in ("object", "place", "person", "day"):
        got, ok = _best(records, query["cue"], k)
    elif qtype == "order":
        sides = [q for q in (query["a"], query["b"]) if q]
        got, ok = [], True
        for cue in sides:
            part, c = _best(records, cue, max(1, k // len(sides)) if sides else k)
            got += [r for r in part if r not in got]
            ok = ok and c
    elif qtype == "latest":
        got, ok = _recent(records, query["person"], k)
    elif qtype == "at_day":
        got, ok = _best(records, {"person": query["person"], "day": query["day"]}, k)
    elif qtype == "find":
        first, ok = _best(records, query["cue"], 1)
        full = [r for r in first if _overlap(r, query["cue"]) == len(query["cue"])]
        got = list(first)
        if full:
            more, c = _recent(records, full[0]["actor"], k - 1)
            got += [r for r in more if r not in got]
            ok = ok and c
    elif qtype == "act":
        # the record that could be the last event with the object (also one whose unknown
        # object could be it); certified only if there is at most one such record
        with_obj = match(records, obj=query["obj"])
        cands, _ = could_be_latest(with_obj, _minus(possible(records, obj=query["obj"]), with_obj))
        got = _by_recency(cands)[:1]
        ok = len(cands) <= 1
        if got:
            more, c = _recent(records, got[0]["actor"], k - 1)
            got += [r for r in more if r not in got]
            ok = ok and c
    else:
        got, ok = [], False
    return sorted(got, key=lambda r: r["seq"])[:k], ok


def _entities(qtype: str, query: dict) -> list[tuple[str, str]]:
    cues = [query["cue"]] if "cue" in query else [q for q in (query.get("a"), query.get("b")) if q]
    out = []
    for cue in cues:
        for key in ("person", "obj", "place"):
            if cue.get(key):
                out.append((key, cue[key]))
    if qtype in ("latest", "at_day"):
        out.append(("person", query["person"]))
    if qtype == "act":
        out.append(("obj", query["obj"]))
    return sorted(set(out))


def entity_note(qtype: str, query: dict, universe: list[dict]) -> str:
    """The index's knowledge about the question's names (the same knowledge the operators
    use to tell none_in_scope from no_observation)."""
    missing = [v for k, v in _entities(qtype, query) if not _known(universe, **{k: v})]
    if not missing:
        return "Every person, place and object named in the question occurs in memory."
    return "Never recorded in memory at all: " + ", ".join(missing) + "."


def reader_messages(question: str, notes: list[str], covered: bool, note: str | None,
                    answer_type: str) -> list[dict]:
    """Reader prompt with the SAME information and abstention contract as the operators:
    coverage of the selection for this question, the index's entity knowledge when the
    selection is covered, "none" only for a covered selection without the event and with
    every name known, "unknown" otherwise."""
    text = ("You answer one question from notes retrieved from your memory. Answer with only "
            f"{FORMAT_V1[answer_type]}, nothing else.")
    if answer_type == "choice":
        text += " If the notes do not settle it, answer with the single word: unknown."
    else:
        text += (" If the notes are complete for this question and none of them contains the event "
                 "asked about, answer with the single word: none - unless a name in the question was "
                 "never recorded in memory; then answer: unknown. If the notes are not complete and do "
                 "not settle the answer, or the question asks for the latest or last state and the notes "
                 "are not complete, answer with the single word: unknown.")
    coverage = ("Coverage: complete for this question (the whole memory was searched)." if covered
                else "Coverage: partial selection (other relevant notes may exist).")
    lines = [coverage] + ([note] if covered and note else [])
    body = "\n".join(notes) if notes else "(no notes)"
    user = "\n".join(lines) + f"\n\nMemory notes:\n{body}\n\nQuestion: {question}"
    return [{"role": "system", "content": text}, {"role": "user", "content": user}]


class _Cell:
    DIGEST_COVERS = ("store", "model", "encoder")
    EXPOSURE = None
    E1B = {"internal_replays": 0, "optimizer_steps": 0, "store_writes": 1}
    READER = False

    def __init__(self, model=None, store: EpisodeStore | None = None, encoder=regex_encode,
                 encoder_name: str = "regex"):
        if self.READER and model is None:
            raise ValueError("reader cells need a model")
        self.model = model if self.READER else None
        self.store = store if store is not None else EpisodeStore()
        self.encoder = encoder
        self.encoder_name = encoder_name

    def encode(self, text: str) -> None:
        encode_into(self.store, text, self.encoder, self.encoder_name)

    def state_digest(self) -> str:
        models = [m for m in (self.model, getattr(self.encoder, "model", None)) if m is not None]
        return self.store.content_digest() + "".join(m.weights_digest() for m in models)

    def select(self, text: str, qtype: str, query: dict, records: list[dict]) -> tuple[list[dict], bool]:
        raise NotImplementedError

    def explain(self, text: str, records: list[dict]) -> dict:
        """Deterministic replay of the selection (and the operator result) for one question
        over a given record set; used by the evaluator after the run, never while answering."""
        parsed = parse_question(text)
        if parsed is None:
            return {"selected": [], "covered": False, "entity_note": None, "result": None}
        got, covered = self.select(text, *parsed, records)
        out = {"selected": [r["id"] for r in got], "covered": covered,
               "entity_note": entity_note(*parsed, records) if covered else None, "result": None}
        if not self.READER:
            out["result"] = self._ops(got, parsed, covered, records).to_json()
        return out

    def _ops(self, got, parsed, covered, records):
        # `covered`: the selection is certified sufficient for THIS question (an index scan
        # over the whole store); the index then also knows which names occur at all
        return answer_query(got, *parsed, complete=covered, universe=records if covered else None)

    def reader_prompt(self, text: str, answer_type: str, records: list[dict]) -> list[dict]:
        parsed = parse_question(text)
        got, covered = self.select(text, *parsed, records)
        note = entity_note(*parsed, records) if covered else None
        return reader_messages(text, [r["text"] for r in got], covered, note, answer_type)

    def answer(self, text: str, answer_type: str) -> str:
        parsed = parse_question(text)
        if parsed is None:
            return "unknown"
        records = self.store._records
        if not self.READER:
            got, covered = self.select(text, *parsed, records)
            return self._ops(got, parsed, covered, records).answer()
        return self.model.generate(self.reader_prompt(text, answer_type, records))


class Lex3Reader(_Cell):
    NAME, READER = "lex3+reader", True

    def select(self, text, qtype, query, records):
        return bm25_top(records, text), False


class Lex3Ops(Lex3Reader):
    NAME, READER = "lex3+ops", False


class Struct3Reader(_Cell):
    NAME, READER = "struct3+reader", True

    def select(self, text, qtype, query, records):
        return struct_select(records, qtype, query)


class Struct3Ops(Struct3Reader):
    NAME, READER = "struct3+ops", False


class FullOps(_Cell):
    NAME = "full+ops"

    def select(self, text, qtype, query, records):
        return list(records), True


class Random3Ops(_Cell):
    NAME = "random3+ops"

    def select(self, text, qtype, query, records):
        order = sorted(records, key=lambda r: hashlib.sha256((text + r["id"]).encode()).hexdigest())
        return sorted(order[:K], key=lambda r: r["seq"]), False


CELLS = {c.NAME: c for c in (Lex3Reader, Lex3Ops, Struct3Reader, Struct3Ops, FullOps, Random3Ops)}


# ----------------------------------------------------------------- LM encoder
SLOT_QUESTIONS = {
    "event_day": ("On which day did the event in the note happen?", "day"),
    "actor": ("Who is the first person named in the note?", "person"),
    "partner": ("Who is the second person named in the note? If only one person is named, "
                "answer none.", "person"),
    "action": ("What did the first person do? Answer with the single verb from the note, in "
               "the past tense.", "action"),
    "object": ("Which object is named in the note?", "object"),
    "place": ("Which place is named in the note?", "place"),
}
SLOT_FORMAT = {"day": "the day number", "person": "the person's full name as written in the note",
               "action": "one verb in the past tense as written in the note",
               "object": "the object name as written in the note",
               "place": "the place name as written in the note"}


def _clean(raw: str, kind: str):
    text = raw.strip().split("\n", 1)[0].strip().strip(".").strip()
    low = text.lower()
    if low in ("none", "nobody", "no one", "nothing"):
        return None
    if kind == "day":
        m = re.fullmatch(r"(?:day\s*)?(\d+)", low)
        return int(m.group(1)) if m else INVALID
    if kind == "object" and low.startswith("the "):
        text = text[4:]
    if kind == "place" and low.startswith("at "):
        text = text[3:]
    if kind == "action" and low == "hidden":  # the one irregular participle of the templates
        text = "hid"
    return text


INVALID = object()
_NAME_SHAPE = {"person": re.compile(r"[A-Z][a-z]+ [A-Z][a-z]+"), "place": re.compile(r"[A-Z][a-z]+ [A-Z][a-z]+"),
               "object": re.compile(r"[a-z]+ [a-z]+"), "action": re.compile(r"[a-z]+")}


class LMEncoder:
    """Slot filling by single-detail questions. S1 qualified person, place, object and day;
    the second person and the action are measured here for the first time. Every slot is
    type-checked: an invalid or missing required value (no day number, a reply not shaped
    like a name, "none" for a slot every episode has) is listed in `invalid`, stored as
    None and declared unknown in the record; the raw reply is kept in `raw`. It never stops
    the run. A reply for the second person that repeats the first person is read as "no
    second person" (a declared normalisation, measured by the partner slot accuracy)."""

    def __init__(self, model):
        self.model = model
        self.raw: list[dict] = []       # telemetry per encoded episode, not memory
        self.invalid: list[list] = []   # invalid slots per encoded episode

    def __call__(self, text: str) -> dict:
        raw = {}
        for slot, (question, kind) in SLOT_QUESTIONS.items():
            msgs = [{"role": "system", "content": "You read one note and answer one question "
                     f"about it. Answer with only {SLOT_FORMAT[kind]}, nothing else."},
                    {"role": "user", "content": f"Note:\n{text}\n\nQuestion: {question}"}]
            raw[slot] = self.model.generate(msgs)
        content, bad = postprocess(raw)
        self.raw.append(raw)
        self.invalid.append(bad)
        return content, bad


def postprocess(raw: dict) -> tuple[dict, list]:
    """Raw slot replies -> (record content, invalid slots); every invalid slot is None in
    the content and declared unknown in the record. Deterministic, so the collector can
    re-derive both from the recorded raw replies."""
    out, bad = {}, []
    for slot, (_, kind) in SLOT_QUESTIONS.items():
        value = _clean(raw[slot], kind)
        if value is INVALID:
            bad.append(slot)
            value = None
        elif value is not None and kind in _NAME_SHAPE and not _NAME_SHAPE[kind].fullmatch(value):
            bad.append(slot)
            value = None  # the raw reply stays in the encoder's raw record
        out[slot] = value
    for slot in ("actor", "action", "object", "place", "event_day"):  # required in every episode
        if out[slot] is None:
            bad.append(slot)
    if out["partner"] == out["actor"]:
        out["partner"] = None
    return {k: out[k] for k in FIELDS}, sorted(set(bad))


def diagnose(cell, rows: list[dict], world: dict, questions: dict) -> None:
    """Per answer row: deterministic replay of the selection, coverage, entity note and
    operator result on the record set of that test point, plus evaluator-only gold support.
    Used by the job after the run and by the collector to recompute every field."""
    texts = {e["episode_id"]: e["text"] for e in world["episodes"]}
    by_qid = {q["qid"]: q["text"] for q in questions["public"]["final"]}
    n_early = sum(e["block"] == "early" for e in world["episodes"])
    for row in rows:
        recs = cell.store._records if row["phase"] == "final" else [r for r in cell.store._records
                                                                      if r["seq"] < n_early]
        diag = cell.explain(by_qid[row["qid"]], recs)
        chosen = {r["text"] for r in recs if r["id"] in set(diag["selected"])}
        targets = questions["gold"][row["qid"]]["targets"]
        diag["gold_support_selected"] = all(texts[t] in chosen for t in targets) if targets else None
        row["diag"] = diag


def slot_accuracy(pairs: list[tuple[dict, dict]]) -> dict:
    """pairs: (lm record content, regex truth) -> share correct per slot and all slots."""
    acc = {s: sum(a[s] == t[s] for a, t in pairs) / len(pairs) for s in FIELDS}
    acc["all_slots"] = sum(all(a[s] == t[s] for s in FIELDS) for a, t in pairs) / len(pairs)
    return acc


__all__ = ["CELLS", "LMEncoder", "Result", "bm25_top", "match", "slot_accuracy", "struct_select"]
