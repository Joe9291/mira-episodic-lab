"""Synthetic episodic worlds (protocol section 3).

Invented people, places, objects and actions with deliberate feature overlap: the same
people, places and objects recur, so only a combination identifies an episode (binding).
One event per day. An early block is followed by K follow-up episodes that either
overlap strongly with it (competing) or use disjoint names (low overlap), for E6.

The early block depends on the seed only (its own random stream), so the "high" and
"low" conditions of one seed share exactly the same early episodes; only the follow-ups
differ. About a third of the early episodes are moved later in the narration, and at
least one is always told out of chronological order (E3a).
Episode identifiers are random tokens and reveal no order (E4).

Every fact a question can ask about is generated here, never by a model.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .rng import HashRng

WORLD_SCHEMA = "episodic_lab.world.v3"

FIRST = ("Varo", "Ilsen", "Tamric", "Odile", "Brenna", "Casimo", "Yelda", "Fenwick",
         "Marit", "Quillon", "Sabeth", "Dorran", "Elvie", "Gorvin", "Halsey", "Juno")
LAST = ("Tellin", "Marrow", "Quist", "Ambery", "Corland", "Vesk", "Pellow", "Drummet",
        "Haverl", "Ostrin", "Lunsey", "Brack")
PLACE_STEM = ("Brannick", "Mossgate", "Wyndle", "Carrow", "Ellsmere", "Thornby",
              "Quarrel", "Fenhollow", "Ashgrove", "Lindmere", "Pellan", "Sorrow")
PLACE_KIND = ("Mill", "Harbour", "Library", "Market", "Bridge", "Orchard", "Forge",
              "Chapel", "Station", "Garden")
OBJ_ADJ = ("copper", "blue", "cracked", "heavy", "tiny", "silver", "wooden", "striped")
OBJ_NOUN = ("lantern", "ledger", "kettle", "compass", "violin", "map", "basket",
            "telescope", "clock", "umbrella", "ladder", "mirror")
ACTIONS = ("repaired", "painted", "sold", "hid", "found", "measured", "cleaned", "carried")
PARTICIPLE = {"hid": "hidden"}

IN_ORDER = (
    "On day {day}, {actor} {action} the {object} at {place}{partner}.",
    "Day {day}: at {place}, {actor}{partner} {action} the {object}.",
    "{actor} was at {place} on day {day} and {action} the {object}{partner}.",
)
OUT_OF_ORDER = (
    "Looking back to day {day}: {actor} {action} the {object} at {place}{partner}.",
    "Earlier, on day {day}, {actor}{partner} had {participle} the {object} at {place}.",
)


@dataclass(frozen=True)
class Episode:
    episode_id: str
    day: int
    actor: str
    partner: str | None
    place: str
    action: str
    object: str
    block: str            # "early" or "followup"
    position: int         # presentation position (0-based)
    out_of_order: bool
    text: str

    @property
    def participants(self) -> tuple[str, ...]:
        return (self.actor,) if self.partner is None else (self.actor, self.partner)


def _pool(rng: HashRng, people: int, places: int, objects: int, actions: int,
          used: dict) -> dict:
    """Draw pools that reuse no first name, place stem, object noun or action in `used`."""
    firsts = rng.sample([f for f in FIRST if f not in used["first"]], people)
    stems = rng.sample([s for s in PLACE_STEM if s not in used["stem"]], places)
    nouns = rng.sample([n for n in OBJ_NOUN if n not in used["noun"]], objects)
    verbs = rng.sample([a for a in ACTIONS if a not in used["action"]], actions)
    used["first"].update(firsts)
    used["stem"].update(stems)
    used["noun"].update(nouns)
    used["action"].update(verbs)
    return {"people": [f"{first} {rng.choice(LAST)}" for first in firsts],
            "places": [f"{stem} {rng.choice(PLACE_KIND)}" for stem in stems],
            "objects": [f"{rng.choice(OBJ_ADJ)} {noun}" for noun in nouns],
            "actions": verbs}


def _event(rng: HashRng, pool: dict, day: int, block: str) -> dict:
    actor = rng.choice(pool["people"])
    partner = rng.choice([p for p in pool["people"] if p != actor]) if rng.below(3) == 0 else None
    return {"day": day, "actor": actor, "partner": partner, "place": rng.choice(pool["places"]),
            "action": rng.choice(pool["actions"]), "object": rng.choice(pool["objects"]),
            "block": block}


def _render(rng: HashRng, event: dict, late: bool) -> str:
    partner = f" together with {event['partner']}" if event["partner"] else ""
    return rng.choice(OUT_OF_ORDER if late else IN_ORDER).format(
        day=event["day"], actor=event["actor"], action=event["action"],
        participle=PARTICIPLE.get(event["action"], event["action"]), object=event["object"],
        place=event["place"], partner=partner)


def _token(rng: HashRng, taken: set) -> str:
    while True:
        token = "ep-" + "".join(rng.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(6))
        if token not in taken:
            taken.add(token)
            return token


def generate_world(seed: str, early: int = 30, followup: int = 10, overlap: str = "high",
                   people: int = 4, places: int = 4, objects: int = 4, actions: int = 4) -> dict:
    """Return a world; `overlap` is "high" (follow-ups reuse the early pools) or "low"."""
    if overlap not in ("high", "low"):
        raise ValueError("overlap must be 'high' or 'low'")
    if not (4 <= early <= 200 and 0 <= followup <= 200 and 3 <= people <= 8
            and 2 <= places <= 6 and 2 <= objects <= 6 and 2 <= actions <= 4):
        raise ValueError("world size out of range")
    params = {"early": early, "followup": followup, "people": people, "places": places,
              "objects": objects, "actions": actions}

    # Early block: seed-only stream, identical for both overlap conditions.
    rng_e = HashRng(f"world:{seed}:early")
    used = {"first": set(), "stem": set(), "noun": set(), "action": set()}
    early_pool = _pool(rng_e, people, places, objects, actions, used)
    early_events = [_event(rng_e, early_pool, day, "early") for day in range(1, early + 1)]
    order = list(range(early))
    for _ in range(max(1, early // 3)):
        index = rng_e.below(early - 1)
        item = order.pop(index)
        order.insert(index + 1 + rng_e.below(early - index - 1), item)
    if order == sorted(order):  # guarantee at least one out-of-order narration
        order[0], order[1] = order[1], order[0]
    taken: set[str] = set()
    rendered = []
    for position, index in enumerate(order):
        event = early_events[index]
        late = any(early_events[j]["day"] > event["day"] for j in order[:position])
        rendered.append((event, position, late, _render(rng_e, event, late), _token(rng_e, taken)))

    # Follow-up block: its own stream per condition.
    rng_f = HashRng(f"world:{seed}:followup:{overlap}")
    follow_pool = (early_pool if overlap == "high"
                   else _pool(rng_f, people, places, objects, actions, used))
    for k in range(followup):
        event = _event(rng_f, follow_pool, early + 1 + k, "followup")
        rendered.append((event, early + k, False, _render(rng_f, event, False), _token(rng_f, taken)))

    episodes = [Episode(token, ev["day"], ev["actor"], ev["partner"], ev["place"], ev["action"],
                        ev["object"], ev["block"], pos, late, text)
                for ev, pos, late, text, token in rendered]
    return {"schema": WORLD_SCHEMA, "seed": seed, "overlap": overlap, "params": params,
            "early_pool": early_pool, "followup_pool": follow_pool,
            "episodes": [asdict(e) for e in episodes]}


def episodes_of(world: dict) -> list[Episode]:
    return [Episode(**e) for e in world["episodes"]]


def vocabulary(world: dict) -> dict:
    """All people, places and objects that occur anywhere in the world."""
    result = {"people": set(), "places": set(), "objects": set(), "actions": set()}
    for pool in (world["early_pool"], world["followup_pool"]):
        for key in result:
            result[key].update(pool[key])
    return {k: sorted(v) for k, v in result.items()}
