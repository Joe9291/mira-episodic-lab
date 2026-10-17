"""Round 3.3 agent and memory interventions (docs/ROUND_3_3.md).

The agent writes every experience into its episodic store (episodic_lab.memory) and, at
decision time, answers the goal only from the store with the explicit operators. If the
memory gives no supported answer it explores: it goes to the first listed place (a fixed,
memory-free policy, identical in both worlds of a pair).

Interventions change only the memory content: the agent's store is encoded ONCE per
world, every variant is derived from that encoded store (derive_variant) following the
plan of env_reference.plan and written as a new sealed store; the decision is taken by a
fresh process per case that sees nothing but one store, its seal and the decision text.
Predictions are computed on the environment side (episodic_lab/env_reference.py) from
the generator's structured events, independently of the encoder and the operators.
"""
from __future__ import annotations

from .env import PLACING, SELF, env_encode, parse_goal, render_content
from .memory import EpisodeStore, Result, _day, _ok, latest, match

from .env_reference import INTERVENTIONS  # noqa: E402  (one list of interventions)


def object_location(records, obj: str) -> Result:
    """Latest placing of the object; an undated placing elsewhere makes it ambiguous."""
    hits = [r for r in match(records, obj=obj) if r["action"] in PLACING]
    trace = [("object_location", obj, [r["id"] for r in hits])]
    if not hits:
        return Result(None, "no_observation", [], trace)
    dated = [r for r in hits if _day(r) is not None]
    if not dated:
        return Result(None, "ambiguous", [r["id"] for r in hits], trace)
    top = max(_day(r) for r in dated)
    places = {r["place"] for r in dated if _day(r) == top} | {r["place"] for r in hits if _day(r) is None}
    if len(places) != 1:
        return Result(None, "ambiguous", [r["id"] for r in hits], trace)
    return _ok(places.pop(), [r["id"] for r in dated if _day(r) == top], trace)


def giver_location(records, obj: str) -> Result:
    gave = [r for r in match(records, action="gave", obj=obj) if r["partner"] == SELF]
    trace = [("giver", obj, [r["id"] for r in gave])]
    if len(gave) != 1:
        return Result(None, "no_observation" if not gave else "ambiguous", [r["id"] for r in gave], trace)
    nxt = latest(records, gave[0]["actor"])
    return Result(nxt.value, nxt.status, [gave[0]["id"]] + nxt.ids, trace + nxt.trace)


def decide(records, decision: dict) -> dict:
    """Memory-based decision; falls back to exploring the first listed place."""
    parsed = parse_goal(decision["goal"])
    result = Result(None, "no_observation")
    if parsed:
        kind, obj = parsed
        result = object_location(records, obj) if kind == "object" else giver_location(records, obj)
    if result.status == "ok" and result.value in decision["options"]:
        place, policy = result.value, "memory"
    else:
        place, policy = decision["options"][0], "explore"
    text = (f"I remember: {result.value}. I go to {place}." if policy == "memory"
            else f"I do not remember where. I search {place}.")
    return {"action": {"go": place}, "answer": text, "policy": policy, "result": result.to_json()}


def write_store(path, experiences: list, contents: list | None = None) -> EpisodeStore:
    """Encode experiences into a new store. With `contents` (an intervened memory) every
    record gets the content and a text re-rendered from it, so text and fields agree."""
    store = EpisodeStore(path)
    for i, exp in enumerate(experiences):
        if contents is None:
            text, content = exp["text"], env_encode(exp["text"])
        else:
            content = contents[i]
            text = render_content(content)
        store.append(text, content, source=exp["source"], encoder="env-template")
    return store


CONTENT = ("actor", "partner", "action", "object", "place", "event_day")


def derive_variant(spec: dict, records: list[dict]) -> list[dict]:
    """Memory side: the intervened record contents, derived from the ACTUALLY ENCODED store
    (agent's records), following the plan made by env_reference.plan. This is a separate
    implementation of the counterfactual; predictions never use it."""
    contents = [{k: r[k] for k in CONTENT} for r in records]
    op = spec["op"]
    if op == "keep":
        return contents
    if op == "clear":
        return []
    if op == "replace":  # the random memory comes from the environment's random events
        return [{k: e[k] for k in CONTENT} for e in spec["events"]]
    if op == "swap":
        f, i, j = spec["field"], spec["i"], spec["j"]
        a, b = contents[i][f], contents[j][f]
        contents[i] = dict(contents[i], **{f: b})
        contents[j] = dict(contents[j], **{f: a})
        return contents
    if op == "remove":
        return [c for n, c in enumerate(contents) if n != spec["i"]]
    raise ValueError(op)


def materialize(path, contents: list[dict], sources: list[dict]) -> EpisodeStore:
    """A new sealed store from intervened contents; every text is re-rendered from its
    fields, so text and fields of a record never contradict each other."""
    store = EpisodeStore(path)
    for content, source in zip(contents, sources):
        store.append(render_content(content), content, source=source, encoder="env-template")
    return store
