"""Synthetic episodic worlds: invented people, places and events, one event per day.

Every fact a question can ask about is generated here and nowhere else, so ground
truth never depends on a language model and no model can know a world in advance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .rng import HashRng

WORLD_SCHEMA = "episodic_lab.world.v1"

FIRST = ("Varo", "Ilsen", "Tamric", "Odile", "Brenna", "Casimo", "Yelda", "Fenwick",
         "Marit", "Quillon", "Sabeth", "Dorran", "Elvie", "Gorvin", "Halsey", "Juno")
LAST = ("Tellin", "Marrow", "Quist", "Ambery", "Corland", "Vesk", "Pellow", "Drummet",
        "Haverl", "Ostrin", "Lunsey", "Brack")
PLACE_STEM = ("Brannick", "Mossgate", "Wyndle", "Carrow", "Ellsmere", "Thornby",
              "Quarrel", "Fenhollow", "Ashgrove", "Lindmere")
PLACE_KIND = ("Mill", "Harbour", "Library", "Market", "Bridge", "Orchard", "Forge",
              "Chapel", "Station", "Garden")
OBJ_ADJ = ("copper", "blue", "cracked", "heavy", "tiny", "silver", "wooden", "striped")
OBJ_NOUN = ("lantern", "ledger", "kettle", "compass", "violin", "map", "basket",
            "telescope", "clock", "umbrella")
ACTIONS = ("repaired", "painted", "sold", "hid", "found", "measured", "cleaned", "carried")

TEMPLATES = (
    "On day {day}, {actor} {action} the {object} at {place}{partner}.",
    "Day {day}: at {place}, {actor}{partner} {action} the {object}.",
    "{actor} was at {place} on day {day} and {action} the {object}{partner}.",
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
    text: str


def _distinct(rng: HashRng, make, count: int) -> list[str]:
    seen: list[str] = []
    while len(seen) < count:
        value = make()
        if value not in seen:
            seen.append(value)
    return seen


def generate_world(seed: str, episodes: int = 40, people: int = 8, places: int = 6,
                   objects: int = 10) -> dict:
    if not (4 <= people <= len(FIRST) and 2 <= places <= len(PLACE_STEM)
            and 2 <= objects <= len(OBJ_NOUN) and 4 <= episodes <= 400):
        raise ValueError("world size out of range")
    rng = HashRng(f"world:{seed}")
    firsts = rng.sample(FIRST, people)
    person_names = [f"{first} {rng.choice(LAST)}" for first in firsts]
    place_names = _distinct(rng, lambda: f"{rng.choice(PLACE_STEM)} {rng.choice(PLACE_KIND)}", places)
    nouns = rng.sample(OBJ_NOUN, objects)
    object_names = [f"{rng.choice(OBJ_ADJ)} {noun}" for noun in nouns]

    items: list[Episode] = []
    for index in range(episodes):
        day = index + 1
        actor = rng.choice(person_names)
        partner = None
        if rng.below(2) == 1:
            partner = rng.choice([p for p in person_names if p != actor])
        place = rng.choice(place_names)
        action = rng.choice(ACTIONS)
        obj = rng.choice(object_names)
        template = rng.choice(TEMPLATES)
        text = template.format(day=day, actor=actor, action=action, object=obj, place=place,
                               partner=f" together with {partner}" if partner else "")
        items.append(Episode(f"e{day:03d}", day, actor, partner, place, action, obj, text))
    return {
        "schema": WORLD_SCHEMA,
        "seed": seed,
        "people": person_names,
        "places": place_names,
        "objects": object_names,
        "actions": list(ACTIONS),
        "episodes": [asdict(e) for e in items],
    }


def episodes_of(world: dict) -> list[Episode]:
    return [Episode(**e) for e in world["episodes"]]
