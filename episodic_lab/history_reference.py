"""Round 3.4 step 1 reference path (environment side), independent of the agent's memory.

Interventions are planned from the generator's structured events (`truth_content`), the
counterfactual is applied to those events by this module's own code, and the expected
decision for every goal is computed by this module's own rules. Nothing here uses the
memory store, its operators or the experience encoder.
"""
from __future__ import annotations

from .env import PLACING

INTERVENTIONS = ("intact", "none", "old_removed", "old_swapped", "last_removed", "irrelevant_removed")


def _is_target(e: dict, kind: str, target: str) -> bool:
    if kind == "object":
        return e["object"] == target and e["action"] in PLACING
    return target in (e["actor"], e["partner"])


def _same_type_other(e: dict, kind: str, target: str) -> bool:
    """An irrelevant episode of the same type as the old one (for the place swap)."""
    if kind == "object":
        return e["action"] in PLACING and e["object"] not in (target, None)
    return e["action"] == "was" and target not in (e["actor"], e["partner"])


def plan(pair: dict, world_name: str) -> dict:
    """{intervention: spec or None (not applicable)}, by event position."""
    ev = pair["worlds"][world_name]["truth_content"]
    kind, target = pair["kind"], pair["target"]
    old, latest = pair["critical"], pair["latest"]
    relevant = {pair["critical"], pair["middle"], pair["latest"]}
    specs = {"intact": {"op": "keep"}, "none": {"op": "clear"},
             "old_removed": {"op": "remove", "i": old}, "last_removed": {"op": "remove", "i": latest}}
    j = next((i for i, e in enumerate(ev) if i not in relevant and _same_type_other(e, kind, target)
              and e["place"] != ev[old]["place"]), None)
    specs["old_swapped"] = None if j is None else {"op": "swap", "field": "place", "i": old, "j": j}
    k = next((i for i, e in enumerate(ev) if i not in relevant and e["object"] != pair["object"]
              and pair["person"] not in (e["actor"], e["partner"])), None)
    specs["irrelevant_removed"] = None if k is None else {"op": "remove", "i": k}
    return specs


def apply_to_events(spec: dict, events: list[dict]) -> list[dict]:
    out = [dict(e) for e in events]
    if spec["op"] == "keep":
        return out
    if spec["op"] == "clear":
        return []
    if spec["op"] == "swap":
        f, i, j = spec["field"], spec["i"], spec["j"]
        out[i][f], out[j][f] = events[j][f], events[i][f]
        return out
    if spec["op"] == "remove":
        return [e for n, e in enumerate(out) if n != spec["i"]]
    raise ValueError(spec["op"])


def reference_decision(events: list[dict], kind: str, target: str, goal: str, options: list) -> str:
    """Where an agent that remembers exactly these events should go for this goal."""
    explore = options[0]
    mine = sorted((e for e in events if _is_target(e, kind, target)), key=lambda e: e["event_day"])
    days = [e["event_day"] for e in mine]
    if not mine or len(set(days)) != len(days):
        return explore
    if goal == "current":
        return mine[-1]["place"]
    if goal == "first":
        return mine[0]["place"]
    if goal == "previous":
        return mine[-2]["place"] if len(mine) >= 2 else explore
    raise ValueError(goal)


def predictions(pair: dict, world_name: str) -> dict:
    """{intervention: {goal: predicted place} or None (not applicable)}."""
    w = pair["worlds"][world_name]
    out = {}
    for name, spec in plan(pair, world_name).items():
        if spec is None:
            out[name] = None
            continue
        events = apply_to_events(spec, w["truth_content"])
        out[name] = {g: reference_decision(events, pair["kind"], pair["target"], g, d["options"])
                     for g, d in w["decisions"].items()}
    return out
