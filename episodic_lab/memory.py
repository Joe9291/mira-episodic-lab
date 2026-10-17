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

    def __init__(self, path: str | os.PathLike | None = None, stream: str = "agent",
                 expect: dict | None = None):
        """`expect` = a seal kept OUTSIDE the record chain ({"count", "head"}); with it, a
        store whose last records were cut off is refused as well."""
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
        if expect is not None and self.seal() != expect:
            raise StoreCorrupted(f"seal mismatch: {self.seal()} != {expect}")

    def seal(self) -> dict:
        return {"count": len(self._records),
                "head": self._records[-1]["hash"] if self._records else GENESIS}

    def content_digest(self) -> str:
        """Digest of the actual record contents (not of the stored hashes), so any change
        of a record in working memory changes it."""
        return hashlib.sha256(json.dumps(self._records, sort_keys=True).encode()).hexdigest()

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
# Every operator takes the record set it may use and whether that set is the COMPLETE
# store (`complete`). Statuses:
#   ok                    a value supported by the records used
#   none_in_scope         complete scope; the cue's entities are known, the combination never occurred
#   no_observation        complete scope; one of the cue's entities was never recorded
#   ambiguous             several records with different answers
#   insufficient_evidence incomplete scope; nothing (or no unique latest/negative) can be concluded
# Global statements (a negative, "latest", "last handler") require a complete scope.
STATUSES = ("ok", "none_in_scope", "no_observation", "ambiguous", "insufficient_evidence")


@dataclass
class Result:
    value: str | None
    status: str
    ids: list = field(default_factory=list)
    trace: list = field(default_factory=list)

    def answer(self) -> str:
        """Closed-benchmark answer: a value, "none" only for none_in_scope, else "unknown"."""
        if self.status == "ok":
            return self.value
        return "none" if self.status == "none_in_scope" else "unknown"

    def to_json(self) -> dict:
        return {"value": self.value, "status": self.status, "ids": list(self.ids),
                "trace": [[op, arg, list(ids)] for op, arg, ids in self.trace]}


def _people(r):
    return {r["actor"]} | ({r["partner"]} if r["partner"] else set())


def _day(r):
    """Event day if it is a valid integer, else None (an encoder error stays a datum)."""
    d = r.get("event_day")
    return d if isinstance(d, int) and not isinstance(d, bool) else None


# A field is UNKNOWN if the encoder declared it so (record extra "unknown", e.g. an
# invalid or missing LM slot; its value is then None) or if a field every episode has
# (actor, action, place, a valid integer day) is missing. A missing partner or object
# without that declaration means "none in this episode" (legitimate in the templates
# for the partner, in the round 3.3 environment also for the object).
ALWAYS_PRESENT = ("actor", "action", "place", "event_day")


def unknown(r, f) -> bool:
    if f in ((r.get("extra") or {}).get("unknown") or ()):
        return True
    if f == "event_day":
        return _day(r) is None
    return f in ALWAYS_PRESENT and r[f] is None


def match(records, person=None, action=None, obj=None, place=None, day=None):
    return [r for r in records
            if (person is None or person in _people(r)) and (action is None or r["action"] == action)
            and (obj is None or r["object"] == obj) and (place is None or r["place"] == place)
            and (day is None or _day(r) == day)]


def possible(records, person=None, action=None, obj=None, place=None, day=None):
    """Records that match the cue OR could match it because a needed field is unknown
    (see `unknown`): an unknown value is never evidence of absence. A person could be
    the actor or the partner of a record in which either is unknown."""
    def ok(r, value, f):
        return value is None or unknown(r, f) or r[f] == value
    return [r for r in records
            if (person is None or person in _people(r) or unknown(r, "actor") or unknown(r, "partner"))
            and ok(r, action, "action") and ok(r, obj, "object") and ok(r, place, "place")
            and (day is None or unknown(r, "event_day") or _day(r) == day)]


def _ids(rs):
    return [r["id"] for r in rs]


def _minus(rs, exclude):
    ids = set(_ids(exclude))
    return [r for r in rs if r["id"] not in ids]


def could_be_latest(exact, maybe):
    """Records that could be the latest one about an entity: the exact records of the
    latest known day, exact undated records, and possible records (an unknown field could
    make them about the entity) that are undated or not earlier than that day. Records
    outside this set cannot change a latest-state answer."""
    dated = [r for r in exact if _day(r) is not None]
    if not dated:
        return list(exact) + list(maybe), None
    top = max(_day(r) for r in dated)
    return ([r for r in exact if _day(r) in (top, None)]
            + [r for r in maybe if _day(r) is None or _day(r) >= top]), top


