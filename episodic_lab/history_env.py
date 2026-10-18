"""Round 3.4 step 1 environment: history goals with an identical final state
(docs/ROUND_3_4.md). Re-uses the round 3.3 world (vocabulary, sentence templates,
distractors) without changing it.

A pair of worlds differs only in an OLD episode about the target (the first placing of
the object / the first sighting of the person); two later episodes about the same target
follow in both worlds, so the final state (every object's last place, every person's
last appearance) is the same. Three goals are asked of the same stored experiences:
current (same answer in A and B), first (different), previous (same).
"""
from __future__ import annotations

from .env import PLACING, SELF, _distractor, _render, _vocab
from .rng import HashRng

HIST_SCHEMA = "episodic_lab.history_trial.v1"
KINDS = ("object", "person")
GOAL_NAMES = ("current", "first", "previous")
GOALS = {
    "object": {"current": "Find the {t}.", "first": "Go to where the {t} was first placed.",
               "previous": "Go to where the {t} was before it was last placed."},
    "person": {"current": "Find {t}.", "first": "Go to where you first saw {t}.",
               "previous": "Go to where you saw {t} before you last saw them."},
}
DECISION = "You are in the hall. Goal: {goal} You can go to: {options}."


def _mentions(ev: tuple, person: str) -> bool:
    return ev[0] in ("placing", "seen", "gave") and ev[1] == person


def generate_pair(seed: str, kind: str, length: int = 14) -> dict:
    if kind not in KINDS:
        raise ValueError(kind)
    rng = HashRng(f"hist:{seed}:{kind}")
    v = _vocab(rng)
    obj, person, other = v["objects"][0], v["people"][0], v["people"][1]
    p1a, p1b, p2, final = rng.sample(v["places"], 4)
    events = [_distractor(rng, v, obj, {person}) for _ in range(length)]
    if kind == "person":  # the target person appears only in the three target episodes
        events = [("went", ev[-1]) if _mentions(ev, person) else ev for ev in events]
    d1, d2, d3, dx = rng.sample(list(range(length)), 4)
    d1, d2, d3 = sorted((d1, d2, d3))
    # one irrelevant episode of the same type as the old one, at a place that differs from
    # the old place in both worlds (the swap partner of the old_swapped intervention)
    px = rng.choice([p for p in v["places"] if p not in (p1a, p1b)])
    if kind == "object":
        events[dx] = ("placing", other, rng.choice(PLACING), v["objects"][1], px)
    else:
        events[dx] = ("seen", other, px)
    if kind == "object":
        events[d1] = ("own_put", obj, None)                                    # old, critical
        events[d2] = ("placing", person, rng.choice(PLACING), obj, p2)
        events[d3] = ("placing", other, rng.choice(PLACING), obj, final)       # latest
        target = obj
    else:
        events[d1] = ("seen", person, None)                                    # old, critical
        events[d2] = ("seen", person, p2)
        events[d3] = ("seen", person, final)                                   # latest
        target = person
    worlds = {}
    for name, place in (("A", p1a), ("B", p1b)):
        evs = list(events)
        evs[d1] = evs[d1][:-1] + (place,)
        rendered = [_render(day, ev) for day, ev in enumerate(evs, start=1)]
        goals = {g: GOALS[kind][g].format(t=target) for g in GOAL_NAMES}
        worlds[name] = {
            "experiences": [{"text": t, "source": {"kind": "own_action" if c["actor"] == SELF else "observed",
                                                   "by": None}} for t, c in rendered],
            "truth_content": [dict(c, event_day=day) for day, (_, c) in enumerate(rendered, start=1)],
            "decisions": {g: {"goal": goals[g], "options": list(v["places"]),
                              "text": DECISION.format(goal=goals[g], options=", ".join(v["places"]))}
                          for g in GOAL_NAMES},
            "truth": truths(evs, kind, target),
            "final_state": final_state(evs, v)}
    return {"schema": HIST_SCHEMA, "seed": seed, "kind": kind, "target": target, "object": obj,
            "person": person, "critical": d1, "middle": d2, "latest": d3, "worlds": worlds}


def _target_places(events: list, kind: str, target: str) -> list:
    """Places of the target's episodes in time order (the environment's own history)."""
    if kind == "object":
        return [ev[-1] for ev in events if (ev[0] == "placing" and ev[3] == target)
                or (ev[0] == "own_put" and ev[1] == target)]
    return [ev[-1] for ev in events if _mentions(ev, target)]


def truths(events: list, kind: str, target: str) -> dict:
    places = _target_places(events, kind, target)
    return {"current": places[-1], "first": places[0], "previous": places[-2]}


def final_state(events: list, v: dict) -> dict:
    """Every object's last place and every person's last appearance (None if never)."""
    objects = {o: None for o in v["objects"]}
    people = {p: None for p in v["people"]}
    for ev in events:
        if ev[0] == "placing":
            objects[ev[3]] = ev[4]
            people[ev[1]] = ev[4]
        elif ev[0] == "own_put":
            objects[ev[1]] = ev[2]
        elif ev[0] in ("seen", "gave"):
            people[ev[1]] = ev[-1]
    return {"objects": objects, "people": people}
