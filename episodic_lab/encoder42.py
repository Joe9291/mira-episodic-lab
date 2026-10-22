"""Round 4.2 LM-assisted extraction of report notes (docs/ROUND_4_2.md section 3).

For every slot of cands42.SLOTS the model scores every candidate surface as the complete
answer to a fixed slot question about the note; the recorded encoding keeps every
surface, its canonical value and its score. The type decision, the slots a note uses,
their allowed candidates, margins and thresholds are applied later and model-free.

Prompts are development choices (changed only on development data; every change logged
in docs/ROUND_4_2.md). Worked examples use names, places and things OUTSIDE the world
vocabulary.
"""
from __future__ import annotations

from .cands42 import ATTRIBUTES, SLOTS, TYPES, candidates

PROMPTS = ("p1",)
SYSTEM = ("You read one short note and fill in one field of a record about it. In a note written by "
          "someone else, 'you' means the reader. Answer with only the value, nothing else.")
QUESTIONS = {
    "type": ("Field 'type': what kind of note is this? " + "; ".join(f"{k} = {v}" for k, v in TYPES.items())
             + ". Answer with one of these words."),
    "subject": "Field 'thing': the thing (not a person, not a place) that the note is about, as written in the note.",
    "attribute": ("Field 'aspect': " + "; ".join(f"{k} = {v}" for k, v in ATTRIBUTES.items())
                  + ". Answer with one of these words."),
    "value": ("Field 'value': the place where the thing is, or the person who has it, as written in the note; for a "
              "correction, the corrected place or person. If a correction only changes the date and keeps the place "
              "or person, answer: keep."),
    "valid_from": ("Field 'since': the day from which the stated place or holder is true, as a number (today and "
                   "yesterday count from the day the note was written). If the note names no such day, answer: not "
                   "stated. If a correction only changes the place or person and keeps the date, answer: keep."),
    "ref_source": ("Field 'source': whose earlier report does this note repeat, correct or withdraw? Answer with that "
                   "person's first name; if it is the reader's report, answer: you; if it is the author's own "
                   "report, answer: me."),
    "ref_day": "Field 'report day': the day on which that earlier report was made, as a number.",
    "person": "Field 'person': the person the reader met, as written in the note.",
    "place": "Field 'place': the place where the reader met that person, as written in the note.",
    "day": ("Field 'day': the day of the meeting, as a number (today and yesterday count from the day the note was "
            "written)."),
}
# worked examples (outside the world vocabulary): (header, text, answers of the slots the
# example's type uses)
EXAMPLES = [
    ("Day 9, note from Ola.", "The green box has been at Rook Tower since day 6.",
     {"type": "statement", "subject": "green box", "attribute": "location", "value": "Rook Tower", "valid_from": "6"}),
    ("Day 5, your own note.", "Mara Lind has had the old key.",
     {"type": "statement", "subject": "old key", "attribute": "holder", "value": "Mara Lind", "valid_from": "not stated"}),
    ("Day 12, note from Pim.", "Ola said on day 10 that Tom Reed has had the red bell since day 8.",
     {"type": "repeated statement", "subject": "red bell", "attribute": "holder", "value": "Tom Reed",
      "valid_from": "8", "ref_source": "Ola", "ref_day": "10"}),
    ("Day 7, note from Ola.", "Correction to Pim's report of day 4: the green box was actually at Fern Hall.",
     {"type": "correction", "subject": "green box", "attribute": "location", "value": "Fern Hall",
      "valid_from": "keep", "ref_source": "Pim", "ref_day": "4"}),
    ("Day 11, note from Pim.", "My report of day 9 was wrong: the handover of the old key actually happened on day 8.",
     {"type": "correction", "subject": "old key", "attribute": "holder", "value": "keep", "valid_from": "8",
      "ref_source": "me", "ref_day": "9"}),
    ("Day 6, note from Pim.", "Please disregard your report of day 3 about where the red bell is.",
     {"type": "retraction", "subject": "red bell", "attribute": "location", "ref_source": "you", "ref_day": "3"}),
    ("Day 8, note from Ola.", "You met Ida Voss at Pine Lodge yesterday.",
     {"type": "meeting", "person": "Ida Voss", "place": "Pine Lodge", "day": "yesterday"}),
]


def note_block(header: str, text: str) -> str:
    return f"{header}\nNote: {text}"


def messages(slot: str, header: str, text: str, prompt: str = "p1") -> list[dict]:
    if prompt not in PROMPTS:
        raise ValueError(prompt)
    q = QUESTIONS[slot]
    turns = [{"role": "system", "content": SYSTEM}]
    for h, t, answers in EXAMPLES:
        if slot in answers:
            turns += [{"role": "user", "content": f"{note_block(h, t)}\n\nQuestion: {q}"},
                      {"role": "assistant", "content": answers[slot]}]
    return turns + [{"role": "user", "content": f"{note_block(header, text)}\n\nQuestion: {q}"}]


def encode_note(scorer, header: str, text: str, ctx: dict, prompt: str = "p1") -> dict:
    """{slot: [[surface, canonical, score], ...]} for every slot (the superset)."""
    out = {}
    full = header + " " + text
    for slot in SLOTS:
        cands = candidates(slot, full, ctx)
        scores = scorer(messages(slot, header, text, prompt), [s for s, _ in cands]) if cands else []
        out[slot] = [[s, c, float(x)] for (s, c), x in zip(cands, scores)]
    return out
