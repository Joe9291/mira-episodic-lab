"""Question sets with ground truth for a world (protocol sections 2 and 3).

Two test points: `phase1` right after the early block and `final` after all episodes.

Early-target items (E2, E3a, E3b on a day, E4, E5) are chosen from the early block with
a seed-only random stream and are checked against the full worlds of BOTH overlap
conditions, so the high- and low-overlap versions of a seed test exactly the same early
items with the same answers (E6). Lures are built from details that co-occur in the
early block, so they are lures already at phase 1. Final-only items (latest state, E7)
may differ between conditions.

The public question files carry no answers; the gold file is for the evaluator only.
Gold answers come from `answer_for`, a direct rule over episodes that tests also check
on hand-made worlds.
"""
from __future__ import annotations

import hashlib
import json

from .rng import HashRng
from .world import Episode, episodes_of, generate_world

QUESTION_SCHEMA = "episodic_lab.questions.v2"
MINIMUM = {"E2": 8, "E3a": 4, "E3b": 4, "E4": 4, "E5": 6, "E7": 3}

PARA = {
    "object": ("What did {person} {action} at {place}?",
               "At {place}, which thing did {person} {action}?",
               "Name the object that {person} {past} at {place}."),
    "place": ("Where did {person} {action} the {object}?",
              "At which place did {person} {action} the {object}?",
              "Name the place where {person} {past} the {object}."),
    "person": ("Who {past} the {object} at {place}?",
               "Which person {past} the {object} at {place}?",
               "Name someone who {past} the {object} at {place}."),
    "day": ("On which day did {person} {action} the {object}?",
            "Which day was it when {person} {past} the {object}?"),
    "order": ("Which happened first? (A) {a} (B) {b} Answer A or B.",
              "Two events: (A) {a} (B) {b} Which one was earlier? Answer A or B."),
    "latest": ("Where was {person} most recently?",
               "At which place was {person} seen last?"),
    "at_day": ("Where was {person} on day {day}?",
               "At which place was {person} on day {day}?"),
    "act": ("You need to talk to the last person who handled the {object}. To which place "
            "do you go, where that person was seen most recently?",
            "Decide where to go: you are looking for whoever last handled the {object}, at "
            "the place where that person was last seen."),
    "find": ("You want to meet the person who {past} the {object} at {place}. Where do you go "
             "to find that person now?",
             "Decide where to go to meet whoever {past} the {object} at {place}, at the place "
             "where that person was seen most recently."),
}
BASE = {"repaired": "repair", "painted": "paint", "sold": "sell", "hid": "hide",
        "found": "find", "measured": "measure", "cleaned": "clean", "carried": "carry"}


def matching(episodes, person=None, action=None, place=None, obj=None):
    return [e for e in episodes
            if (person is None or person in e.participants)
            and (action is None or e.action == action)
            and (place is None or e.place == place)
            and (obj is None or e.object == obj)]


def answer_for(episodes: list[Episode], qtype: str, cue: dict) -> list[str]:
    """The gold answer(s) by direct rule; ["none"] if no episode matches.

    Raises ValueError if an item is ill-defined (ambiguous cue, equal days, two handlers).
    """
    if qtype in ("object", "place", "person", "day"):
        hits = matching(episodes, **cue)
        if not hits:
            return ["none"]
        if len(hits) > 1:
            raise ValueError("ambiguous cue")
        e = hits[0]
        return {"object": [e.object], "place": [e.place], "person": list(e.participants),
                "day": [str(e.day)]}[qtype]
    if qtype == "order":
        a = matching(episodes, **cue["a"])
        b = matching(episodes, **cue["b"])
        if len(a) != 1 or len(b) != 1 or a[0].day == b[0].day:
            raise ValueError("order items need two unique events on different days")
        return ["A" if a[0].day < b[0].day else "B"]
    if qtype == "latest":
        hits = matching(episodes, person=cue["person"])
        return [max(hits, key=lambda e: e.day).place] if hits else ["none"]
    if qtype == "at_day":
        hits = [e for e in matching(episodes, person=cue["person"]) if e.day == cue["day"]]
        return [hits[0].place] if hits else ["none"]
    if qtype == "act":
        with_obj = matching(episodes, obj=cue["obj"])
        if not with_obj:
            return ["none"]
        last = max(with_obj, key=lambda e: e.day)
        if last.partner is not None:
            raise ValueError("last handling has two people")
        return [max(matching(episodes, person=last.actor), key=lambda e: e.day).place]
    if qtype == "find":
        hits = matching(episodes, **cue)
        if len(hits) != 1 or hits[0].partner is not None:
            raise ValueError("find items need one event with one person")
        return [max(matching(episodes, person=hits[0].actor), key=lambda e: e.day).place]
    raise ValueError(qtype)


