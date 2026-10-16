"""Question sets with ground truth for a world (protocol sections 2 and 3).

Two test points: `phase1` right after the early block (only questions whose answer is
the same before and after the follow-ups) and `final` after all episodes. The public
question files carry no answers; the gold file is for the evaluator only.
"""
from __future__ import annotations

from .rng import HashRng
from .world import Episode, episodes_of

QUESTION_SCHEMA = "episodic_lab.questions.v1"

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
    "act": ("You want to give the {object} back to the last person who had it. "
            "To which place do you go to find that person?",
            "The {object} must go back to whoever last had it. Which place do you visit "
            "to meet that person?"),
}
BASE = {"repaired": "repair", "painted": "paint", "sold": "sell", "hid": "hide",
        "found": "find", "measured": "measure", "cleaned": "clean", "carried": "carry"}


def _match(episodes, person=None, action=None, place=None, obj=None):
    return [e for e in episodes
            if (person is None or person in e.participants)
            and (action is None or e.action == action)
            and (place is None or e.place == place)
            and (obj is None or e.object == obj)]


def _describe(e: Episode, person: str) -> str:
    return f"{person} {e.action} the {e.object}."


def build_questions(world: dict, per_type: int = 8) -> dict:
    """Return {"public": {"phase1": [...], "final": [...]}, "gold": {qid: {...}}}."""
    rng = HashRng(f"questions:{world['seed']}:{world['overlap']}")
    eps = episodes_of(world)
    early = [e for e in eps if e.block == "early"]
    people = sorted({p for e in eps for p in e.participants})
    places = sorted({e.place for e in eps})
    objects = sorted({e.object for e in eps})
    actions = sorted({e.action for e in eps})
    items: list[dict] = []

    def add(criterion, qtype, text, answer_type, gold, targets, phase1, cue=None):
        items.append({"criterion": criterion, "qtype": qtype, "text": text,
                      "answer_type": answer_type, "gold": gold, "targets": targets,
                      "phase1": phase1, "cue": cue})

    def pick(candidates, n):
        return rng.sample(candidates, min(n, len(candidates)))

    # E2 binding recall and E5 lures (same templates); targets in the early block only,
    # uniqueness and absence checked over the WHOLE world, so phase1 and final agree.
    seen = set()
    e2 = []
    for e in early:
        for person in e.participants:
            for qtype, cue in (("object", dict(person=person, action=e.action, place=e.place)),
                               ("place", dict(person=person, action=e.action, obj=e.object)),
                               ("person", dict(action=e.action, place=e.place, obj=e.object))):
                key = (qtype, tuple(sorted(cue.items())))
                if key in seen or len(_match(eps, **cue)) != 1:
                    continue
                seen.add(key)
                e2.append((qtype, cue, e))
    for qtype, cue, e in pick(e2, 3 * per_type):
        fill = {"person": cue.get("person"), "action": BASE[e.action], "past": e.action,
                "place": e.place, "object": e.object}
        gold = {"object": [e.object], "place": [e.place], "person": list(e.participants)}[qtype]
        add("E2", qtype, rng.choice(PARA[qtype]).format(**fill), qtype, gold, [e.episode_id], True)

    lures = []
    for _ in range(400):
        qtype = rng.choice(("object", "place", "person"))
        person, action, place, obj = (rng.choice(people), rng.choice(actions),
                                      rng.choice(places), rng.choice(objects))
        cue = {"object": dict(person=person, action=action, place=place),
               "place": dict(person=person, action=action, obj=obj),
               "person": dict(action=action, place=place, obj=obj)}[qtype]
        # Lure: every detail occurs in the world, but never in this combination; each
        # pair of cue details does co-occur somewhere, so single facts do not reveal it.
        if _match(eps, **cue):
            continue
        keys = list(cue)
        if not all(_match(eps, **{a: cue[a], b: cue[b]}) for i, a in enumerate(keys)
                   for b in keys[i + 1:]):
            continue
        key = (qtype, tuple(sorted(cue.items())))
        if key in seen:
            continue
        seen.add(key)
        lures.append((qtype, cue))
        if len(lures) >= 2 * per_type:
            break
    for qtype, cue in lures:
        fill = {"person": cue.get("person"), "action": BASE[cue["action"]],
                "past": cue["action"], "place": cue.get("place"), "object": cue.get("obj")}
        add("E5", qtype, rng.choice(PARA[qtype]).format(**fill), qtype, ["none"], [], True,
            cue=cue)

    # E4 source: content (person, action, object) unique, asked for the day.
    e4 = []
    for e in early:
        for person in e.participants:
            if len(_match(eps, person=person, action=e.action, obj=e.object)) == 1:
                e4.append((person, e))
    for person, e in pick(e4, per_type):
        text = rng.choice(PARA["day"]).format(person=person, action=BASE[e.action],
                                              past=e.action, object=e.object)
        add("E4", "day", text, "day", [str(e.day)], [e.episode_id], True)

    # E3a order: two uniquely described events with different days; prefer pairs whose
    # presentation order differs from their day order.
    described = [(person, e) for person, e in e4]
    pairs = []
    for i, (pa, a) in enumerate(described):
        for pb, b in described[i + 1:]:
            if a.day != b.day:
                pairs.append(((pa, a), (pb, b), (a.position < b.position) != (a.day < b.day)))
    pairs = [p for p in pairs if p[2]] + [p for p in pairs if not p[2]]
    for (pa, a), (pb, b), _ in pairs[:per_type]:
        if rng.below(2):
            (pa, a), (pb, b) = (pb, b), (pa, a)
        text = rng.choice(PARA["order"]).format(a=_describe(a, pa), b=_describe(b, pb))
        add("E3a", "order", text, "choice", ["A" if a.day < b.day else "B"],
            [a.episode_id, b.episode_id], True)

    # E3b state: latest place (final only) and place on a given day (both phases when
    # the day lies in the early block).
    for person in pick(people, per_type // 2):
        mine = _match(eps, person=person)
        if mine:
            last = max(mine, key=lambda x: x.day)
            add("E3b", "latest", rng.choice(PARA["latest"]).format(person=person), "place",
                [last.place], [last.episode_id], False)
    at_day = [(p, e) for e in early for p in e.participants]
    for person, e in pick(at_day, per_type // 2):
        add("E3b", "at_day", rng.choice(PARA["at_day"]).format(person=person, day=e.day),
            "place", [e.place], [e.episode_id], True)

    # E7 action: needs the latest episode with the object (its actor, no partner) AND
    # that person's latest episode, at a different place.
    for obj in pick(objects, len(objects)):
        with_obj = _match(eps, obj=obj)
        if not with_obj:
            continue
        first = max(with_obj, key=lambda x: x.day)
        if first.partner is not None:
            continue
        second = max(_match(eps, person=first.actor), key=lambda x: x.day)
        if second.episode_id == first.episode_id or second.place == first.place:
            continue
        add("E7", "act", rng.choice(PARA["act"]).format(object=obj), "place",
            [second.place], [first.episode_id, second.episode_id], False)

    items = rng.shuffled(items)
    public = {"phase1": [], "final": []}
    gold = {}
    for n, item in enumerate(items):
        qid = f"q{n:03d}"
        record = {"qid": qid, "text": item["text"], "answer_type": item["answer_type"]}
        public["final"].append(record)
        if item["phase1"]:
            public["phase1"].append(record)
        gold[qid] = {k: item[k] for k in ("criterion", "qtype", "answer_type", "gold",
                                          "targets", "phase1", "cue")}
    return {"schema": QUESTION_SCHEMA, "public": public, "gold": gold,
            "candidates": {"person": people, "place": places, "object": objects}}
