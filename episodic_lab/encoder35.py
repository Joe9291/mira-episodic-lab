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

PROMPT_VERSION = "p1"
SYSTEM = "You read one note about an event and answer one question about it. Answer with only the answer, nothing else."
QUESTIONS = {
    "actor": "Who did what the note describes? If it was the narrator (you or I), answer: You.",
    "partner": ("Apart from the one who did it, which other person took part in the event, for example by "
                "receiving something? If it was the narrator, answer: You. If nobody else took part, answer: none."),
    "action": ("Which word describes the event best? " + "; ".join(f"{k} ({v})" for k, v in ACTIONS.items())
               + ". Answer with one of these words."),
    "object": "Which object is the note about? Answer with its name as written in the note, or none if there is no object.",
    "place": "At which place did the event happen? Answer with the place's name as written in the note.",
    "event_day": "On which day number did the event happen? Answer with the number.",
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
