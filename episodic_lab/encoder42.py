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

PROMPTS = ("p1", "p2", "p3")
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


# p2 (development change after the timing slice, logged in docs/ROUND_4_2.md): sharper
# questions for type, aspect, since and source, and fourteen worked examples - every
# development frame family, value-only and date-only corrections ("keep"), a repeat inside
# the reader's own note (its source is the quoted person, not "me"), retractions "about who
# has" (aspect holder); only template / development frames, names outside the vocabulary
QUESTIONS_P2 = dict(QUESTIONS)
QUESTIONS_P2.update({
    "type": ("Field 'type': what kind of note is this? statement = the author says where a thing is or who has it, "
             "without mentioning any earlier report; repeated statement = the author passes on what another person "
             "said or reported on an earlier day; correction = the author says that an earlier report was wrong and "
             "gives the right place, person or day; retraction = the author withdraws or cancels an earlier report; "
             "meeting = the note says that the reader met a person somewhere. Answer with one of: statement, repeated "
             "statement, correction, retraction, meeting."),
    "attribute": ("Field 'aspect': is the note about WHERE the thing is (answer: location) or about WHO has the "
                  "thing (answer: holder)? 'with a person', 'in the hands of', 'who has', 'the handover' mean holder; "
                  "'at a place', 'where', 'the move' mean location."),
    "valid_from": ("Field 'since': the day from which the stated place or holder is true, as a number (today and "
                   "yesterday count from the day the note was written). A statement that names no such day: answer "
                   "not stated. A correction that does not name a new day for the place or person: answer keep."),
    "ref_source": ("Field 'source': whose earlier report is repeated, corrected or withdrawn? Answer with that "
                   "person's first name as written; answer you if it is the reader's report ('your report'); answer "
                   "me only if it is the author's own report ('my report')."),
})
EXAMPLES_P2 = [
    ("Day 9, note from Ola.", "The green box has been at Rook Tower since day 6.",
     {"type": "statement", "subject": "green box", "attribute": "location", "value": "Rook Tower", "valid_from": "6"}),
    ("Day 5, your own note.", "Mara Lind has had the old key.",
     {"type": "statement", "subject": "old key", "attribute": "holder", "value": "Mara Lind", "valid_from": "not stated"}),
    ("Day 8, note from Kai.", "Tom Reed is the one who has had the red bell since yesterday.",
     {"type": "statement", "subject": "red bell", "attribute": "holder", "value": "Tom Reed", "valid_from": "yesterday"}),
    ("Day 6, note from Pim.", "Update: the small drum has been with Ida Voss since day 4.",
     {"type": "statement", "subject": "small drum", "attribute": "holder", "value": "Ida Voss", "valid_from": "4"}),
    ("Day 12, note from Pim.", "Ola reported on day 10 that Tom Reed has had the red bell since day 8.",
     {"type": "repeated statement", "subject": "red bell", "attribute": "holder", "value": "Tom Reed",
      "valid_from": "8", "ref_source": "Ola", "ref_day": "10"}),
    ("Day 7, your own note.", "According to Kai on day 6, the green box has been at Pine Lodge since day 3.",
     {"type": "repeated statement", "subject": "green box", "attribute": "location", "value": "Pine Lodge",
      "valid_from": "3", "ref_source": "Kai", "ref_day": "6"}),
    ("Day 7, note from Ola.", "Correction to Pim's report of day 4: the green box was actually at Fern Hall.",
     {"type": "correction", "subject": "green box", "attribute": "location", "value": "Fern Hall",
      "valid_from": "keep", "ref_source": "Pim", "ref_day": "4"}),
    ("Day 11, note from Pim.", "My report of day 9 was wrong: the handover of the old key actually happened on day 8.",
     {"type": "correction", "subject": "old key", "attribute": "holder", "value": "keep", "valid_from": "8",
      "ref_source": "me", "ref_day": "9"}),
    ("Day 9, note from Kai.", "Please fix your report of day 5 - the small drum was actually with Mara Lind from day 4.",
     {"type": "correction", "subject": "small drum", "attribute": "holder", "value": "Mara Lind",
      "valid_from": "4", "ref_source": "you", "ref_day": "5"}),
    ("Day 6, note from Pim.", "Please disregard your report of day 3 about who has the red bell.",
     {"type": "retraction", "subject": "red bell", "attribute": "holder", "ref_source": "you", "ref_day": "3"}),
    ("Day 10, your own note.", "Withdraw my report of day 8 about where the old key is.",
     {"type": "retraction", "subject": "old key", "attribute": "location", "ref_source": "me", "ref_day": "8"}),
    ("Day 8, note from Ola.", "You met Ida Voss at Pine Lodge yesterday.",
     {"type": "meeting", "person": "Ida Voss", "place": "Pine Lodge", "day": "yesterday"}),
    ("Day 11, your own note.", "On day 9, I met Tom Reed at Rook Tower.",
     {"type": "meeting", "person": "Tom Reed", "place": "Rook Tower", "day": "9"}),
    ("Day 4, note from Kai.", "Your meeting today with Mara Lind at Fern Hall.",
     {"type": "meeting", "person": "Mara Lind", "place": "Fern Hall", "day": "today"}),
]


