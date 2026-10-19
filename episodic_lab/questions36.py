"""Round 3.6 question wordings (docs/ROUND_3_6.md, design v3, section 2).

Supported question types (the goals of rounds 3.3/3.4) with the template and 3
development, 3 holdout and 3 reserve paraphrases; control families (ambiguous: pronoun,
bare noun, first name; unsupported: why, count, future, ownership, event-relative,
who-did) with one wording per group. Placeholders: {o} object (adjective + noun), {x}
person (first + last name), {noun} a bare noun, {first} a first name, {p} a place.
Development uses only the template and the development wordings. `parse` is the exact
inverse of `render` for every wording (model-free roundtrip audit).
"""
from __future__ import annotations

import hashlib
import re

SUPPORTED = ("object_current", "object_first", "object_previous", "person_current", "person_first",
             "person_previous", "giver")
UNSUPPORTED = "unsupported"
INTENTS = SUPPORTED + (UNSUPPORTED,)
OBJECT_TYPES = ("object_current", "object_first", "object_previous", "giver")
PERSON_TYPES = ("person_current", "person_first", "person_previous")
GROUPS = ("template", "dev", "holdout", "reserve")
SETS = {"dev": ("template", "dev"), "holdout": ("holdout",), "reserve": ("reserve",)}

TYPES = {
    "object_current": {
        "template": ["Find the {o}."],
        "dev": ["Where is the {o} now?", "Take me to the {o}.", "I need the {o} - where is it?"],
        "holdout": ["Where can I find the {o} at the moment?", "Go get the {o}.", "Which place has the {o} right now?"],
        "reserve": ["Locate the {o}.", "Where should I look for the {o}?", "Head to wherever the {o} is."]},
    "object_first": {
        "template": ["Go to where the {o} was first placed."],
        "dev": ["Where was the {o} put the very first time?", "Take me to the first place the {o} was put.",
                "Where did the {o} start out?"],
        "holdout": ["Where was the {o} originally placed?", "Go to the {o}'s first location.",
                    "Before all the moving, where was the {o} put?"],
        "reserve": ["Where did the {o} get placed first?", "Show me where the {o} was put initially.",
                    "Which place did the {o} land in first?"]},
    "object_previous": {
        "template": ["Go to where the {o} was before it was last placed."],
        "dev": ["Where was the {o} before its last move?",
                "Go to the place the {o} was in before it was last put somewhere.",
                "Where had the {o} been just before it was last placed?"],
        "holdout": ["Where was the {o} prior to the latest placing?", "Take me to the {o}'s previous spot.",
                    "Before the {o} was put where it is now, where was it?"],
        "reserve": ["Where did the {o} sit before its most recent placing?", "Go to the {o}'s second-to-last place.",
                    "One move back, where was the {o}?"]},
    "person_current": {
        "template": ["Find {x}."],
        "dev": ["Where is {x} now?", "Go to {x}.", "Take me to where {x} was last seen."],
        "holdout": ["Where can I meet {x}?", "Head to {x}'s last known spot.", "Where did you see {x} most recently?"],
        "reserve": ["Find where {x} is.", "Where was {x} last spotted?", "Go wherever {x} was last."]},
    "person_first": {
        "template": ["Go to where you first saw {x}."],
        "dev": ["Where did you see {x} for the first time?", "Go to the place where {x} first appeared.",
                "Where was {x} when you first saw them?"],
        "holdout": ["Take me to where you originally saw {x}.", "Where did you first come across {x}?",
                    "Go to {x}'s earliest known place."],
        "reserve": ["Where did {x} first show up?", "Head to the first place you saw {x}.",
                    "Your first sighting of {x} - where was it?"]},
    "person_previous": {
        "template": ["Go to where you saw {x} before you last saw them."],
        "dev": ["Where did you see {x} before the last time?", "Go to where {x} was seen before the latest sighting.",
                "Where was {x} the time before you last saw them?"],
        "holdout": ["Take me to {x}'s previous location.", "Before the most recent sighting, where was {x}?",
                    "Where did you see {x} one time before the last?"],
        "reserve": ["Where was {x} seen just before the last sighting?", "Go back one sighting: where was {x}?",
                    "Where did {x} appear before their latest appearance?"]},
    "giver": {
        "template": ["Find the person who gave you the {o}."],
        "dev": ["Who gave you the {o}? Go to them.", "Go to the person you got the {o} from.",
                "Find whoever handed you the {o}."],
        "holdout": ["Take me to the one who gave you the {o}.", "Where is the person the {o} came from?",
                    "Go find the giver of the {o}."],
        "reserve": ["The {o} - who gave it to you? Find them.", "Locate the person who passed you the {o}.",
                    "Where is whoever gave you the {o}?"]},
}
# ambiguous families: (wording, gold intent) per group
AMBIGUOUS = {
    "pronoun": {"dev": [("Where is it now?", "object_current")],
                "holdout": [("Where did they put it first?", "object_first")],
                "reserve": [("Find it.", "object_current")]},
    "bare_noun": {"dev": [("Find the {noun}.", "object_current")],
                  "holdout": [("Take me to the {noun}.", "object_current")],
                  "reserve": [("Where was the {noun} placed first?", "object_first")]},
    "first_name": {"dev": [("Go to {first}.", "person_current")],
                   "holdout": [("Where is {first} now?", "person_current")],
                   "reserve": [("Locate {first}.", "person_current")]},
}
UNSUPPORTED_FAMILIES = {
    "why": {"dev": ["Why did {x} put the {o} there?"], "holdout": ["Why was the {o} hidden?"],
            "reserve": ["For what reason did {x} leave the {o} behind?"]},
    "count": {"dev": ["How many times was the {o} moved?"], "holdout": ["How often did you see {x}?"],
              "reserve": ["How many people have you seen?"]},
    "future": {"dev": ["Where will the {o} be tomorrow?"], "holdout": ["Who will take the {o} next?"],
               "reserve": ["Where is {x} going to be next week?"]},
    "ownership": {"dev": ["Who does the {o} belong to?"], "holdout": ["Who owns the {o}?"],
                  "reserve": ["Whose {o} is it?"]},
    "event_relative": {"dev": ["Where was {x} right before they gave you the {o}?"],
                       "holdout": ["Where was the {o} just before you met {x}?"],
                       "reserve": ["Where did you go after {x} handed you the {o}?"]},
    "who_did": {"dev": ["Who put the {o} at {p}?"], "holdout": ["Which person hid the {o}?"],
                "reserve": ["Who was the last person to move the {o}?"]},
}

