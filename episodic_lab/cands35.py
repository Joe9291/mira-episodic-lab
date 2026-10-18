"""Round 3.5 candidates and canonical values (docs/ROUND_3_5.md section 2), fixed before
any model run.

Contract:
- tokens: maximal runs of letters, digits and apostrophes; punctuation is not a token and
  a span never crosses punctuation; candidate spans are 1-3 consecutive tokens;
- canonical values: names (person, place) keep the text's spelling; objects are
  lower-cased with a leading article (the, a, an) removed; numbers become integers;
  "I", "me", "you" (any case) become "You"; "none" = the optional field is absent;
- action: a fixed label set with one short description each;
- surface variants of one canonical value are merged; the value's score is the MAXIMUM of
  its variants' scores; the margin is taken between DIFFERENT canonical values.

Slots and their candidate kinds:
  actor    person spans + "You"
  partner  person spans + "You" + "none"
  object   object spans + "none"
  place    name spans
  event_day numbers in the text
  action   the label set
"""
from __future__ import annotations

import re

SELF = "You"
NONE = "none"
SLOTS = ("actor", "partner", "action", "object", "place", "event_day")
ACTIONS = {"hid": "hid an object somewhere", "left": "left an object somewhere",
           "put": "put or placed an object somewhere", "gave": "gave an object to someone",
           "was": "was seen somewhere, without an object", "went": "went somewhere"}
_SEGMENT = re.compile(r"[^,.;:!?()\-]+")
_TOKEN = re.compile(r"[A-Za-z0-9']+")
_SELF_WORDS = {"i", "me", "you"}
_ARTICLES = ("the ", "a ", "an ")


def spans(text: str, max_len: int = 3) -> list[str]:
    """All contiguous 1-3-token spans that do not cross punctuation, in text order."""
    out = []
    for seg in _SEGMENT.findall(text):
        toks = _TOKEN.findall(seg)
        for i in range(len(toks)):
            for n in range(1, max_len + 1):
                if i + n <= len(toks):
                    out.append(" ".join(toks[i:i + n]))
    return out


def canonical(slot: str, surface: str):
    """Canonical value of a surface candidate for a slot (None = the candidate is not a
    possible value of that slot, e.g. a non-number for the day)."""
    s = surface.strip()
    if slot == "action":
        return s if s in ACTIONS else None
    if s.lower() == NONE:
        return NONE if slot in ("partner", "object") else None
    if slot == "event_day":
        return int(s) if s.isdigit() else None
    if slot in ("actor", "partner"):
        return SELF if s.lower() in _SELF_WORDS else s
    if slot == "object":
        low = s.lower()
        for art in _ARTICLES:
            if low.startswith(art):
                low = low[len(art):]
        return low or None
    return s  # place


def candidates(slot: str, text: str) -> list[tuple[str, object]]:
    """[(surface, canonical value)] for one slot, deduplicated by surface, in a fixed order."""
    if slot == "action":
        surf = list(ACTIONS)
    else:
        surf = spans(text)
        if slot in ("actor", "partner"):
            surf.append(SELF)
        if slot in ("partner", "object"):
            surf.append(NONE)
    out, seen = [], set()
    for s in surf:
        if s in seen:
            continue
        seen.add(s)
        c = canonical(slot, s)
        if c is not None:
            out.append((s, c))
    return out


def truth_value(slot: str, content: dict):
    """The canonical form of the true value of a slot (None in the content -> "none")."""
    v = content[slot]
    if v is None:
        return NONE
    return v


def merge(scored: list[tuple[str, object, float]]) -> dict:
    """{canonical value: max score over its surface variants}."""
    best = {}
    for _, value, score in scored:
        key = value
        if key not in best or score > best[key]:
            best[key] = score
    return best


def decide(scored: list[tuple[str, object, float]], tau: float | None):
    """(value, margin, status) from scored candidates. status: "ok", "unknown" (margin below
    tau, margin 0, or no qualifying tau = None), "single" (only one canonical value: accepted
    unless the slot has no qualifying tau)."""
    best = merge(scored)
    if not best:
        return None, None, "unknown"
    ranked = sorted(best.items(), key=lambda kv: (-kv[1], str(kv[0])))
    value, top = ranked[0]
    if len(ranked) == 1:
        return (value, None, "single") if tau is not None else (None, None, "unknown")
    margin = top - ranked[1][1]
    if tau is None or margin <= 0 or margin < tau:
        return None, margin, "unknown"
    return value, margin, "ok"


def coverage(slot: str, text: str, content: dict) -> bool:
    return truth_value(slot, content) in {c for _, c in candidates(slot, text)}
