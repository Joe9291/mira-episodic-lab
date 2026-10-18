"""Round 3.4 step 1 systems (docs/ROUND_3_4.md): the episodic agent (round 3.3 store and
template encoder, history operators) and the current-state-only baseline.

Both systems receive the goal only as decision text and parse it; neither sees the
environment's truth. Without a supported answer both explore (first listed place).
"""
from __future__ import annotations

import hashlib
import json
import re

from .env import PLACING, SELF, env_encode
from .memory import Result, _day, _minus, _ok, match, possible, unknown

_GOALS = [
    (re.compile(r"Find the (?P<t>[a-z]+ [a-z]+)\."), "object", "current"),
    (re.compile(r"Go to where the (?P<t>[a-z]+ [a-z]+) was first placed\."), "object", "first"),
    (re.compile(r"Go to where the (?P<t>[a-z]+ [a-z]+) was before it was last placed\."), "object", "previous"),
    (re.compile(r"Find (?P<t>[A-Z][a-z]+ [A-Z][a-z]+)\."), "person", "current"),
    (re.compile(r"Go to where you first saw (?P<t>[A-Z][a-z]+ [A-Z][a-z]+)\."), "person", "first"),
    (re.compile(r"Go to where you saw (?P<t>[A-Z][a-z]+ [A-Z][a-z]+) before you last saw them\."), "person", "previous"),
]


def parse_goal(goal: str):
    """Goal text -> (target kind, target, which) or None."""
    for pattern, kind, which in _GOALS:
        m = pattern.fullmatch(goal)
        if m:
            return kind, m.group("t"), which
    return None


# ----------------------------------------------------------------- episodic agent
def target_records(records, kind: str, target: str) -> list:
    if kind == "object":
        return [r for r in match(records, obj=target) if r["action"] in PLACING]
    return match(records, person=target)


def possible_target_records(records, kind: str, target: str) -> list:
    """Records that are not certainly about the target but could be, because a field
    that decides it is unknown (round 3.2 v4 semantics: declared unknowns, missing
    always-present fields): an unknown object or action for an object, an unknown actor
    or partner for a person."""
    if kind == "object":
        cand = [r for r in possible(records, obj=target) if r["action"] in PLACING or unknown(r, "action")]
    else:
        cand = possible(records, person=target)
    return _minus(cand, target_records(records, kind, target))


def history_place(records, kind: str, target: str, which: str) -> Result:
    """The target's episodes ordered by event day; the latest, the first or the one
    before the latest. An undated record, or two records on one day at the asked position
    (for "previous": at the latest or the one before), make the answer ambiguous. A possible record (one that could be about the target, see
    possible_target_records) blocks the answer whenever it could take the asked position
    or tie with it: undated, or not earlier than the latest / not later than the first /
    not earlier than the one before the latest. Without any exact record but with
    possible ones the evidence is insufficient."""
    hits = target_records(records, kind, target)
    maybe = possible_target_records(records, kind, target)
    trace = [("history", [kind, target, which], [r["id"] for r in hits + maybe])]
    if not hits:
        return Result(None, "insufficient_evidence" if maybe else "no_observation", [r["id"] for r in maybe], trace)
    days = [_day(r) for r in hits]
    if None in days:
        return Result(None, "ambiguous", [r["id"] for r in hits], trace)
    ordered = sorted(hits, key=_day)
    if which == "previous" and len(ordered) < 2:
        status = "insufficient_evidence" if maybe else "no_observation"
        return Result(None, status, [r["id"] for r in ordered + maybe], trace)
    pos = {"current": -1, "first": 0, "previous": -2}[which]
    chosen = ordered[pos]
    # a tie decides only where it touches the asked position (latest; first; latest and
    # the one before it)
    needed = {"current": [-1], "first": [0], "previous": [-1, -2]}[which]
    if any(days.count(_day(ordered[i])) > 1 for i in needed):
        return Result(None, "ambiguous", [r["id"] for r in hits], trace)
    border = _day(chosen)

    def blocks(r):
        d = _day(r)
        if d is None:
            return True
        return d <= border if which == "first" else d >= border
    blocking = [r for r in maybe if blocks(r)]
    if blocking:
        return Result(None, "ambiguous", [chosen["id"]] + [r["id"] for r in blocking], trace)
    return _ok(chosen["place"], [chosen["id"]], trace)


def decide(records, decision: dict) -> dict:
    parsed = parse_goal(decision["goal"])
    result = history_place(records, *parsed) if parsed else Result(None, "no_observation")
    return _act(result, decision)


def _act(result: Result, decision: dict) -> dict:
    if result.status == "ok" and result.value in decision["options"]:
        place, policy = result.value, "memory"
    else:
        place, policy = decision["options"][0], "explore"
    text = (f"I remember: {result.value}. I go to {place}." if policy == "memory"
            else f"I do not remember where. I search {place}.")
    return {"action": {"go": place}, "answer": text, "policy": policy, "result": result.to_json()}


# ----------------------------------------------------------------- current-state baseline
def state_only_encode(experiences: list) -> dict:
    """Reads the same experiences with the same encoder; keeps only the current state:
    the last place per object (placing events) and the last appearance per person."""
    state = {"objects": {}, "people": {}}
    for exp in experiences:
        c = env_encode(exp["text"])
        if c["action"] in PLACING and c["object"]:
            state["objects"][c["object"]] = c["place"]
        for who in (c["actor"], c["partner"]):
            if who and who != SELF:
                state["people"][who] = c["place"]
    return state


def state_digest(state: dict) -> str:
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def state_decide(state: dict, decision: dict) -> dict:
    parsed = parse_goal(decision["goal"])
    trace = [("state", list(parsed) if parsed else None, [])]
    result = Result(None, "no_observation", [], trace)
    if parsed and parsed[2] == "current":
        kind, target, _ = parsed
        place = state["objects" if kind == "object" else "people"].get(target)
        if place is not None:
            result = _ok(place, [], trace)
    # a historical goal: the current state holds no history, so there is no answer
    return _act(result, decision)
