"""Round 3.3 text action environment (docs/ROUND_3_3.md).

The agent lives through a sequence of days; every day it experiences one event, given to
it as a sentence (its own experience: what it saw, what it did, what someone did to it).
Only then is a goal announced, together with the current observation (where it is and
which places it can go to). The environment, not the agent, knows where things really are
and scores the action the agent takes.

Trials come in PAIRS that are identical in every experience except one (the critical
episode) and identical at decision time (same goal text, same current observation, same
options); the critical episode makes a different action correct. An agent without memory
of that episode cannot be right in both worlds of a pair.

Kinds:
  hidden  you saw a person hide/leave/put an object at a place; goal: find the object
  moved   the object was placed at one place and later moved to another; goal: find it
          (the later episode decides)
  giver   a person gave you an object; later you saw that person somewhere; goal: find
          the person who gave you the object (two episodes linked through the person)

Distractors re-use the same people, places and objects, so only bindings identify the
relevant episodes.
"""
from __future__ import annotations

import re

from .rng import HashRng
from .world import FIRST, LAST, OBJ_ADJ, OBJ_NOUN, PLACE_KIND, PLACE_STEM

ENV_SCHEMA = "episodic_lab.env_trial.v1"
KINDS = ("hidden", "moved", "giver")
PLACING = ("hid", "left", "put")
SELF = "You"
N_PLACES, N_OBJECTS, N_PEOPLE = 6, 8, 3

OBSERVED_PLACING = "On day {d}, you saw {x} {verb} the {obj} at {place}."
OWN_PUT = "On day {d}, you put the {obj} at {place}."
GAVE = "On day {d}, {x} gave you the {obj} at {place}."
SEEN_AT = "On day {d}, you saw {x} at {place}."
WENT = "On day {d}, you went to {place}."
GOALS = {"hidden": "Find the {obj}.", "moved": "Find the {obj}.",
         "giver": "Find the person who gave you the {obj}."}
DECISION = "You are in the hall. Goal: {goal} You can go to: {options}."


def _vocab(rng: HashRng) -> dict:
    firsts, lasts = rng.sample(list(FIRST), N_PEOPLE), rng.sample(list(LAST), N_PEOPLE)
    stems, kinds = rng.sample(list(PLACE_STEM), N_PLACES), rng.sample(list(PLACE_KIND), N_PLACES)
    adjs, nouns = rng.sample(list(OBJ_ADJ), N_OBJECTS), rng.sample(list(OBJ_NOUN), N_OBJECTS)
    return {"people": [f"{f} {s}" for f, s in zip(firsts, lasts)],
            "places": sorted(f"{s} {k}" for s, k in zip(stems, kinds)),
            "objects": [f"{a} {n}" for a, n in zip(adjs, nouns)]}


def _distractor(rng: HashRng, v: dict, target_obj: str, givers_used: set) -> tuple:
    """One irrelevant event that re-uses people, places and other objects."""
    kind = rng.choice(("placing", "own_put", "seen", "went"))
    other_objs = [o for o in v["objects"] if o != target_obj]
    if kind == "placing":
        return ("placing", rng.choice(v["people"]), rng.choice(PLACING), rng.choice(other_objs),
                rng.choice(v["places"]))
    if kind == "own_put":
        return ("own_put", rng.choice(other_objs), rng.choice(v["places"]))
    if kind == "seen":
        return ("seen", rng.choice([p for p in v["people"] if p not in givers_used] or v["people"]),
                rng.choice(v["places"]))
    return ("went", rng.choice(v["places"]))


def _render(day: int, ev: tuple) -> tuple[str, dict]:
    kind = ev[0]
    if kind == "placing":
        _, x, verb, obj, place = ev
        return OBSERVED_PLACING.format(d=day, x=x, verb=verb, obj=obj, place=place), {
            "actor": x, "partner": None, "action": verb, "object": obj, "place": place}
    if kind == "own_put":
        _, obj, place = ev
        return OWN_PUT.format(d=day, obj=obj, place=place), {
            "actor": SELF, "partner": None, "action": "put", "object": obj, "place": place}
    if kind == "gave":
        _, x, obj, place = ev
        return GAVE.format(d=day, x=x, obj=obj, place=place), {
            "actor": x, "partner": SELF, "action": "gave", "object": obj, "place": place}
    if kind == "seen":
        _, x, place = ev
        return SEEN_AT.format(d=day, x=x, place=place), {
            "actor": x, "partner": None, "action": "was", "object": None, "place": place}
    _, place = ev
    return WENT.format(d=day, place=place), {
        "actor": SELF, "partner": None, "action": "went", "object": None, "place": place}


def _truth(events: list, kind: str, obj: str):
    """Where the goal is really reached, from the event list (the environment's state)."""
    if kind in ("hidden", "moved"):
        last = None
        for ev in events:
            if ev[0] == "placing" and ev[3] == obj:
                last = ev[4]
            elif ev[0] == "own_put" and ev[1] == obj:
                last = ev[2]
        return last
    giver = next(ev[1] for ev in events if ev[0] == "gave" and ev[2] == obj)
    last = None
    for ev in events:
        if ev[0] in ("placing", "seen", "gave") and ev[1] == giver:
            last = ev[-1]
    return last