def _unique_everywhere(worlds, **cue) -> bool:
    return all(len(matching(w, **cue)) == 1 for w in worlds)


def _binding_needed(early, cue) -> bool:
    """Dropping any single cue detail leaves more than one early episode."""
    return all(len(matching(early, **{k: v for k, v in cue.items() if k != drop})) > 1
               for drop in cue)


def build_questions(world: dict, per_type: int = 8) -> dict:
    """Return {"public": {"phase1": [...], "final": [...]}, "gold": {...}, ...}."""
    seed, params = world["seed"], world["params"]
    eps = episodes_of(world)
    early = [e for e in eps if e.block == "early"]
    both = [episodes_of(generate_world(seed, overlap=o, **params)) for o in ("high", "low")]
    rng = HashRng(f"questions:{seed}:early")
    items: list[dict] = []

    def add(criterion, qtype, text, answer_type, cue, targets, phase1):
        gold = answer_for(eps, qtype, cue)
        if phase1:  # identical answer in both conditions and at both test points
            if not (all(answer_for(w, qtype, cue) == gold for w in both)
                    and answer_for(early, qtype, cue) == gold):
                raise AssertionError(f"unstable early item {qtype} {cue}")
        items.append({"criterion": criterion, "qtype": qtype, "text": text,
                      "answer_type": answer_type, "gold": gold, "targets": targets,
                      "phase1": phase1, "cue": cue})

    def pick(candidates, n):
        return rng.sample(candidates, min(n, len(candidates)))

    def words(past, **extra):
        return {"action": BASE[past], "past": past, **extra}

    # E2 binding recall: unique in every condition, and every cue detail is needed.
    seen, e2 = set(), []
    for e in early:
        for person in e.participants:
            for qtype, cue in (("object", dict(person=person, action=e.action, place=e.place)),
                               ("place", dict(person=person, action=e.action, obj=e.object)),
                               ("person", dict(action=e.action, place=e.place, obj=e.object))):
                key = (qtype, tuple(sorted(cue.items())))
                if (key in seen or not _unique_everywhere(both, **cue)
                        or not _binding_needed(early, cue)):
                    continue
                seen.add(key)
                e2.append((qtype, cue, e))
    for qtype, cue, e in pick(e2, 3 * per_type):
        text = rng.choice(PARA[qtype]).format(**words(e.action, person=cue.get("person"),
                                                      place=e.place, object=e.object))
        add("E2", qtype, text, qtype, cue, [e.episode_id], True)

    # E5 binding lures: every pair of cue details co-occurs in the EARLY block; the full
    # combination occurs in no condition at all.
    people = sorted({p for e in early for p in e.participants})
    places = sorted({e.place for e in early})
    objects = sorted({e.object for e in early})
    actions = sorted({e.action for e in early})
    lures = []
    for _ in range(4000):
        qtype = rng.choice(("object", "place", "person"))
        person, action, place, obj = (rng.choice(people), rng.choice(actions),
                                      rng.choice(places), rng.choice(objects))
        cue = {"object": dict(person=person, action=action, place=place),
               "place": dict(person=person, action=action, obj=obj),
               "person": dict(action=action, place=place, obj=obj)}[qtype]
        key = (qtype, tuple(sorted(cue.items())))
        if key in seen or any(matching(w, **cue) for w in both):
            continue
        keys = list(cue)
        if not all(matching(early, **{a: cue[a], b: cue[b]})
                   for i, a in enumerate(keys) for b in keys[i + 1:]):
            continue
        seen.add(key)
        lures.append((qtype, cue))
        if len(lures) >= 2 * per_type:
            break
    for qtype, cue in lures:
        text = rng.choice(PARA[qtype]).format(**words(cue["action"], person=cue.get("person"),
                                                      place=cue.get("place"),
                                                      object=cue.get("obj")))
        add("E5", qtype, text, qtype, cue, [], True)

    # E4 source: content (person, action, object) unique in every condition.
    e4 = [(person, e) for e in early for person in e.participants
          if _unique_everywhere(both, person=person, action=e.action, obj=e.object)]
    for person, e in pick(e4, per_type):
        cue = dict(person=person, action=e.action, obj=e.object)
        text = rng.choice(PARA["day"]).format(**words(e.action, person=person, object=e.object))
        add("E4", "day", text, "day", cue, [e.episode_id], True)

    # E3a order: two such events; pairs whose presentation order differs from day order first.
    pairs = [((pa, a), (pb, b)) for i, (pa, a) in enumerate(e4) for pb, b in e4[i + 1:]
             if a.day != b.day]
    mixed = [p for p in pairs if (p[0][1].position < p[1][1].position) != (p[0][1].day < p[1][1].day)]
    pairs = mixed + [p for p in pairs if p not in mixed]
    for (pa, a), (pb, b) in pairs[:per_type]:
        if rng.below(2):
            (pa, a), (pb, b) = (pb, b), (pa, a)
        cue = {"a": dict(person=pa, action=a.action, obj=a.object),
               "b": dict(person=pb, action=b.action, obj=b.object)}
        text = rng.choice(PARA["order"]).format(a=f"{pa} {a.action} the {a.object}.",
                                                b=f"{pb} {b.action} the {b.object}.")
        add("E3a", "order", text, "choice", cue, [a.episode_id, b.episode_id], True)

    # E3b place on a given early day.
    for person, e in pick([(p, e) for e in early for p in e.participants], per_type // 2):
        add("E3b", "at_day", rng.choice(PARA["at_day"]).format(person=person, day=e.day),
            "place", dict(person=person, day=e.day), [e.episode_id], True)

    # Final-only items, own stream per condition: latest place and E7 decisions.
    rng = HashRng(f"questions:{seed}:final:{world['overlap']}")
    for person in pick(sorted({p for e in eps for p in e.participants}), per_type // 2):
        last = max(matching(eps, person=person), key=lambda x: x.day)
        add("E3b", "latest", rng.choice(PARA["latest"]).format(person=person), "place",
            dict(person=person), [last.episode_id], False)
    for obj in sorted({e.object for e in eps}):
        last = max(matching(eps, obj=obj), key=lambda x: x.day)
        if last.partner is not None:
            continue
        seen_at = max(matching(eps, person=last.actor), key=lambda x: x.day)
        if seen_at.episode_id == last.episode_id or seen_at.place == last.place:
            continue  # the decision must need two episodes
        add("E7", "act", rng.choice(PARA["act"]).format(object=obj), "place", dict(obj=obj),
            [last.episode_id, seen_at.episode_id], False)
    finds = []
    for e in early:
        cue = dict(action=e.action, place=e.place, obj=e.object)
        if e.partner is not None or len(matching(eps, **cue)) != 1:
            continue
        seen_at = max(matching(eps, person=e.actor), key=lambda x: x.day)
        if seen_at.episode_id != e.episode_id and seen_at.place != e.place:
            finds.append((e, cue, seen_at))
    for e, cue, seen_at in pick(finds, per_type // 2):
        text = rng.choice(PARA["find"]).format(past=e.action, object=e.object, place=e.place)
        add("E7", "find", text, "place", cue, [e.episode_id, seen_at.episode_id], False)

    counts = {c: sum(i["criterion"] == c for i in items) for c in MINIMUM}
    short = {c: n for c, n in counts.items() if n < MINIMUM[c]}
    if short:
        raise ValueError(f"WORLD_TOO_SMALL:{short}")

    items = rng.shuffled(items)
    public = {"phase1": [], "final": []}
    gold = {}
    for item in items:
        # Content-derived id: the same early item has the same id in both conditions.
        qid = "q" + hashlib.sha256(json.dumps([item["criterion"], item["qtype"], item["cue"]],
                                              sort_keys=True).encode()).hexdigest()[:10]
        if qid in gold:
            raise AssertionError("duplicate item")
        record = {"qid": qid, "text": item["text"], "answer_type": item["answer_type"]}
        public["final"].append(record)
        if item["phase1"]:
            public["phase1"].append(record)
        gold[qid] = {k: item[k] for k in ("criterion", "qtype", "answer_type", "gold",
                                          "targets", "phase1", "cue")}
    return {"schema": QUESTION_SCHEMA, "public": public, "gold": gold, "counts": counts,
            "candidates": {"person": sorted({p for e in eps for p in e.participants}),
                           "place": sorted({e.place for e in eps}),
                           "object": sorted({e.object for e in eps})}}


def make_world(base_seed: str, index: int, max_attempts: int = 50) -> tuple[int, dict]:
    """World `index` of a series: the first attempt whose seed yields valid question sets
    in BOTH overlap conditions (protocol section 3). The rule depends only on the
    generator, never on any system's answers. Returns (attempt, {overlap: (world, qs)})."""
    for attempt in range(max_attempts):
        seed = f"{base_seed}-{index}-{attempt}"
        try:
            pair = {}
            for overlap in ("high", "low"):
                world = generate_world(seed, overlap=overlap)
                pair[overlap] = (world, build_questions(world))
            return attempt, pair
        except ValueError as exc:
            if not str(exc).startswith("WORLD_TOO_SMALL"):
                raise
    raise RuntimeError("no valid world within the attempt limit")
