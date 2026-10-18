"""Round 3.5 wordings (docs/ROUND_3_5.md section 1), fixed before any model run.

Per event type: the round 3.3 template, 3 development paraphrases, 3 holdout paraphrases
and 3 reserve paraphrases. Development, calibration and audit worlds use only the
template and the development paraphrases; the holdout and reserve paraphrases are never
used for any choice of model, prompts, normalisation, candidate generator or thresholds.

Placeholders: {x} person, {o} object, {p} place, {d} day, {v} past verb (hid/left/put),
{vb} base form (hide/leave/put), {vpp} participle (hidden/left/put). Every template has an
exact inverse parser (`parse`), used for the meaning-preservation roundtrip; a person
additionally checks one rendered example per template (independent meaning check).
"""
from __future__ import annotations

import hashlib
import re

SELF = "You"
VERBS = {"hid": ("hide", "hidden"), "left": ("leave", "left"), "put": ("put", "put")}

WORDINGS = {
    "placing": {  # an observed person places an object: actor x, action v, object o, place p
        "template": ["On day {d}, you saw {x} {v} the {o} at {p}."],
        "dev": ["Day {d}: at {p}, you watched {x} {vb} the {o}.",
                "You saw that {x} {v} the {o} at {p} on day {d}.",
                "At {p} on day {d}, {x} {v} the {o} while you were watching."],
        "holdout": ["The {o} was {vpp} at {p} by {x} on day {d}, and you saw it.",
                    "It was day {d} when you saw {x} {vb} the {o} at {p}.",
                    "{x} {v} the {o} at {p}, which you saw happen on day {d}."],
        "reserve": ["You were at {p} on day {d} and saw {x} {vb} the {o} there.",
                    "On day {d}, at {p}, the {o} was {vpp} by {x}, as you saw.",
                    "You noticed on day {d} that {x} {v} the {o} at {p}."],
    },
    "own_put": {  # the agent puts an object somewhere: actor You, action put
        "template": ["On day {d}, you put the {o} at {p}."],
        "dev": ["Day {d}: you put the {o} down at {p}.",
                "You placed the {o} at {p} on day {d}.",
                "At {p}, on day {d}, you put the {o} away."],
        "holdout": ["On day {d} the {o} was put at {p} by you.",
                    "It was day {d} when you set the {o} down at {p}.",
                    "You went to {p} on day {d} and put the {o} there."],
        "reserve": ["I put the {o} at {p} on day {d}.",
                    "The {o} ended up at {p} on day {d}, because you put it there.",
                    "On day {d}, you were the one who put the {o} at {p}."],
    },
    "gave": {  # a person gives the agent an object: actor x, partner You, action gave
        "template": ["On day {d}, {x} gave you the {o} at {p}."],
        "dev": ["Day {d}: at {p}, {x} handed you the {o}.",
                "You got the {o} from {x} at {p} on day {d}.",
                "At {p} on day {d}, {x} gave the {o} to you."],
        "holdout": ["You were given the {o} by {x} at {p} on day {d}.",
                    "On day {d}, the {o} came to you from {x}, at {p}.",
                    "It was day {d} at {p} when {x} passed you the {o}."],
        "reserve": ["{x} gave me the {o} at {p} on day {d}.",
                    "At {p}, on day {d}, you received the {o} from {x}.",
                    "On day {d} {x} handed the {o} over to you at {p}."],
    },
    "seen": {  # the agent sees a person somewhere: actor x, action was
        "template": ["On day {d}, you saw {x} at {p}."],
        "dev": ["Day {d}: {x} was at {p}.",
                "You met {x} at {p} on day {d}.",
                "At {p} on day {d}, you spotted {x}."],
        "holdout": ["{x} was seen by you at {p} on day {d}.",
                    "On day {d}, {x} was standing at {p} when you passed.",
                    "It was day {d} when you ran into {x} at {p}."],
        "reserve": ["I saw {x} at {p} on day {d}.",
                    "At {p}, {x} crossed your path on day {d}.",
                    "On day {d} you caught sight of {x} at {p}."],
    },
    "went": {  # the agent goes somewhere: actor You, action went
        "template": ["On day {d}, you went to {p}."],
        "dev": ["Day {d}: you walked to {p}.",
                "You visited {p} on day {d}.",
                "On day {d} you made your way to {p}."],
        "holdout": ["{p} was where you went on day {d}.",
                    "On day {d}, you travelled to {p}.",
                    "It was day {d} when you headed to {p}."],
        "reserve": ["I went to {p} on day {d}.",
                    "You arrived at {p} on day {d}.",
                    "On day {d}, your way led you to {p}."],
    },
}
SETS = {"dev": ("template", "dev"), "holdout": ("holdout",), "reserve": ("reserve",)}
_GROUPS = {"x": r"(?P<x>[A-Z][a-z]+ [A-Z][a-z]+)", "p": r"(?P<p>[A-Z][a-z]+ [A-Z][a-z]+)",
           "o": r"(?P<o>[a-z]+ [a-z]+)", "d": r"(?P<d>\d+)", "v": r"(?P<v>hid|left|put)",
           "vb": r"(?P<vb>hide|leave|put)", "vpp": r"(?P<vpp>hidden|left|put)"}