def generate_pair(seed: str, kind: str, length: int = 14) -> dict:
    """Two worlds that differ only in the critical episode; returns both with metadata."""
    if kind not in KINDS:
        raise ValueError(kind)
    rng = HashRng(f"env:{seed}:{kind}")
    v = _vocab(rng)
    obj = v["objects"][0]
    person, other = v["people"][0], v["people"][1]
    p_a, p_b = rng.sample(v["places"], 2)        # the critical place in world A / world B
    givers = {person, other}
    events = [_distractor(rng, v, obj, givers) for _ in range(length)]
    slots = rng.sample(list(range(length)), 3)
    first, second, third = sorted(slots)
    if kind == "hidden":
        events[second] = ("placing", person, rng.choice(PLACING), obj, None)   # critical
        critical, relevant = second, [second]
    elif kind == "moved":
        p_old = rng.choice([p for p in v["places"] if p not in (p_a, p_b)])
        events[first] = ("placing", person, rng.choice(PLACING), obj, p_old)
        events[third] = ("own_put", obj, None)                                 # critical
        critical, relevant = third, [first, third]
    else:
        events[first] = ("gave", person, obj, rng.choice(v["places"]))
        events[second] = ("gave", other, v["objects"][1], rng.choice(v["places"]))
        events[third] = ("seen", person, None)                                 # critical
        critical, relevant = third, [first, third]
        # no later sighting of the giver may follow the critical one
        for i in range(third + 1, length):
            if events[i][0] in ("placing", "seen") and events[i][1] == person:
                events[i] = ("went", events[i][-1])
    worlds = {}
    for name, place in (("A", p_a), ("B", p_b)):
        evs = list(events)
        evs[critical] = evs[critical][:-1] + (place,)
        rendered = [_render(day, ev) for day, ev in enumerate(evs, start=1)]
        truth = _truth(evs, kind, obj)
        goal = GOALS[kind].format(obj=obj)
        worlds[name] = {
            "experiences": [{"text": t, "source": {"kind": "own_action" if c["actor"] == SELF else "observed",
                                                   "by": None}} for t, c in rendered],
            "truth_content": [dict(c, event_day=day) for day, (_, c) in enumerate(rendered, start=1)],
            "decision": {"goal": goal, "options": list(v["places"]),
                         "text": DECISION.format(goal=goal, options=", ".join(v["places"]))},
            "truth": truth}
    return {"schema": ENV_SCHEMA, "seed": seed, "kind": kind, "object": obj, "person": person,
            "other_person": other, "critical": critical, "relevant": relevant, "worlds": worlds}


def render_content(c: dict) -> str:
    """Experience sentence for a record content (used for intervened memories, so that a
    record's text never contradicts its fields)."""
    if c["action"] == "gave":
        return _render(c["event_day"], ("gave", c["actor"], c["object"], c["place"]))[0]
    if c["action"] == "was":
        return _render(c["event_day"], ("seen", c["actor"], c["place"]))[0]
    if c["action"] == "went":
        return _render(c["event_day"], ("went", c["place"]))[0]
    if c["actor"] == SELF:
        return _render(c["event_day"], ("own_put", c["object"], c["place"]))[0]
    return _render(c["event_day"], ("placing", c["actor"], c["action"], c["object"], c["place"]))[0]


# ----------------------------------------------------------------- encoder for the env texts
_N = r"[A-Z][a-z]+ [A-Z][a-z]+"
_P = _N
_O = r"[a-z]+ [a-z]+"
_ENV_PATTERNS = [
    (rf"On day (?P<d>\d+), you saw (?P<x>{_N}) (?P<verb>hid|left|put) the (?P<obj>{_O}) at (?P<place>{_P})\.", "placing"),
    (rf"On day (?P<d>\d+), you put the (?P<obj>{_O}) at (?P<place>{_P})\.", "own_put"),
    (rf"On day (?P<d>\d+), (?P<x>{_N}) gave you the (?P<obj>{_O}) at (?P<place>{_P})\.", "gave"),
    (rf"On day (?P<d>\d+), you saw (?P<x>{_N}) at (?P<place>{_P})\.", "seen"),
    (rf"On day (?P<d>\d+), you went to (?P<place>{_P})\.", "went"),
]


def env_encode(text: str) -> dict:
    """Template encoder for the environment's experience sentences (control encoder)."""
    for pattern, kind in _ENV_PATTERNS:
        m = re.fullmatch(pattern, text)
        if not m:
            continue
        g, d = m.groupdict(), int(m.group("d"))
        content = {"placing": lambda: {"actor": g["x"], "partner": None, "action": g["verb"], "object": g["obj"]},
                   "own_put": lambda: {"actor": SELF, "partner": None, "action": "put", "object": g["obj"]},
                   "gave": lambda: {"actor": g["x"], "partner": SELF, "action": "gave", "object": g["obj"]},
                   "seen": lambda: {"actor": g["x"], "partner": None, "action": "was", "object": None},
                   "went": lambda: {"actor": SELF, "partner": None, "action": "went", "object": None}}[kind]()
        return dict(content, place=g["place"], event_day=d)
    raise ValueError(f"unparsed experience: {text}")


_GOALS = [(re.compile(r"Find the (?P<obj>[a-z]+ [a-z]+)\."), "object"),
          (re.compile(r"Find the person who gave you the (?P<obj>[a-z]+ [a-z]+)\."), "giver")]


def parse_goal(goal: str) -> tuple[str, str] | None:
    for pattern, kind in _GOALS:
        m = pattern.fullmatch(goal)
        if m:
            return kind, m.group("obj")
    return None
