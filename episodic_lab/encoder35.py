"""Round 3.5 LM-assisted structured extraction (docs/ROUND_3_5.md section 2).

For every slot of a note the model scores every candidate surface (cands35) as the
complete answer to a fixed slot question; the recorded encoding keeps every surface,
its canonical value and its score. Choice, margin and the unknown flag are derived
later, model-free (`decide_record`), from the recorded scores and the frozen thresholds.

Prompts are development choices (they may change only on development data; every change
is logged in docs/ROUND_3_5.md).
"""
from __future__ import annotations

from .cands35 import ACTIONS, NONE, SLOTS, candidates, decide, ranking

PROMPT_VERSION = "p2"
# p2 (development change after the timing slice, logged in docs/ROUND_3_5.md): questions
# state the schema's roles explicitly (who is reported, who received something, objects
# are things, "was" = a person seen somewhere)
SYSTEM = ("You read one note about an event and fill in one field of a record about it. "
          "Answer with only the value, nothing else.")
QUESTIONS = {
    "actor": ("Field 'actor': the person whose action or presence the note reports - the one who hid, left, put "
              "or gave something, or the one who was seen or met. If the narrator (you / I) did it, answer: You."),
    "partner": ("Field 'receiver': the person who received something from the actor in this event. If the narrator "
                "(you / me) received it, answer: You. If nothing was given to anyone, answer: none."),
    "action": ("Field 'action': one of these words: " + "; ".join(f"{k} = {v}" for k, v in ACTIONS.items())
               + ". Answer with one of these words."),
    "object": ("Field 'object': the thing (not a person, not a place) that the event is about, as written in the "
               "note. If the note mentions no thing, answer: none."),
    "place": "Field 'place': the place where the event happened, as written in the note.",
    "event_day": "Field 'day': the day number of the event.",
}


def messages(slot: str, text: str) -> list[dict]:
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Note: {text}\n\nQuestion: {QUESTIONS[slot]}"}]


def encode_text(scorer, text: str) -> dict:
    """{slot: [[surface, canonical, score], ...]} with `scorer(messages, surfaces) -> scores`."""
    out = {}
    for slot in SLOTS:
        cands = candidates(slot, text)
        scores = scorer(messages(slot, text), [s for s, _ in cands])
        out[slot] = [[s, c, float(x)] for (s, c), x in zip(cands, scores)]
    return out


def decide_record(encoding: dict, taus: dict) -> tuple[dict, list, dict]:
    """(record content, declared unknown slots, per-slot detail) from a recorded encoding.
    taus[slot] = threshold or None (no qualifying threshold: always unknown)."""
    content, unknown, detail = {}, [], {}
    for slot in SLOTS:
        value, margin, status = decide([tuple(x) for x in encoding[slot]], taus.get(slot))
        detail[slot] = {"value": value, "margin": margin, "status": status}
        if status == "unknown":
            content[slot] = None
            unknown.append(slot)
        else:
            content[slot] = None if value == NONE else value
    return content, unknown, detail


def margins(encoding: dict) -> dict:
    """{slot: (best canonical value, margin or None for a single value)} - for calibration."""
    return {slot: ranking([tuple(x) for x in encoding[slot]])[:2] for slot in SLOTS}
