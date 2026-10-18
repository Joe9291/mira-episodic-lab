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


# p3 = p2 plus five worked examples per slot as earlier chat turns (development wordings
# only; names, places and objects outside the world vocabulary)
EXAMPLES = [
    ("On day 3, you saw Mara Lind hid the green box at Rook Tower.",
     {"actor": "Mara Lind", "partner": "none", "action": "hid", "object": "green box", "place": "Rook Tower", "event_day": "3"}),
    ("At Pine Lodge on day 8, you spotted Tom Reed.",
     {"actor": "Tom Reed", "partner": "none", "action": "was", "object": "none", "place": "Pine Lodge", "event_day": "8"}),
    ("You got the old key from Ida Voss at Fern Hall on day 5.",
     {"actor": "Ida Voss", "partner": "You", "action": "gave", "object": "old key", "place": "Fern Hall", "event_day": "5"}),
    ("You placed the small drum at Rook Tower on day 11.",
     {"actor": "You", "partner": "none", "action": "put", "object": "small drum", "place": "Rook Tower", "event_day": "11"}),
    ("Day 6: you walked to Pine Lodge.",
     {"actor": "You", "partner": "none", "action": "went", "object": "none", "place": "Pine Lodge", "event_day": "6"}),
]
PROMPTS = ("p2", "p3")


def messages(slot: str, text: str, prompt: str = "p2") -> list[dict]:
    if prompt not in PROMPTS:
        raise ValueError(prompt)
    turns = [{"role": "system", "content": SYSTEM}]
    if prompt == "p3":
        for note, answers in EXAMPLES:
            turns += [{"role": "user", "content": f"Note: {note}\n\nQuestion: {QUESTIONS[slot]}"},
                      {"role": "assistant", "content": answers[slot]}]
    return turns + [{"role": "user", "content": f"Note: {text}\n\nQuestion: {QUESTIONS[slot]}"}]


NULL_NOTE = "(no note)"
MODES = ("sum", "mean", "pmi")


def encode_text(scorer, text: str, null_scorer=None, ntokens=None, prompt: str = "p2") -> dict:
    """{slot: [[surface, canonical, score, null_score, tokens], ...]}: `score` is the total
    log-probability of the complete answer after the slot question about this note (the
    approved definition); `null_score` the same with the note replaced by "(no note)"
    (for a calibrated comparison, development measurement), `tokens` the answer's token
    count including the end-of-turn token. Without null_scorer/ntokens those are None."""
    out = {}
    for slot in SLOTS:
        cands = candidates(slot, text)
        surf = [s for s, _ in cands]
        scores = scorer(messages(slot, text, prompt), surf)
        nulls = null_scorer(slot, surf) if null_scorer else [None] * len(surf)
        toks = [ntokens(s) for s in surf] if ntokens else [None] * len(surf)
        out[slot] = [[s, c, float(x), None if n is None else float(n), t]
                     for (s, c), x, n, t in zip(cands, scores, nulls, toks)]
    return out


def view(entries: list, mode: str = "sum") -> list[tuple]:
    """(surface, canonical, score) under a scoring mode: "sum" = total log-probability (the
    approved definition), "mean" = per answer token, "pmi" = minus the score without the
    note (development comparisons)."""
    out = []
    for x in entries:
        if mode == "sum":
            out.append((x[0], x[1], x[2]))
        elif mode == "mean":
            out.append((x[0], x[1], x[2] / x[4]))
        elif mode == "pmi":
            out.append((x[0], x[1], x[2] - x[3]))
        else:
            raise ValueError(mode)
    return out


def decide_record(encoding: dict, taus: dict, mode: str = "sum") -> tuple[dict, list, dict]:
    """(record content, declared unknown slots, per-slot detail) from a recorded encoding.
    taus[slot] = threshold or None (no qualifying threshold: always unknown)."""
    content, unknown, detail = {}, [], {}
    for slot in SLOTS:
        value, margin, status = decide(view(encoding[slot], mode), taus.get(slot))
        detail[slot] = {"value": value, "margin": margin, "status": status}
        if status == "unknown":
            content[slot] = None
            unknown.append(slot)
        else:
            content[slot] = None if value == NONE else value
    return content, unknown, detail


def margins(encoding: dict, mode: str = "sum") -> dict:
    """{slot: (best canonical value, margin or None for a single value)} - for calibration."""
    return {slot: ranking(view(encoding[slot], mode))[:2] for slot in SLOTS}
