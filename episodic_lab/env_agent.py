"""Round 3.3 agent and memory interventions (docs/ROUND_3_3.md).

The agent writes every experience into its episodic store (episodic_lab.memory) and, at
decision time, answers the goal only from the store with the explicit operators. If the
memory gives no supported answer it explores: it goes to the first listed place (a fixed,
memory-free policy, identical in both worlds of a pair).

Interventions change only the memory content, then the decision is taken by a fresh
process that sees nothing but the store, its seal and the decision text. Predictions for
every intervention are computed from the ENVIRONMENT's event list (not from the agent):

  intact            the true place
  none              the exploration place (empty store)
  random            the exploration place (equal number of irrelevant episodes from the
                    same vocabulary, nothing about the goal object or its giver)
  swapped_binding   the place implied by the swapped binding (hidden/moved: the critical
                    episode exchanges its place with another object's placing episode;
                    giver: the two "gave" episodes exchange their person)
  relevant_removed  hidden: exploration; moved: the earlier place; giver: the giver's
                    last appearance before the critical sighting
  irrelevant_removed the true place (one distractor that mentions neither the goal object
                    nor the giver is removed)
"""
from __future__ import annotations

from .env import PLACING, SELF, _distractor, _render, _vocab, env_encode, parse_goal, render_content
from .memory import EpisodeStore, Result, _day, _ok, latest, match
from .rng import HashRng

INTERVENTIONS = ("intact", "none", "random", "swapped_binding", "relevant_removed", "irrelevant_removed")


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


def _events_of(world: dict) -> list:
    return [dict(c) for c in world["truth_content"]]


def intervene(pair: dict, world_name: str) -> dict:
    """{intervention: (experiences, contents, predicted place)} for one world of a pair."""
    world = pair["worlds"][world_name]
    exps, content = world["experiences"], [env_encode(e["text"]) for e in world["experiences"]]
    options, explore = world["decision"]["options"], world["decision"]["options"][0]
    kind, obj, person, other = pair["kind"], pair["object"], pair["person"], pair["other_person"]
    crit, relevant = pair["critical"], pair["relevant"]
    truth = world["truth"]
    out = {"intact": (exps, content, truth), "none": ([], [], explore)}

    rng = HashRng(f"intervene:{pair['seed']}:{kind}:{world_name}")
    v = _vocab(HashRng(f"env:{pair['seed']}:{kind}"))
    rand_exps, rand_content = [], []
    while len(rand_exps) < len(exps):
        ev = _distractor(rng, v, obj, {person, other})
        if ev[0] == "seen" and ev[1] in (person, other):
            continue
        if ev[0] == "placing" and ev[1] in (person, other):
            ev = ("went", ev[-1])
        text, c = _render(len(rand_exps) + 1, ev)
        rand_exps.append({"text": text, "source": {"kind": "own_action" if c["actor"] == SELF else "observed", "by": None}})
        rand_content.append(dict(c, event_day=len(rand_exps)))
    out["random"] = (rand_exps, rand_content, explore)

    swapped = [dict(c) for c in content]
    if kind in ("hidden", "moved"):
        partner = next((i for i, c in enumerate(content)
                        if c["action"] in PLACING and c["object"] not in (obj, None)
                        and c["place"] != truth and i not in relevant), None)
        if partner is None:
            predicted_swap = None
        else:
            swapped[crit]["place"], swapped[partner]["place"] = content[partner]["place"], content[crit]["place"]
            predicted_swap = content[partner]["place"]
    else:
        g1 = next(i for i, c in enumerate(content) if c["action"] == "gave" and c["object"] == obj)
        g2 = next(i for i, c in enumerate(content) if c["action"] == "gave" and c["object"] != obj)
        swapped[g1]["actor"], swapped[g2]["actor"] = content[g2]["actor"], content[g1]["actor"]
        appearances = [c for c in swapped if other in (c["actor"], c["partner"])]
        predicted_swap = max(appearances, key=lambda c: c["event_day"])["place"]
    out["swapped_binding"] = (exps, swapped, predicted_swap) if predicted_swap is not None else None

    keep = [i for i in range(len(exps)) if i != crit]
    if kind == "hidden":
        predicted_rm = explore
    elif kind == "moved":
        predicted_rm = content[relevant[0]]["place"]
    else:
        before = [content[i] for i in keep if person in (content[i]["actor"], content[i]["partner"])]
        predicted_rm = max(before, key=lambda c: c["event_day"])["place"]
    out["relevant_removed"] = ([exps[i] for i in keep], [content[i] for i in keep], predicted_rm)

    irrelevant = next((i for i, c in enumerate(content)
                       if i not in relevant and c["object"] != obj
                       and person not in (c["actor"], c["partner"]) and other not in (c["actor"], c["partner"])), None)
    if irrelevant is None:
        out["irrelevant_removed"] = None
    else:
        keep = [i for i in range(len(exps)) if i != irrelevant]
        out["irrelevant_removed"] = ([exps[i] for i in keep], [content[i] for i in keep], truth)
    return out
