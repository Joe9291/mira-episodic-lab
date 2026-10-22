"""Round 4.2 candidates and canonical values (docs/ROUND_4_2.md sections 3 and 8), fixed
before any model run. Inputs: only the note (header + text), its author and report day,
and the world's source names - never the generator's note type or the gold report.

Contract (the round 3.5 token rules):
- tokens: maximal runs of letters, digits and apostrophes; a span never crosses
  punctuation; candidate spans are 1-3 consecutive tokens;
- name candidates (value, person, place): spans whose tokens all begin with a capital
  letter; object candidates (subject; version c42.2, a development change after the
  timing slice, which showed 23 subject candidates per note dominating the run time): the
  one or two lower-case words directly after an article ("the", "a", "an"), never
  crossing punctuation (canonical value = those words);
- day candidates: the numbers of the note and the words "today" / "yesterday" (canonical:
  the report day / the day before); "not stated" (statement) has the canonical value of
  the report day (a statement without a day speaks about the day it is written);
- "keep" (corrections: value or day unchanged) is its own canonical value;
- source candidates: the world's source names, "you" (= the reader, canonical "self") and
  "me" (= the author);
- label slots (type, attribute) score a fixed label set;
- surface variants of one canonical value are merged (maximum score); margins are taken
  between DIFFERENT canonical values (cands35.ranking / decide).

Every slot is scored for every note (a superset); which slots a note USES, and which of
their candidates are allowed, follows only from the PREDICTED type (USES / ALLOWED below).
"""
from __future__ import annotations

import re

from .cands35 import decide, merge, ranking, spans  # noqa: F401 (re-exported, unchanged rules)

CANDIDATE_VERSION = "c42.2"
TYPES = {"statement": "it says where a thing is or who has it",
         "repeated statement": "the author passes on what another person reported",
         "correction": "the author corrects an earlier report",
         "retraction": "the author withdraws an earlier report",
         "meeting": "it says that the reader met a person somewhere"}
ATTRIBUTES = {"location": "the note says WHERE the thing is", "holder": "the note says WHO has the thing"}
NOT_STATED, KEEP = "not stated", "keep"
SLOTS = ("type", "subject", "attribute", "value", "valid_from", "ref_source", "ref_day", "person", "place", "day")
USES = {
    "statement": ("subject", "attribute", "value", "valid_from"),
    "repeated statement": ("subject", "attribute", "value", "valid_from", "ref_source", "ref_day"),
    "correction": ("subject", "attribute", "value", "valid_from", "ref_source", "ref_day"),
    "retraction": ("subject", "attribute", "ref_source", "ref_day"),
    "meeting": ("person", "place", "day"),
}
_ARTICLES = ("the ", "a ", "an ")


def _is_name(s: str) -> bool:
    return all(t[:1].isupper() for t in s.split())


def canonical(slot: str, surface: str, ctx: dict):
    """Canonical value of a surface for a slot; None = not a possible value. ctx: author,
    report_day, sources."""
    s = surface.strip()
    rd = ctx["report_day"]
    if slot == "type":
        return s if s in TYPES else None
    if slot == "attribute":
        return s if s in ATTRIBUTES else None
    if slot in ("valid_from", "day", "ref_day"):
        if s.isdigit():
            return int(s)
        if slot != "ref_day" and s == "today":
            return rd
        if slot != "ref_day" and s == "yesterday":
            return rd - 1
        if slot == "valid_from" and s == NOT_STATED:
            return rd
        if slot == "valid_from" and s == KEEP:
            return KEEP
        return None
    if slot == "ref_source":
        if s == "you":
            return "self"
        if s == "me":
            return ctx["author"]
        return s if s in ctx["sources"] else None
    if slot == "subject":
        if not all(t.isalpha() and t.islower() for t in s.split()):
            return None
        low = s
        for art in _ARTICLES:
            if low.startswith(art):
                low = low[len(art):]
        return low or None
    if slot == "value" and s == KEEP:
        return KEEP
    if slot in ("value", "person", "place"):
        return s if _is_name(s) and s not in ("I",) else None
    raise ValueError(slot)


def candidates(slot: str, note: str, ctx: dict) -> list[tuple[str, object]]:
    """[(surface, canonical)] for one slot, deduplicated by surface, in a fixed order."""
    if slot == "type":
        surf = list(TYPES)
    elif slot == "attribute":
        surf = list(ATTRIBUTES)
    elif slot == "ref_source":
        surf = sorted(n for n in ctx["sources"] if n != "self") + ["you", "me"]
    elif slot in ("valid_from", "day", "ref_day"):
        low = note.lower()
        surf = re.findall(r"\d+", note)
        if slot != "ref_day":
            surf += [w for w in ("today", "yesterday") if re.search(r"\b" + w + r"\b", low)]
        if slot == "valid_from":
            surf += [NOT_STATED, KEEP]
    elif slot == "subject":
        surf = []
        for seg in re.findall(r"[^,.;:!?()\-]+", note):
            toks = re.findall(r"[A-Za-z0-9']+", seg)
            for i, tok in enumerate(toks[:-1]):
                if tok.lower() in ("the", "a", "an"):
                    nxt = toks[i + 1:i + 3]
                    for n in range(1, len(nxt) + 1):
                        if all(t.isalpha() and t.islower() for t in nxt[:n]):
                            surf.append(" ".join(nxt[:n]))
    else:
        surf = spans(note)
        if slot == "value":
            surf.append(KEEP)
    out, seen = [], set()
    for s in surf:
        if s in seen:
            continue
        seen.add(s)
        c = canonical(slot, s, ctx)
        if c is not None:
            out.append((s, c))
    return out


def allowed_surface(slot: str, surface: str, predicted_type: str) -> bool:
    """Candidates a note may use, given its PREDICTED type: "not stated" (= the report day)
    only for statements, "keep" only for corrections; everything else as scored."""
    if surface == NOT_STATED:
        return predicted_type == "statement" and slot == "valid_from"
    if surface == KEEP:
        return predicted_type == "correction" and slot in ("value", "valid_from")
    return True


def truth(note: dict, report: dict, by_id: dict) -> dict:
    """The canonical true value of every slot a note of its TRUE type uses (generator side,
    used only for scoring and audits)."""
    t = {"statement": "statement", "repeat": "repeated statement", "correction": "correction",
         "retraction": "retraction", "meeting": "meeting"}[note["gold_type"]]
    out = {"type": t}
    if t == "meeting":
        m = re.fullmatch(r"event:met (.+) at (.+)", report["subject"])
        out.update(person=m[1], place=m[2], day=report["value"])
        return out
    out["subject"] = report["subject"][4:] if report["subject"].startswith("the ") else report["subject"]
    out["attribute"] = report["attribute"]
    if t in ("statement", "repeated statement"):
        out.update(value=report["value"], valid_from=report["valid_from"])
    if t == "correction":
        out.update(value=report["value"] if report["value"] is not None else KEEP,
                   valid_from=report["valid_from"] if report["valid_from"] is not None else KEEP)
    if t != "statement":
        ref = by_id[report["origin"][2:]] if t == "repeated statement" else by_id[report["target_report_id"]]
        out.update(ref_source=ref["source"], ref_day=ref["report_day"])
    return out

