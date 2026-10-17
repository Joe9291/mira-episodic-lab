"""Round 3.2 agent memory (docs/ROUND_3_2.md), evolved from S0.

Store: an append-only JSON-lines file, one record per experienced episode, written once
and flushed, chained by SHA-256 so that any changed, removed or reordered record is
detected on load. Current state is always derived from the records at query time.

Operators answer structured queries over the records and return the value, a status and
the trace (episode ids, operation). Negative results are three-valued: "none_in_scope"
(the cue's people, objects and places are known, but this combination never occurred),
"no_observation" (nothing was ever recorded about one of the cue's entities) and
"ambiguous" (several records match with different answers).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .questions import BASE, PARA
from .symbolic import EPISODE_PATTERNS, PAST, _template_regex

STORE_SCHEMA = "episodic_lab.memory_record.v1"
FIELDS = ("actor", "partner", "action", "object", "place", "event_day")
SOURCE_KINDS = ("observed", "own_action", "reported", "inferred")
GENESIS = "0" * 64


class StoreCorrupted(RuntimeError):
    pass


def _digest(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class EpisodeStore:
    """Append-only episodic store backed by one file (or memory only if path is None)."""

    def __init__(self, path: str | os.PathLike | None = None, stream: str = "agent"):
        self.path = Path(path) if path is not None else None
        self.stream = stream
        self._records: list[dict] = []
        if self.path is not None and self.path.exists():
            prev = GENESIS
            for n, line in enumerate(self.path.read_text(encoding="utf-8").splitlines()):
                rec = json.loads(line)
                if rec.get("prev") != prev or rec.get("seq") != n or _digest(rec) != rec.get("hash"):
                    raise StoreCorrupted(f"record {n}")
                prev = rec["hash"]
                self._records.append(rec)

    @property
    def records(self) -> list[dict]:
        return [dict(r) for r in self._records]

    def append(self, text: str, content: dict, source: dict | None = None,
               encoder: str = "regex", relations: list | None = None, extra: dict | None = None) -> dict:
        source = source or {"kind": "observed", "by": None}
        if source.get("kind") not in SOURCE_KINDS:
            raise ValueError("unknown source kind")
        if set(content) != set(FIELDS):
            raise ValueError(f"content needs exactly {FIELDS}")
        prev = self._records[-1]["hash"] if self._records else GENESIS
        rec = {"schema": STORE_SCHEMA, "seq": len(self._records), "stream": self.stream,
               "id": "m" + hashlib.sha256((prev + text).encode()).hexdigest()[:12],
               **content, "source": source, "text": text, "relations": relations or [],
               "encoder": encoder, "extra": extra or {}, "prev": prev}
        rec["hash"] = _digest(rec)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        self._records.append(rec)
        return dict(rec)


# ----------------------------------------------------------------- encoders
def regex_encode(text: str) -> dict:
    """S0's template parser (control encoder)."""
    for pattern in EPISODE_PATTERNS:
        m = re.fullmatch(pattern, text)
        if m:
            g = m.groupdict()
            return {"actor": g["actor"], "partner": g["partner"],
                    "action": "hid" if g["action"] == "hidden" else g["action"],
                    "object": g["object"], "place": g["place"], "event_day": int(g["day"])}
    raise ValueError(f"unparsed episode: {text}")


# ----------------------------------------------------------------- operators
@dataclass
class Result:
    value: str | None
    status: str                     # "ok", "none_in_scope", "no_observation", "ambiguous"
    ids: list = field(default_factory=list)
    trace: list = field(default_factory=list)

    def answer(self) -> str:
        """Closed-benchmark answer: a value, or "none" only for none_in_scope."""
        if self.status == "ok":
            return self.value
        return "none" if self.status == "none_in_scope" else "unknown"


def _people(r):
    return {r["actor"]} | ({r["partner"]} if r["partner"] else set())


def match(records, person=None, action=None, obj=None, place=None, day=None):
    return [r for r in records
            if (person is None or person in _people(r)) and (action is None or r["action"] == action)
            and (obj is None or r["object"] == obj) and (place is None or r["place"] == place)
            and (day is None or r["event_day"] == day)]


def _known(records, person=None, obj=None, place=None, **_):
    people = set().union(*(_people(r) for r in records)) if records else set()
    return ((person is None or person in people)
            and (obj is None or any(r["object"] == obj for r in records))
            and (place is None or any(r["place"] == place for r in records)))


def find(records, cue: dict, want: str) -> Result:
    hits = match(records, **cue)
    trace = [("find", dict(cue), [h["id"] for h in hits])]
    if not hits:
        return Result(None, "none_in_scope" if _known(records, **cue) else "no_observation", [], trace)
    values = {(h["actor"] if want == "person" else str(h["event_day"]) if want == "day" else h[want])
              for h in hits}
    if len(values) != 1:
        return Result(None, "ambiguous", [h["id"] for h in hits], trace)
    return Result(values.pop(), "ok", [h["id"] for h in hits], trace)


def latest(records, person: str) -> Result:
    hits = match(records, person=person)
    trace = [("latest", person, [h["id"] for h in hits])]
    if not hits:
        return Result(None, "no_observation", [], trace)
    last = max(hits, key=lambda r: r["event_day"])
    return Result(last["place"], "ok", [last["id"]], trace)