# p3 (development change after probe 1, logged in docs/ROUND_4_2.md; needs candidates
# c42.3): the source is COPIED from the note (a name, my, your / you); the aspect is asked
# as place / person with cue words; the type question names the cue phrases of repeated
# statements and says that "Update:" only introduces a statement
QUESTIONS_P3 = dict(QUESTIONS_P2)
QUESTIONS_P3.update({
    "type": ("Field 'type': what kind of note is this? statement = the author says where a thing is or who has it "
             "(a leading 'Update:' or 'I can tell you that' still makes it a statement); repeated statement = the "
             "author passes on what ANOTHER person said or reported on an earlier day ('X reported on day N that', "
             "'according to X on day N', 'as X told me on day N', 'passing on what X said'); correction = the author "
             "says that an earlier report was wrong and gives the right place, person or day; retraction = the author "
             "withdraws or cancels an earlier report; meeting = the note says that the reader met a person somewhere. "
             "Answer with one of: statement, repeated statement, correction, retraction, meeting."),
    "attribute": ("Field 'aspect': does the note say at which PLACE the thing is (answer: place) or which PERSON has "
                  "the thing (answer: person)? 'with', 'in the hands of', 'kept by', 'who has', 'had', 'the handover' "
                  "point to a person; 'at', 'where', 'the move' point to a place. Answer: place or person."),
    "ref_source": ("Field 'source': whose earlier report or statement does the note repeat, correct or withdraw? Copy "
                   "the word from the note: that person's first name, or my (the author's own report), or your / you "
                   "(the reader's report)."),
})
_P3_FIX = {"location": "place", "holder": "person", "me": "my"}


def _p3(answers: dict, text: str) -> dict:
    out = dict(answers)
    if "attribute" in out:
        out["attribute"] = _P3_FIX[out["attribute"]]
    if out.get("ref_source") == "me":
        out["ref_source"] = "my"
    if out.get("ref_source") == "you":
        out["ref_source"] = "your" if "your" in text else "you"
    return out


EXAMPLES_P3 = [(h, t, _p3(a, t)) for h, t, a in EXAMPLES_P2]


def note_block(header: str, text: str) -> str:
    return f"{header}\nNote: {text}"


def messages(slot: str, header: str, text: str, prompt: str = "p1") -> list[dict]:
    if prompt not in PROMPTS:
        raise ValueError(prompt)
    q = {"p1": QUESTIONS, "p2": QUESTIONS_P2, "p3": QUESTIONS_P3}[prompt][slot]
    turns = [{"role": "system", "content": SYSTEM}]
    for h, t, answers in {"p1": EXAMPLES, "p2": EXAMPLES_P2, "p3": EXAMPLES_P3}[prompt]:
        if slot in answers:
            turns += [{"role": "user", "content": f"{note_block(h, t)}\n\nQuestion: {q}"},
                      {"role": "assistant", "content": answers[slot]}]
    return turns + [{"role": "user", "content": f"{note_block(header, text)}\n\nQuestion: {q}"}]


def encode_note(scorer, header: str, text: str, ctx: dict, prompt: str = "p1", slots=None) -> dict:
    """{slot: [[surface, canonical, score], ...]} for every slot (the superset); `slots`
    restricts the slots for development probes only."""
    out = {}
    full = header + " " + text
    for slot in (slots or SLOTS):
        cands = candidates(slot, full, ctx)
        scores = scorer(messages(slot, header, text, prompt), [s for s, _ in cands]) if cands else []
        out[slot] = [[s, c, float(x)] for (s, c), x in zip(cands, scores)]
    return out
