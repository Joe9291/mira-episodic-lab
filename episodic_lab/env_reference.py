"""Round 3.3 reference path (environment side), independent of the agent's memory.

Interventions are PLANNED here from the environment's structured events (`truth_content`
of a world, produced by the generator, not by any encoder): which episode is critical,
which one is swapped with it, which distractor is irrelevant, which random episodes
replace the memory. The prediction for every intervention is computed by applying the
counterfactual to those events with this module's own code and deciding with this
module's own rules. Nothing here uses the memory store, its operators or the
experience encoder, so an encoding error on the agent side cannot change a prediction.
"""
from __future__ import annotations

import re

from .env import PLACING, SELF, _distractor, _render, _vocab
from .rng import HashRng

INTERVENTIONS = ("intact", "none", "random", "swapped_binding", "relevant_removed", "irrelevant_removed")
_OBJECT_GOAL = re.compile(r"Find the ([a-z]+ [a-z]+)\.")
_GIVER_GOAL = re.compile(r"Find the person who gave you the ([a-z]+ [a-z]+)\.")


def plan(pair: dict, world_name: str) -> dict:
    """{intervention: spec or None (not applicable)} from the environment's events."""
    ev = pair["worlds"][world_name]["truth_content"]
    kind, obj, person, other = pair["kind"], pair["object"], pair["person"], pair["other_person"]
    crit, relevant, truth = pair["critical"], pair["relevant"], pair["worlds"][world_name]["truth"]
    specs = {"intact": {"op": "keep"}, "none": {"op": "clear"}}

    rng = HashRng(f"intervene:{pair['seed']}:{kind}:{world_name}")
    v = _vocab(HashRng(f"env:{pair['seed']}:{kind}"))
    random_events = []
    while len(random_events) < len(ev):
        e = _distractor(rng, v, obj, {person, other})
        if e[0] == "seen" and e[1] in (person, other):
            continue
        if e[0] == "placing" and e[1] in (person, other):
            e = ("went", e[-1])
        random_events.append(dict(_render(len(random_events) + 1, e)[1], event_day=len(random_events) + 1))
    specs["random"] = {"op": "replace", "events": random_events}

    if kind in ("hidden", "moved"):
        j = next((i for i, e in enumerate(ev) if e["action"] in PLACING and e["object"] not in (obj, None)
                  and e["place"] != truth and i not in relevant), None)
        specs["swapped_binding"] = None if j is None else {"op": "swap", "field": "place", "i": crit, "j": j}
    else:
        g1 = next(i for i, e in enumerate(ev) if e["action"] == "gave" and e["object"] == obj)
        g2 = next(i for i, e in enumerate(ev) if e["action"] == "gave" and e["object"] != obj)
        specs["swapped_binding"] = {"op": "swap", "field": "actor", "i": g1, "j": g2}
    specs["relevant_removed"] = {"op": "remove", "i": crit}
    k = next((i for i, e in enumerate(ev) if i not in relevant and e["object"] != obj
              and person not in (e["actor"], e["partner"]) and other not in (e["actor"], e["partner"])), None)
    specs["irrelevant_removed"] = None if k is None else {"op": "remove", "i": k}
    return specs


def apply_to_events(spec: dict, events: list[dict]) -> list[dict]:
    """The counterfactual on the environment's events (reference implementation)."""
    out = [dict(e) for e in events]
    if spec["op"] == "keep":
        return out
    if spec["op"] == "clear":
        return []
    if spec["op"] == "replace":
        return [dict(e) for e in spec["events"]]
    if spec["op"] == "swap":
        f, i, j = spec["field"], spec["i"], spec["j"]
        out[i][f], out[j][f] = events[j][f], events[i][f]
        return out
    if spec["op"] == "remove":
        return [e for n, e in enumerate(out) if n != spec["i"]]
    raise ValueError(spec["op"])


def reference_decision(events: list[dict], decision: dict) -> str:
    """Where an agent that remembers exactly these events should go (own rules)."""
    explore = decision["options"][0]
    goal = decision["goal"]
    m = _GIVER_GOAL.fullmatch(goal)
    if m:
        gave = [e for e in events if e["action"] == "gave" and e["object"] == m.group(1) and e["partner"] == SELF]
        if len(gave) != 1:
            return explore
        giver = gave[0]["actor"]
        seen = [e for e in events if giver in (e["actor"], e["partner"])]
        last_day = max(e["event_day"] for e in seen)
        places = {e["place"] for e in seen if e["event_day"] == last_day}
        return places.pop() if len(places) == 1 else explore
    m = _OBJECT_GOAL.fullmatch(goal)
    if m:
        placed = [e for e in events if e["object"] == m.group(1) and e["action"] in PLACING]
        if not placed:
            return explore
        last_day = max(e["event_day"] for e in placed)
        places = {e["place"] for e in placed if e["event_day"] == last_day}
        return places.pop() if len(places) == 1 else explore
    return explore


def predictions(pair: dict, world_name: str) -> dict:
    """{intervention: predicted place or None (not applicable)}."""
    world = pair["worlds"][world_name]
    out = {}
    for name, spec in plan(pair, world_name).items():
        out[name] = None if spec is None else reference_decision(
            apply_to_events(spec, world["truth_content"]), world["decision"])
    return out