def state_at(records, person: str, day: int) -> Result:
    if not match(records, person=person):
        return Result(None, "no_observation", [], [("state_at", (person, day), [])])
    hits = match(records, person=person, day=day)
    trace = [("state_at", (person, day), [h["id"] for h in hits])]
    if not hits:
        return Result(None, "none_in_scope", [], trace)
    places = {h["place"] for h in hits}
    if len(places) != 1:
        return Result(None, "ambiguous", [h["id"] for h in hits], trace)
    return Result(places.pop(), "ok", [h["id"] for h in hits], trace)


def compare_time(records, cue_a: dict, cue_b: dict) -> Result:
    a, b = match(records, **cue_a), match(records, **cue_b)
    trace = [("compare_time", (dict(cue_a), dict(cue_b)), [r["id"] for r in a + b])]
    if len(a) != 1 or len(b) != 1:
        status = "ambiguous" if (len(a) > 1 or len(b) > 1) else "none_in_scope"
        return Result(None, status, [r["id"] for r in a + b], trace)
    if a[0]["event_day"] == b[0]["event_day"]:
        return Result(None, "ambiguous", [a[0]["id"], b[0]["id"]], trace)
    return Result("A" if a[0]["event_day"] < b[0]["event_day"] else "B", "ok",
                  [a[0]["id"], b[0]["id"]], trace)


def link_latest(records, cue: dict, holder: str = "actor") -> Result:
    """E7: the person of the unique event matching `cue`, then that person's latest place."""
    first = find(records, cue, "person")
    if first.status != "ok":
        return Result(None, first.status, first.ids, first.trace)
    nxt = latest(records, first.value)
    return Result(nxt.value, nxt.status, first.ids + nxt.ids, first.trace + nxt.trace)


def last_handler_latest(records, obj: str) -> Result:
    """E7 "act": the actor of the latest event with the object, then that actor's latest place."""
    with_obj = match(records, obj=obj)
    trace = [("last_handler", obj, [r["id"] for r in with_obj])]
    if not with_obj:
        return Result(None, "no_observation", [], trace)
    holder = max(with_obj, key=lambda r: r["event_day"])["actor"]
    nxt = latest(records, holder)
    return Result(nxt.value, nxt.status, [r["id"] for r in with_obj] + nxt.ids, trace + nxt.trace)


# ----------------------------------------------------------------- question parsing (shared)
_EVENT = re.compile(r"(?P<person>[A-Z][a-z]+ [A-Z][a-z]+) (?P<action>\w+) the (?P<obj>[a-z]+ [a-z]+) "
                    r"at (?P<place>[A-Z][a-z]+ [A-Z][a-z]+)\.")


def parse_question(text: str) -> tuple[str, dict] | None:
    """Template question -> (qtype, structured query); shared by every round 3.2 cell."""
    for qtype, templates in PARA.items():
        for template in templates:
            m = re.fullmatch(_template_regex(template), text)
            if not m:
                continue
            g = m.groupdict()
            action = PAST.get(g.get("action"), g.get("past"))
            if qtype in ("object", "place", "person", "day"):
                cue = {k: v for k, v in {"person": g.get("person"), "action": action,
                                         "place": g.get("place"), "obj": g.get("object")}.items()
                       if v is not None}
                return qtype, {"cue": cue}
            if qtype == "order":
                sides = []
                for side in ("a", "b"):
                    e = _EVENT.fullmatch(g[side])
                    sides.append(dict(e.groupdict()) if e else None)
                return qtype, {"a": sides[0], "b": sides[1]}
            if qtype == "latest":
                return qtype, {"person": g["person"]}
            if qtype == "at_day":
                return qtype, {"person": g["person"], "day": int(g["day"])}
            if qtype == "act":
                return qtype, {"obj": g["object"]}
            if qtype == "find":
                return qtype, {"cue": {"action": g["past"], "place": g["place"], "obj": g["object"]}}
    return None


def answer_query(records, qtype: str, query: dict) -> Result:
    if qtype in ("object", "place", "person", "day"):
        return find(records, query["cue"], qtype)
    if qtype == "order":
        if query["a"] is None or query["b"] is None:
            return Result(None, "no_observation")
        return compare_time(records, query["a"], query["b"])
    if qtype == "latest":
        return latest(records, query["person"])
    if qtype == "at_day":
        return state_at(records, query["person"], query["day"])
    if qtype == "act":
        return last_handler_latest(records, query["obj"])
    if qtype == "find":
        return link_latest(records, query["cue"])
    raise ValueError(qtype)


class MemoryAgent:
    """struct+ops cell: encodes every presented episode into the store, answers from it."""
    DIGEST_COVERS = ("store",)

    def __init__(self, store: EpisodeStore, encoder=regex_encode, encoder_name: str = "regex"):
        self.store = store
        self.encoder = encoder
        self.encoder_name = encoder_name

    def encode(self, text: str) -> None:
        self.store.append(text, self.encoder(text), encoder=self.encoder_name)

    def state_digest(self) -> str:
        recs = self.store._records
        return recs[-1]["hash"] if recs else GENESIS

    def answer(self, text: str, answer_type: str | None = None) -> str:
        parsed = parse_question(text)
        if parsed is None:
            return "unknown"
        return answer_query(self.store._records, *parsed).answer()
