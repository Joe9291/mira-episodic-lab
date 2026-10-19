"""Round 3.5 worlds (docs/ROUND_3_5.md section 1): the round 3.3 kinds (hidden, moved,
giver) and the round 3.4 kinds (object, person history), with

- a distractor object with the SAME noun as the target object and another adjective
  (renaming one non-target object of the pair), so that dropping the adjective is a real
  binding error;
- in the non-giver kinds one extra "gave" episode (another person gives the agent a
  non-target object), so that every wording frame of the gave type is used often enough;
- wordings from `wordings35`: the frame of an episode depends on the split's wording set
  and on (pair seed, kind, position), never on the world, so both worlds of a pair differ
  only in the critical episode.

All changes are made on the structured events of both worlds alike and outside the
episodes the goals depend on; the truths (and, for history pairs, the final states) are
recomputed from the changed events by the independent references and must equal the
generator's truths (checked here and in the tests).
"""
from __future__ import annotations

import hashlib

from . import env, history_env
from .env import SELF
from .env_reference import reference_decision as env_reference_decision
from .history_reference import reference_decision as hist_reference_decision
from .wordings35 import choose, event_type, frame_id, render
from .world import OBJ_ADJ

KINDS35 = ("hidden", "moved", "giver", "object", "person")
FAMILY = {"hidden": "env", "moved": "env", "giver": "env", "object": "hist", "person": "hist"}
SPLITS = {"dev": "dev", "cal": "dev", "aud": "dev", "ho": "holdout", "res": "reserve"}
SCHEMA = "episodic_lab.env35_trial.v1"
SIZES = {"dev": 10, "cal": 10, "aud": 5, "ho": 40, "res": 40}   # pairs per kind
ORDER = ("dev", "cal", "aud", "ho", "res")


def _h(*parts) -> int:
    return int(hashlib.sha256(":".join(map(str, parts)).encode()).hexdigest(), 16)


def _protected(pair: dict) -> set:
    if FAMILY[pair["kind"]] == "env":
        return set(pair["relevant"]) | {pair["critical"]}
    return {pair["critical"], pair["middle"], pair["latest"]}


def _final_state(events: list[dict], objects: list, people: list) -> dict:
    """Every object's last place (placing events) and every person's last appearance."""
    obj = {o: None for o in objects}
    ppl = {p: None for p in people}
    for e in events:
        if e["action"] in env.PLACING and e["object"]:
            obj[e["object"]] = e["place"]
        for who in (e["actor"], e["partner"]):
            if who and who != SELF:
                ppl[who] = e["place"]
    return {"objects": obj, "people": ppl}