_SLOT_RE = {"o": r"(?P<o>[a-z]+ [a-z]+)", "x": r"(?P<x>[A-Z][a-z]+ [A-Z][a-z]+)", "noun": r"(?P<noun>[a-z]+)",
            "first": r"(?P<first>[A-Z][a-z]+)", "p": r"(?P<p>[A-Z][a-z]+ [A-Z][a-z]+)"}


def wording_id(family: str, group: str, idx: int) -> str:
    return f"{family}:{group}:{idx}"


def wordings(family: str, group: str) -> list[str]:
    """The wordings of a family in a group (template only for supported types)."""
    if family in TYPES:
        return TYPES[family].get(group, [])
    if family in AMBIGUOUS:
        return [w for w, _ in AMBIGUOUS[family].get(group, [])]
    return UNSUPPORTED_FAMILIES[family].get(group, [])


def ambiguous_intent(family: str, group: str, idx: int) -> str:
    return AMBIGUOUS[family][group][idx][1]


def is_constant(template: str) -> bool:
    return "{" not in template


def placeholders(template: str) -> list[str]:
    return re.findall(r"\{(\w+)\}", template)


def render(template: str, fill: dict) -> str:
    return template.format(**{k: fill[k] for k in placeholders(template)})


def parse(text: str, template: str) -> dict | None:
    """Exact inverse of render: the fill of every placeholder, or None."""
    pattern = ""
    for part in re.split(r"(\{\w+\})", template):
        m = re.fullmatch(r"\{(\w+)\}", part)
        pattern += _SLOT_RE[m.group(1)] if m else re.escape(part)
    m = re.fullmatch(pattern, text)
    return m.groupdict() if m else None


def choose(options: list, key: str):
    """Deterministic uniform choice by SHA-256 of the key."""
    return options[int(hashlib.sha256(key.encode()).hexdigest(), 16) % len(options)]
