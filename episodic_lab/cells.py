"""Round 3.2 comparison cells (docs/ROUND_3_2.md section 4) and the LM encoder.

All cells share the store (episodes appended once, in presentation order) and the
template question parser. They differ in retrieval (lexical BM25 over the raw texts vs
conjunctive match over the records) and in processing (the LM reads the retrieved notes
vs explicit operators over the retrieved records). Every cell keeps its whole state in
the store; answering never changes it (checked by the runner's fingerprint).
"""
from __future__ import annotations

import math
import re

from .arms import build_messages
from .memory import (FIELDS, EpisodeStore, Result, answer_query, match, parse_question,
                     regex_encode)

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
    return [records[i] for _, i in sorted(scores)[:k]]


def _cue_features(qtype: str, query: dict) -> list[dict]:
    """The partial records a structured retrieval looks for (one per event in the query)."""
    if qtype in ("object", "place", "person", "day", "find"):
        return [query["cue"]]
    if qtype == "order":
        return [q for q in (query["a"], query["b"]) if q]
    if qtype in ("latest",):
        return [{"person": query["person"]}]
    if qtype == "at_day":
        return [{"person": query["person"], "day": query["day"]}]
    if qtype == "act":
        return [{"obj": query["obj"]}]
    return []


def _overlap(record: dict, cue: dict) -> int:
    n = 0
    for key, value in cue.items():
        if key == "person":
            n += value in (record["actor"], record["partner"])
        elif key == "obj":
            n += record["object"] == value
        elif key == "day":
            n += record["event_day"] == value
        else:
            n += record[key] == value
    return n


def struct_top(records: list[dict], qtype: str, query: dict, k: int = K) -> list[dict]:
    """Pattern completion: per event in the query, the records matching the most cue
    features (at least one), ties by record order; up to k in total."""
    chosen = []
    for cue in _cue_features(qtype, query):
        ranked = sorted(((-_overlap(r, cue), r["seq"]) for r in records if _overlap(r, cue) > 0))
        per = max(1, k // max(1, len(_cue_features(qtype, query))))
        for _, seq in ranked[:per]:
            if records[seq] not in chosen:
                chosen.append(records[seq])
    return sorted(chosen, key=lambda r: r["seq"])[:k]


class _Cell:
    DIGEST_COVERS = ("store", "model", "encoder")
    EXPOSURE = None
    E1B = {"internal_replays": 0, "optimizer_steps": 0, "store_writes": 1}

    def __init__(self, model=None, store: EpisodeStore | None = None, encoder=regex_encode,
                 encoder_name: str = "regex"):
        self.model = model
        self.store = store if store is not None else EpisodeStore()
        self.encoder = encoder
        self.encoder_name = encoder_name

    def encode(self, text: str) -> None:
        self.store.append(text, self.encoder(text), encoder=self.encoder_name)

    def state_digest(self) -> str:
        recs = self.store._records
        models = [m for m in (self.model, getattr(self.encoder, "model", None)) if m is not None]
        return (recs[-1]["hash"] if recs else "") + "".join(m.weights_digest() for m in models)

    def retrieve(self, text: str, qtype: str, query: dict, records: list[dict]) -> list[dict]:
        raise NotImplementedError

    def answer(self, text: str, answer_type: str) -> str:
        parsed = parse_question(text)
        if parsed is None:
            return "unknown"
        qtype, query = parsed
        records = self.store._records
        got = self.retrieve(text, qtype, query, records)
        if self.model is None:  # explicit operators over the retrieved records only
            return answer_query(got, qtype, query).answer()
        return self.model.generate(build_messages(text, [r["text"] for r in got], answer_type, STYLE))


class LexReader(_Cell):
    NAME = "lex+reader"

    def retrieve(self, text, qtype, query, records):
        return sorted(bm25_top(records, text), key=lambda r: r["seq"])


class StructReader(_Cell):
    NAME = "struct+reader"

    def retrieve(self, text, qtype, query, records):
        return struct_top(records, qtype, query)


class LexOps(LexReader):
    NAME = "lex+ops"

    def __init__(self, store=None, encoder=regex_encode, encoder_name="regex"):
        super().__init__(None, store, encoder, encoder_name)


class StructOps(_Cell):
    """The full system: operators over ALL records (conjunctive matching is itself the
    structured retrieval)."""
    NAME = "struct+ops"

    def __init__(self, store=None, encoder=regex_encode, encoder_name="regex"):
        super().__init__(None, store, encoder, encoder_name)

    def retrieve(self, text, qtype, query, records):
        return records


class RandomOps(StructOps):
    """Control: K records drawn by a fixed hash of the question, operators over them."""
    NAME = "random+ops"

    def retrieve(self, text, qtype, query, records):
        import hashlib
        order = sorted(records, key=lambda r: hashlib.sha256((text + r["id"]).encode()).hexdigest())
        return sorted(order[:K], key=lambda r: r["seq"])


CELLS = {c.NAME: c for c in (LexReader, StructReader, LexOps, StructOps, RandomOps)}


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
        return int(m.group(1)) if m else text
    if kind == "object" and low.startswith("the "):
        text = text[4:]
    if kind == "place" and low.startswith("at "):
        text = text[3:]
    return text


class LMEncoder:
    """Slot filling by single-detail questions (the sub-skill round 3.1 found reliable)."""

    def __init__(self, model):
        self.model = model
        self.raw: list[dict] = []   # telemetry of the last encoding, not memory

    def __call__(self, text: str) -> dict:
        out, raw = {}, {}
        for slot, (question, kind) in SLOT_QUESTIONS.items():
            msgs = [{"role": "system", "content": "You read one note and answer one question "
                     f"about it. Answer with only {SLOT_FORMAT[kind]}, nothing else."},
                    {"role": "user", "content": f"Note:\n{text}\n\nQuestion: {question}"}]
            raw[slot] = self.model.generate(msgs)
            out[slot] = _clean(raw[slot], kind)
        self.raw.append(raw)
        if out["partner"] == out["actor"]:
            out["partner"] = None
        return {k: out[k] for k in FIELDS}


def slot_accuracy(pairs: list[tuple[dict, dict]]) -> dict:
    """pairs: (lm record content, regex truth) -> share correct per slot and all slots."""
    acc = {s: sum(a[s] == t[s] for a, t in pairs) / len(pairs) for s in FIELDS}
    acc["all_slots"] = sum(all(a[s] == t[s] for s in FIELDS) for a, t in pairs) / len(pairs)
    return acc


__all__ = ["CELLS", "LMEncoder", "Result", "bm25_top", "match", "slot_accuracy", "struct_top"]