def _known(records, person=None, obj=None, place=None, **_):
    people = set().union(*(_people(r) for r in records)) if records else set()
    return ((person is None or person in people)
            and (obj is None or any(r["object"] == obj for r in records))
            and (place is None or any(r["place"] == place for r in records)))


def _negative(records, cue, complete, universe=None):
    """Negative status. `universe` = the whole store when the selection was certified by
    an index scan over it (entity knowledge then comes from the index, not the subset)."""
    if not complete:
        return "insufficient_evidence"
    return "none_in_scope" if _known(universe if universe is not None else records, **cue) else "no_observation"


def _ok(value, ids, trace) -> Result:
    """Every ok result carries a valid answer value (a non-empty string); a missing value
    (an encoder that gave none for a required slot) is uncertainty, never an answer."""
    if isinstance(value, str) and value:
        return Result(value, "ok", ids, trace)
    return Result(None, "ambiguous", ids, trace)


def find(records, cue: dict, want: str, complete: bool = True, universe=None) -> Result:
    hits = match(records, **cue)
    maybe = _minus(possible(records, **cue), hits)
    trace = [("find", dict(cue), [h["id"] for h in hits + maybe])]
    if not hits:
        if maybe:  # a record with an unknown field could be the event
            return Result(None, "insufficient_evidence", [r["id"] for r in maybe], trace)
        return Result(None, _negative(records, cue, complete, universe), [], trace)
    if want == "day":
        values = {str(_day(h)) if _day(h) is not None else None for h in hits + maybe}
    else:
        values = {h["actor"] if want == "person" else h[want] for h in hits + maybe}
    if len(values) != 1:
        return Result(None, "ambiguous", [h["id"] for h in hits + maybe], trace)
    return _ok(values.pop(), [h["id"] for h in hits], trace)


def latest(records, person: str, complete: bool = True) -> Result:
    """Latest place of a person. Every record that could be the latest one about the
    person (an undated record of the person, or a record whose unknown actor/partner
    could be the person and that is not earlier) must agree on the place."""
    hits = match(records, person=person)
    maybe = _minus(possible(records, person=person), hits)
    trace = [("latest", person, _ids(hits + maybe))]
    if not complete:
        return Result(None, "insufficient_evidence", _ids(hits + maybe), trace)
    if not hits:
        return Result(None, "insufficient_evidence" if maybe else "no_observation", _ids(maybe), trace)
    cands, top = could_be_latest(hits, maybe)
    if top is None:
        return Result(None, "ambiguous", _ids(cands), trace)
    places = {r["place"] for r in cands}
    if len(places) != 1:
        return Result(None, "ambiguous", _ids(cands), trace)
    return _ok(places.pop(), [h["id"] for h in hits if _day(h) == top], trace)


def state_at(records, person: str, day: int, complete: bool = True, universe=None) -> Result:
    """Place of a person on a day. Possible records (undated records of the person, or
    records of that day or undated whose unknown actor/partner could be the person) could
    be from that day: without an exact hit they give insufficient_evidence, with one they
    must agree on the place."""
    hits = match(records, person=person, day=day)
    maybe = _minus(possible(records, person=person, day=day), hits)
    trace = [("state_at", [person, day], _ids(hits + maybe))]
    if not hits:
        if maybe:
            return Result(None, "insufficient_evidence", _ids(maybe), trace)
        return Result(None, _negative(records, {"person": person}, complete, universe), [], trace)
    places = {r["place"] for r in hits + maybe}
    if len(places) != 1:
        return Result(None, "ambiguous", _ids(hits + maybe), trace)
    return _ok(places.pop(), _ids(hits), trace)


def compare_time(records, cue_a: dict, cue_b: dict, complete: bool = True, universe=None) -> Result:
    """Which of two unique events happened first. A second exact match makes a side
    ambiguous; so does a second POSSIBLE match (if it were the event, the side would not
    be unique), whatever its day."""
    a, b = match(records, **cue_a), match(records, **cue_b)
    pa, pb = possible(records, **cue_a), possible(records, **cue_b)
    ids = _ids(a + b)
    trace = [("compare_time", [dict(cue_a), dict(cue_b)], _ids(pa + _minus(pb, pa)))]
    if len(a) > 1 or len(b) > 1:
        return Result(None, "ambiguous", ids, trace)
    if len(pa) > 1 or len(pb) > 1:  # before the negative: a side that may not be unique
        return Result(None, "ambiguous", _ids(pa + _minus(pb, pa)), trace)
    if not a or not b:
        missing = cue_a if not a else cue_b
        if possible(records, **missing):
            return Result(None, "insufficient_evidence", ids, trace)
        return Result(None, _negative(records, missing, complete, universe), ids, trace)
    da, db = _day(a[0]), _day(b[0])
    if da is None or db is None or da == db:
        return Result(None, "ambiguous", ids, trace)
    return Result("A" if da < db else "B", "ok", ids, trace)


