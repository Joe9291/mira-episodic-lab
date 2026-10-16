"""Arm S0: a rule-based event manager (protocol section 4).

It reads the same episode texts the models see, once each and in presentation order,
stores parsed events in a table and answers the same questions by rules. It shows how
far the benchmark is solved by plain data handling, without any language model.
"""
from __future__ import annotations

import re

from .questions import BASE, PARA

PAST = {base: past for past, base in BASE.items()}
_NAME = r"[A-Z][a-z]+ [A-Z][a-z]+"
_PLACE = r"[A-Z][a-z]+ [A-Z][a-z]+"
_OBJ = r"[a-z]+ [a-z]+"
_ACT = "|".join(BASE)
_PART = r"(?: together with (?P<partner>" + _NAME + r"))?"
EPISODE_PATTERNS = [
    rf"On day (?P<day>\d+), (?P<actor>{_NAME}) (?P<action>{_ACT}) the (?P<object>{_OBJ}) at (?P<place>{_PLACE}){_PART}\.",
    rf"Day (?P<day>\d+): at (?P<place>{_PLACE}), (?P<actor>{_NAME}){_PART} (?P<action>{_ACT}) the (?P<object>{_OBJ})\.",
    rf"(?P<actor>{_NAME}) was at (?P<place>{_PLACE}) on day (?P<day>\d+) and (?P<action>{_ACT}) the (?P<object>{_OBJ}){_PART}\.",
    rf"Looking back to day (?P<day>\d+): (?P<actor>{_NAME}) (?P<action>{_ACT}) the (?P<object>{_OBJ}) at (?P<place>{_PLACE}){_PART}\.",
    rf"Earlier, on day (?P<day>\d+), (?P<actor>{_NAME}){_PART} had (?P<action>{_ACT}|hidden) the (?P<object>{_OBJ}) at (?P<place>{_PLACE})\.",
]


class SymbolicMemory:
    def __init__(self):
        self.events: list[dict] = []

    def encode(self, text: str) -> None:
        for pattern in EPISODE_PATTERNS:
            m = re.fullmatch(pattern, text)
            if m:
                event = m.groupdict()
                event["day"] = int(event["day"])
                if event["action"] == "hidden":
                    event["action"] = "hid"
                self.events.append(event)
                return
        raise ValueError(f"unparsed episode: {text}")

    def _match(self, person=None, action=None, place=None, obj=None):
        return [e for e in self.events
                if (person is None or person in (e["actor"], e["partner"]))
                and (action is None or e["action"] == action)
                and (place is None or e["place"] == place)
                and (obj is None or e["object"] == obj)]

    def answer(self, text: str) -> str:
        for qtype, templates in PARA.items():
            for template in templates:
                m = re.fullmatch(_template_regex(template), text)
                if m:
                    return self._answer(qtype, m.groupdict())
        return "unparsed"

    def _answer(self, qtype: str, g: dict) -> str:
        action = PAST.get(g.get("action"), g.get("past"))
        if qtype in ("object", "place", "person", "day"):
            cue = {"person": g.get("person"), "action": action, "place": g.get("place"),
                   "obj": g.get("object")}
            hits = self._match(**{k: v for k, v in cue.items() if v is not None})
            if len(hits) != 1:
                return "none"
            e = hits[0]
            return {"object": e["object"], "place": e["place"], "person": e["actor"],
                    "day": str(e["day"])}[qtype]
        if qtype == "order":
            days = []
            for side in ("a", "b"):
                m = re.fullmatch(rf"({_NAME}) ({_ACT}) the ({_OBJ})\.", g[side])
                hits = self._match(person=m.group(1), action=m.group(2), obj=m.group(3)) if m else []
                days.append(hits[0]["day"] if len(hits) == 1 else None)
            if None in days:
                return "unknown"
            return "A" if days[0] < days[1] else "B"
        if qtype == "latest":
            hits = self._match(person=g["person"])
            return max(hits, key=lambda e: e["day"])["place"] if hits else "none"
        if qtype == "at_day":
            hits = [e for e in self._match(person=g["person"]) if e["day"] == int(g["day"])]
            return hits[0]["place"] if hits else "none"
        if qtype == "act":
            with_obj = self._match(obj=g["object"])
            if not with_obj:
                return "none"
            holder = max(with_obj, key=lambda e: e["day"])["actor"]
            return max(self._match(person=holder), key=lambda e: e["day"])["place"]
        return "unparsed"


def _template_regex(template: str) -> str:
    parts = re.split(r"(\{[a-z]+\})", template)
    groups = {"{person}": rf"(?P<person>{_NAME})", "{place}": rf"(?P<place>{_PLACE})",
              "{object}": rf"(?P<object>{_OBJ})", "{action}": rf"(?P<action>{'|'.join(PAST)})",
              "{past}": rf"(?P<past>{_ACT})", "{day}": r"(?P<day>\d+)",
              "{a}": r"(?P<a>.+?)", "{b}": r"(?P<b>.+?)"}
    return "".join(groups.get(p, re.escape(p)) for p in parts)
