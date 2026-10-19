"""Round 3.6 rule baseline (docs/ROUND_3_6.md, design v3, section 3): a small grammar with
precedence, built from the template and DEVELOPMENT wordings only. Lexical words are listed
in LEXICON; `provenance()` checks that each occurs in those wordings (a test enforces it).
General grammar parts (determiners, pronouns, the capitalisation of names) are listed
separately in FUNCTION_WORDS. The holdout shows what this baseline misses.
"""
from __future__ import annotations

import re

from .questions36 import OBJECT_TYPES, SETS, TYPES, UNSUPPORTED, UNSUPPORTED_FAMILIES, AMBIGUOUS

LEXICON = {
    "own_verbs": ("put", "placed", "moved", "saw", "seen"),          # the target's own records
    "recency": ("last", "latest", "now"),
    "giver": (r"\bgave you\b", r"\bgot the [a-z]+ [a-z]+ from\b", r"\bhanded you\b"),
    "unsupported": (r"\bwhy\b", r"\bhow many\b", r"\bwill\b", r"\btomorrow\b", r"\bbelong\b"),
    "who_action": ("put", "placed", "moved"),
    "first": (r"\bfirst\b", r"\bstart out\b"),
    "previous": (r"\bbefore\b.*\b(last|latest)\b",),
}
FUNCTION_WORDS = ("the", "a", "an", "it", "they", "you", "he", "she", "them", "who", "before", "after", "was",
                  "were", "had", "just", "right")
_PRONOUN_SUBJ = r"(?:it|they|you|he|she|[A-Z][a-z]+ [A-Z][a-z]+|the [a-z]+ [a-z]+)"


def _dev_text() -> str:
    parts = []
    for fam in TYPES:
        for g in SETS["dev"]:
            parts += TYPES[fam].get(g, [])
    for fam in AMBIGUOUS:
        parts += [w for w, _ in AMBIGUOUS[fam].get("dev", [])]
    for fam in UNSUPPORTED_FAMILIES:
        parts += UNSUPPORTED_FAMILIES[fam].get("dev", [])
    return " ".join(parts).lower()


_STOP = set(re.findall(r"[a-z]+", re.sub(r"\{\w+\}", " ", _dev_text())))
_STOP_CAP = {w.capitalize() for w in _STOP} | {"I"}


def provenance() -> list[str]:
    """Lexical items of the baseline that do NOT occur in the template and development wordings."""
    text = _dev_text()
    missing = []
    for key, items in LEXICON.items():
        for it in items:
            if it.startswith(r"\b") or "\\" in it:
                words = re.findall(r"[a-z]+", re.sub(r"\\b|\[a-z\]\+", " ", it))
                if not all(re.search(rf"\b{w}\b", text) for w in words):
                    missing.append(f"{key}:{it}")
            elif not re.search(rf"\b{it}\b", text):
                missing.append(f"{key}:{it}")
    return missing


def _clause_kind(text: str) -> str | None:
    """'previous' for a before-clause about the target's own latest record, 'event' for any
    other before/after clause with a verb, None without such a clause."""
    m = re.search(rf"\b(before|after)\s+{_PRONOUN_SUBJ}\s+((?:\w+\s+){{0,3}}?)(\w+)\b([^,.?!]*)", text)
    if not m:
        return None
    clause = (m.group(2) + " " + m.group(3) + m.group(4)).lower()
    words = set(re.findall(r"[a-z]+", clause))
    if m.group(1) == "before" and words & set(LEXICON["own_verbs"]) and words & set(LEXICON["recency"]):
        return "previous"
    return "event"


def _referents(text: str) -> tuple[list[str], list[str]]:
    # overlapping matches (lookahead): "the place the cracked violin", "Find Sabeth Ostrin"
    objs = [f"{a} {b}" for a, b in re.findall(r"\b(?:the|a|an) (?=([a-z]+)\s+([a-z]+)(?:'s)?\b)", text)
            if a not in _STOP and b not in _STOP]
    people = [f"{a} {b}" for a, b in re.findall(r"(?<![A-Za-z])(?=([A-Z][a-z]+)\s+([A-Z][a-z]+)\b)", text)
              if a not in _STOP_CAP and b not in _STOP_CAP]
    return objs, people


def parse_baseline(text: str) -> dict:
    """{outcome, reason, intent, target} like parser36.decide_question."""
    low = text.lower()
    clause = _clause_kind(text)
    if clause == "event":
        return {"outcome": "REFUSE", "reason": None, "intent": UNSUPPORTED, "target": None}
    objs, people = _referents(text)
    if any(re.search(p, low) for p in LEXICON["giver"]):
        intent = "giver"
    elif any(re.search(p, low) for p in LEXICON["unsupported"]) or \
            re.match(rf"^who ({'|'.join(LEXICON['who_action'])})\b", low):
        return {"outcome": "REFUSE", "reason": None, "intent": UNSUPPORTED, "target": None}
    else:
        if clause == "previous" or any(re.search(p, low) for p in LEXICON["previous"]):
            when = "previous"
        elif any(re.search(p, low) for p in LEXICON["first"]):
            when = "first"
        else:
            when = "current"
        intent = f"person_{when}" if people and not objs else f"object_{when}"
    refs = objs if intent in OBJECT_TYPES else people
    if len(refs) != 1:
        return {"outcome": "CLARIFY", "reason": "no_referent", "intent": intent, "target": None}
    return {"outcome": "OK", "reason": None, "intent": intent, "target": refs[0]}