def event_type(c: dict) -> str:
    """Event type of a structured record content (round 3.3 schema)."""
    if c["action"] == "gave":
        return "gave"
    if c["action"] == "was":
        return "seen"
    if c["action"] == "went":
        return "went"
    return "own_put" if c["actor"] == SELF else "placing"


def frames(etype: str, wording_set: str) -> list[tuple[str, int, str]]:
    """[(group, index, template)] of an event type in a wording set."""
    return [(g, i, t) for g in SETS[wording_set] for i, t in enumerate(WORDINGS[etype][g])]


def frame_id(etype: str, group: str, index: int) -> str:
    return f"{etype}:{group}:{index}"


def choose(etype: str, wording_set: str, key: str) -> tuple[str, int, str]:
    """The frame of one episode, by a hash of `key` (pair seed and episode position, never
    the world, so both worlds of a pair get the same wording)."""
    options = frames(etype, wording_set)
    h = int(hashlib.sha256(f"{wording_set}:{key}".encode()).hexdigest(), 16)
    return options[h % len(options)]


def render(c: dict, template: str) -> str:
    v = c["action"] if c["action"] in VERBS else "put"
    text = template.format(x=c["actor"], o=c["object"], p=c["place"], d=c["event_day"], v=v,
                           vb=VERBS[v][0], vpp=VERBS[v][1])
    return text[0].upper() + text[1:]


def _regex(template: str) -> re.Pattern:
    parts, seen = [], set()
    for chunk in re.split(r"(\{[a-z]+\})", template):
        m = re.fullmatch(r"\{([a-z]+)\}", chunk)
        if m:
            name = m.group(1)
            parts.append(f"(?P={name})" if name in seen else _GROUPS[name])
            seen.add(name)
        else:
            parts.append(re.escape(chunk))
    return re.compile("".join(parts))


def parse(text: str, etype: str, template: str) -> dict | None:
    """Exact inverse of `render` for one template: the structured content, or None."""
    t = template[0].upper() + template[1:]
    m = _regex(t).fullmatch(text) or _regex(template).fullmatch(text)
    if not m:
        return None
    g = m.groupdict()
    verb = g.get("v") or next((p for p, (b, pp) in VERBS.items() if g.get("vb") == b or g.get("vpp") == pp), None)
    base = {"placing": {"actor": g.get("x"), "partner": None, "action": verb, "object": g.get("o")},
            "own_put": {"actor": SELF, "partner": None, "action": "put", "object": g.get("o")},
            "gave": {"actor": g.get("x"), "partner": SELF, "action": "gave", "object": g.get("o")},
            "seen": {"actor": g.get("x"), "partner": None, "action": "was", "object": None},
            "went": {"actor": SELF, "partner": None, "action": "went", "object": None}}[etype]
    return dict(base, place=g["p"], event_day=int(g["d"]))