def generate_pair35(split: str, index: int, kind: str, attempt: int = 0, prefix: str = "r35",
                    wording_set: str | None = None) -> dict:
    """One pair; seed f"{prefix}-{split}-{index}[-r{attempt}]". Round 3.6 uses prefix "r36"
    (new worlds); wording_set overrides the note wording group of the split."""
    if kind not in KINDS35 or split not in SPLITS:
        raise ValueError((split, kind))
    seed = f"{prefix}-{split}-{index}" + (f"-r{attempt}" if attempt else "")
    fam = FAMILY[kind]
    pair = env.generate_pair(seed, kind) if fam == "env" else history_env.generate_pair(seed, kind)
    worlds = pair["worlds"]
    events = {w: [dict(e) for e in worlds[w]["truth_content"]] for w in worlds}
    target_obj = pair["object"]
    adj, noun = target_obj.split(" ", 1)
    protected = _protected(pair)
    n = len(events["A"])
    free = [i for i in range(n) if i not in protected]
    used_objects = sorted({e["object"] for w in events for e in events[w] if e["object"]})
    vocab_people = (set(worlds["A"]["final_state"]["people"]) if fam == "hist"
                    else {pair["person"], pair["other_person"]})
    people = sorted({who for w in events for e in events[w] for who in (e["actor"], e["partner"])
                     if who and who != SELF} | {pair["person"]} | vocab_people)

    # 1. same-noun distractor: rename one non-target object that occurs only in free positions
    candidates = [o for o in used_objects if o != target_obj
                  and all(i in free for w in events for i, e in enumerate(events[w]) if e["object"] == o)]
    adjectives = [a for a in OBJ_ADJ if a != adj and f"{a} {noun}" not in used_objects]
    new_name = f"{adjectives[_h(seed, kind, 'adj') % len(adjectives)]} {noun}"
    if candidates:
        old = candidates[_h(seed, kind, 'obj') % len(candidates)]
        for w in events:
            for e in events[w]:
                if e["object"] == old:
                    e["object"] = new_name
    else:  # no suitable object: an own placing of the new object in a free position
        i = free[_h(seed, kind, 'pos') % len(free)]
        place = events["A"][i]["place"]
        for w in events:
            events[w][i] = dict(events[w][i], actor=SELF, partner=None, action="put", object=new_name, place=place)
    # 2. one extra "gave" episode in the non-giver kinds (another person, a non-target object)
    if kind != "giver":
        left = [i for i in free if events["A"][i]["object"] != new_name]
        i = left[_h(seed, kind, 'gave') % len(left)]
        givers = [p for p in people if p != pair["person"]]
        objs = [o for o in used_objects + [new_name] if o not in (target_obj, new_name)] or [new_name]
        giver = givers[_h(seed, kind, 'giver') % len(givers)]
        obj = objs[_h(seed, kind, 'gobj') % len(objs)]
        for w in events:
            events[w][i] = dict(events[w][i], actor=giver, partner=SELF, action="gave", object=obj)
    # 3. wordings (same frame in both worlds at every position)
    wset = wording_set or SPLITS[split]
    out_worlds = {}
    for w, evs in events.items():
        exps = []
        for pos, c in enumerate(evs):
            etype = event_type(c)
            group, idx, template = choose(etype, wset, f"{seed}:{kind}:{pos}")
            exps.append({"text": render(c, template), "frame": frame_id(etype, group, idx),
                         "source": {"kind": "own_action" if c["actor"] == SELF else "observed", "by": None}})
        ow = {"experiences": exps, "truth_content": evs, "truth": worlds[w]["truth"]}
        if fam == "env":
            ow["decision"] = worlds[w]["decision"]
        else:
            ow["decisions"] = worlds[w]["decisions"]
            objects = sorted(set(worlds[w]["final_state"]["objects"]) | {e["object"] for e in evs if e["object"]})
            ow["final_state"] = _final_state(evs, objects, people)
        out_worlds[w] = ow
    out = {k: v for k, v in pair.items() if k != "worlds"}
    out.update(schema=SCHEMA, split=split, index=index, attempt=attempt, family=fam, same_noun_object=new_name,
               wording_set=wset, worlds=out_worlds)
    check_truths(out)
    return out


def check_truths(pair: dict) -> None:
    """The generator's truths must follow from the changed events (independent references)."""
    for w in pair["worlds"].values():
        if pair["family"] == "env":
            # an agent that remembers exactly the true events goes to the true place
            got = env_reference_decision(w["truth_content"], w["decision"])
            if got != w["truth"]:
                raise AssertionError(f"env truth changed: {pair['seed']} {pair['kind']}")
        else:
            for goal, d in w["decisions"].items():
                got = hist_reference_decision(w["truth_content"], pair["kind"], pair["target"], goal, d["options"])
                if got != w["truth"][goal]:
                    raise AssertionError(f"history truth changed: {pair['seed']} {pair['kind']} {goal}")


_CACHE: dict = {}


def split_pairs(split: str) -> list[dict]:
    """The pairs of a split, with episode texts disjoint from every earlier split (order
    dev, cal, aud, ho, res): a pair that would share a text with an earlier split is
    regenerated with the next attempt number (its seed gets the suffix -r<attempt>)."""
    if split in _CACHE:
        return _CACHE[split]
    forbidden = set()
    for earlier in ORDER[:ORDER.index(split)]:
        forbidden |= {e["text"] for p in split_pairs(earlier) for w in p["worlds"].values() for e in w["experiences"]}
    out = []
    for kind in KINDS35:
        for i in range(SIZES[split]):
            attempt = 0
            while True:
                p = generate_pair35(split, i, kind, attempt)
                texts = {e["text"] for w in p["worlds"].values() for e in w["experiences"]}
                if not texts & forbidden:
                    break
                attempt += 1
            out.append(p)
    _CACHE[split] = out
    return out
