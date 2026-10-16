"""Synthetic episodic worlds (protocol section 3).

Invented people, places, objects and actions with deliberate feature overlap: the same
people, places and objects recur, so only a combination identifies an episode (binding).
One event per day. An early block is followed by K follow-up episodes that either
overlap strongly with it (competing) or use disjoint names (low overlap), for E6.
Some early episodes are told out of chronological order (E3a). Episode identifiers are
random tokens and reveal no order (E4).

Every fact a question can ask about is generated here, never by a model.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .rng import HashRng

WORLD_SCHEMA = "episodic_lab.world.v2"

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


def _pools(rng: HashRng, people: int, places: int, objects: int, used: dict) -> dict:
    """Draw name pools that do not reuse any first name, place or object noun in `used`."""
    firsts = rng.sample([f for f in FIRST if f not in used["first"]], people)
    person_names = [f"{first} {rng.choice(LAST)}" for first in firsts]
    stems = rng.sample([s for s in PLACE_STEM if s not in used["stem"]], places)
    place_names = [f"{stem} {rng.choice(PLACE_KIND)}" for stem in stems]
    nouns = rng.sample([n for n in OBJ_NOUN if n not in used["noun"]], objects)
    object_names = [f"{rng.choice(OBJ_ADJ)} {noun}" for noun in nouns]
    used["first"].update(firsts)
    used["stem"].update(stems)
    used["noun"].update(nouns)
    return {"people": person_names, "places": place_names, "objects": object_names}


def _event(rng: HashRng, pool: dict, day: int) -> dict:
    actor = rng.choice(pool["people"])
    partner = rng.choice([p for p in pool["people"] if p != actor]) if rng.below(3) == 0 else None
    return {"day": day, "actor": actor, "partner": partner, "place": rng.choice(pool["places"]),
            "action": rng.choice(ACTIONS), "object": rng.choice(pool["objects"])}


def _token(rng: HashRng) -> str:
    return "ep-" + "".join(rng.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(6))


def generate_world(seed: str, early: int = 12, followup: int = 8, overlap: str = "high",
                   people: int = 5, places: int = 4, objects: int = 5) -> dict:
    """Return a world; `overlap` is "high" (follow-ups reuse the early pools) or "low"."""
    if overlap not in ("high", "low"):
        raise ValueError("overlap must be 'high' or 'low'")
    if not (4 <= early <= 200 and 0 <= followup <= 200 and 3 <= people <= 8
            and 2 <= places <= 6 and 2 <= objects <= 6):
        raise ValueError("world size out of range")
    rng = HashRng(f"world:{seed}:{overlap}")
    used = {"first": set(), "stem": set(), "noun": set()}
    early_pool = _pools(rng, people, places, objects, used)
    follow_pool = early_pool if overlap == "high" else _pools(rng, people, places, objects, used)

    events = [dict(_event(rng, early_pool, day), block="early") for day in range(1, early + 1)]
    events += [dict(_event(rng, follow_pool, day), block="followup")
               for day in range(early + 1, early + followup + 1)]

    # Presentation order: chronological, except that about a quarter of the early
    # episodes are moved to a later position inside the early block.
    order = list(range(early))
    for _ in range(max(1, early // 4)):
        index = rng.below(early - 1)
        item = order.pop(index)
        new_pos = index + 1 + rng.below(early - index - 1) if early - index - 1 > 0 else index
        order.insert(new_pos, item)
    order += list(range(early, early + followup))

    tokens: set[str] = set()
    episodes: list[Episode] = []
    for position, index in enumerate(order):
        event = events[index]
        late = any(events[j]["day"] > event["day"] for j in order[:position])
        templates = OUT_OF_ORDER if late else IN_ORDER
        partner_text = f" together with {event['partner']}" if event["partner"] else ""
        text = rng.choice(templates).format(day=event["day"], actor=event["actor"],
                                            action=event["action"],
                                            participle=PARTICIPLE.get(event["action"], event["action"]),
                                            object=event["object"],
                                            place=event["place"], partner=partner_text)
        token = _token(rng)
        while token in tokens:
            token = _token(rng)
        tokens.add(token)
        episodes.append(Episode(token, event["day"], event["actor"], event["partner"],
                                event["place"], event["action"], event["object"],
                                event["block"], position, late, text))
    return {
        "schema": WORLD_SCHEMA,
        "seed": seed,
        "overlap": overlap,
        "early_pool": early_pool,
        "followup_pool": follow_pool,
        "actions": list(ACTIONS),
        "episodes": [asdict(e) for e in episodes],
    }


def episodes_of(world: dict) -> list[Episode]:
    return [Episode(**e) for e in world["episodes"]]


def vocabulary(world: dict) -> dict:
    """All people, places and objects that occur anywhere in the world."""
    result = {"people": set(), "places": set(), "objects": set()}
    for pool in (world["early_pool"], world["followup_pool"]):
        result["people"].update(pool["people"])
        result["places"].update(pool["places"])
        result["objects"].update(pool["objects"])
    return {k: sorted(v) for k, v in result.items()}