def link_latest(records, cue: dict, complete: bool = True, universe=None) -> Result:
    """E7 "find": the person of the unique event matching `cue`, then that person's latest place."""
    first = find(records, cue, "person", complete, universe)
    if first.status != "ok":
        return Result(None, first.status, first.ids, first.trace)
    nxt = latest(records, first.value, complete)
    return Result(nxt.value, nxt.status, first.ids + nxt.ids, first.trace + nxt.trace)


def last_handler_latest(records, obj: str, complete: bool = True) -> Result:
    """E7 "act": the actor of the latest event with the object, then that actor's latest
    place. Every record that could be the latest event with the object (an undated one, or
    one whose unknown object could be it and that is not earlier) must have the same,
    known actor."""
    with_obj = match(records, obj=obj)
    maybe = _minus(possible(records, obj=obj), with_obj)
    trace = [("last_handler", obj, _ids(with_obj + maybe))]
    if not complete:
        return Result(None, "insufficient_evidence", _ids(with_obj + maybe), trace)
    if not with_obj:
        return Result(None, "insufficient_evidence" if maybe else "no_observation", _ids(maybe), trace)
    cands, top = could_be_latest(with_obj, maybe)
    holders = {r["actor"] for r in cands}
    if top is None or len(holders) != 1 or not isinstance(next(iter(holders)), str):
        return Result(None, "ambiguous", _ids(cands), trace)
    nxt = latest(records, holders.pop(), complete)
    return Result(nxt.value, nxt.status, _ids(cands) + nxt.ids, trace + nxt.trace)


def misbind(records: list[dict], seed: str) -> list[dict]:
    """Control store: places and objects permuted across records (marginals kept)."""
    import random
    rng = random.Random(seed)
    places, objects = [r["place"] for r in records], [r["object"] for r in records]
    rng.shuffle(places)
    rng.shuffle(objects)
    return [dict(r, place=pl, object=ob) for r, pl, ob in zip(records, places, objects)]


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


def answer_query(records, qtype: str, query: dict, complete: bool = True, universe=None) -> Result:
    if qtype in ("object", "place", "person", "day"):
        return find(records, query["cue"], qtype, complete, universe)
    if qtype == "order":
        if query["a"] is None or query["b"] is None:
            return Result(None, "no_observation")
        return compare_time(records, query["a"], query["b"], complete, universe)
    if qtype == "latest":
        return latest(records, query["person"], complete)
    if qtype == "at_day":
        return state_at(records, query["person"], query["day"], complete, universe)
    if qtype == "act":
        return last_handler_latest(records, query["obj"], complete)
    if qtype == "find":
        return link_latest(records, query["cue"], complete, universe)
    raise ValueError(qtype)


def encode_into(store: EpisodeStore, text: str, encoder, encoder_name: str) -> dict:
    """An encoder returns the record content, or (content, unknown slots); declared
    unknown slots are kept in the record (extra "unknown") and read by `unknown`."""
    out = encoder(text)
    content, unk = out if isinstance(out, tuple) else (out, [])
    return store.append(text, content, encoder=encoder_name, extra={"unknown": list(unk)} if unk else None)


class MemoryAgent:
    """struct+ops cell: encodes every presented episode into the store, answers from it."""
    DIGEST_COVERS = ("store",)

    def __init__(self, store: EpisodeStore, encoder=regex_encode, encoder_name: str = "regex"):
        self.store = store
        self.encoder = encoder
        self.encoder_name = encoder_name

    def encode(self, text: str) -> None:
        encode_into(self.store, text, self.encoder, self.encoder_name)

    def state_digest(self) -> str:
        return self.store.content_digest()

    def answer(self, text: str, answer_type: str | None = None) -> str:
        parsed = parse_question(text)
        if parsed is None:
            return "unknown"
        return answer_query(self.store._records, *parsed).answer()
