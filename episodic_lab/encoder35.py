"""Round 3.5 LM-assisted structured extraction (docs/ROUND_3_5.md section 2).

For every slot of a note the model scores every candidate surface (cands35) as the
complete answer to a fixed slot question; the recorded encoding keeps every surface,
its canonical value and its score. Choice, margin and the unknown flag are derived
later, model-free (`decide_record`), from the recorded scores and the frozen thresholds.

Prompts are development choices (they may change only on development data; every change
is logged in docs/ROUND_3_5.md).
"""
from __future__ import annotations

from .cands35 import ACTIONS, NONE, SELF as SELF_VALUE, SLOTS, candidates, decide, ranking

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
PROMPTS = ("p2", "p3", "p4", "p5", "p6", "p7", "p8")
# p4 = p3 with the receiver question made explicit about which events have a receiver
# (development change after probe 3: the receiver was the only weak slot of qwen2.5-1.5b)
Q_RECEIVER_P4 = ("Field 'receiver': only when the note says that something was GIVEN, handed or passed to "
                 "someone - the person who got it; if the narrator (you / me) got it, answer: You. For every "
                 "other event (hiding, leaving, putting, placing, seeing, meeting, going) answer: none.")


# p5 = p3 with the receiver asked as a yes/no-type question about the narrator, and two
# more worked examples (a second "gave", a placing by another person) - development change
# after probe 4 (p4's receiver question was worse than p3's)
Q_RECEIVER_P5 = ("Field 'receiver': did the narrator (you / me) receive something from someone in this note? "
                 "If yes, answer: You. If not, answer: none.")
EXAMPLES_P5 = EXAMPLES + [
    ("Day 9: at Fern Hall, Tom Reed handed you the green box.",
     {"actor": "Tom Reed", "partner": "You", "action": "gave", "object": "green box", "place": "Fern Hall", "event_day": "9"}),
    ("You saw that Ida Voss left the old key at Rook Tower on day 2.",
     {"actor": "Ida Voss", "partner": "none", "action": "left", "object": "old key", "place": "Rook Tower", "event_day": "2"}),
]


# p6 / p7 (development change after probe 5, where the only errors were "You" for absent
# receivers in own placings, "went" and placings by others): three more worked examples of
# exactly those kinds with receiver "none"; p6 also rewords the receiver question
# ("only if another person gave ... to the narrator"), p7 keeps the p5 question
Q_RECEIVER_P6 = ("Field 'receiver': answer You only if another person gave, handed or passed something to the "
                 "narrator (you / me) in this note. In every other case answer: none.")
EXAMPLES_P6 = EXAMPLES_P5 + [
    ("On day 4, you put the red bell at Fern Hall.",
     {"actor": "You", "partner": "none", "action": "put", "object": "red bell", "place": "Fern Hall", "event_day": "4"}),
    ("You visited Rook Tower on day 3.",
     {"actor": "You", "partner": "none", "action": "went", "object": "none", "place": "Rook Tower", "event_day": "3"}),
    ("You saw that Tom Reed put the red bell at Fern Hall on day 7.",
     {"actor": "Tom Reed", "partner": "none", "action": "put", "object": "red bell", "place": "Fern Hall", "event_day": "7"}),
]


# p8 = p7 plus two worked examples for the actor errors of the development run ("you met X"
# and "you watched X leave ...": the actor is X)
EXAMPLES_P8 = EXAMPLES_P6 + [
    ("You met Tom Reed at Fern Hall on day 2.",
     {"actor": "Tom Reed", "partner": "none", "action": "was", "object": "none", "place": "Fern Hall", "event_day": "2"}),
    ("Day 7: at Rook Tower, you watched Mara Lind leave the green box.",
     {"actor": "Mara Lind", "partner": "none", "action": "left", "object": "green box", "place": "Rook Tower", "event_day": "7"}),
]


def messages(slot: str, text: str, prompt: str = "p2") -> list[dict]:
    if prompt not in PROMPTS:
        raise ValueError(prompt)
    question = QUESTIONS[slot]
    if slot == "partner" and prompt == "p4":
        question = Q_RECEIVER_P4
    if slot == "partner" and prompt in ("p5", "p7", "p8"):
        question = Q_RECEIVER_P5
    if slot == "partner" and prompt == "p6":
        question = Q_RECEIVER_P6
    examples = {"p3": EXAMPLES, "p4": EXAMPLES, "p5": EXAMPLES_P5, "p6": EXAMPLES_P6, "p7": EXAMPLES_P6,
                "p8": EXAMPLES_P8}.get(prompt, [])
    turns = [{"role": "system", "content": SYSTEM}]
    if examples:
        for note, answers in examples:
            turns += [{"role": "user", "content": f"Note: {note}\n\nQuestion: {question}"},
                      {"role": "assistant", "content": answers[slot]}]
    return turns + [{"role": "user", "content": f"Note: {text}\n\nQuestion: {question}"}]


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


def _best_per_value(entries: list, mode: str) -> dict:
    best = {}
    for _, c, s in view(entries, mode):
        if c not in best or s > best[c]:
            best[c] = s
    return best


def joint_roles(encoding: dict, action, mode: str = "sum") -> dict:
    """Joint choice of actor and receiver under the schema's role constraints (development
    proposal): the receiver differs from the actor; a person seen ("was") is never the
    narrator. Returns {slot: entries restricted to the values feasible given the other
    slot's joint choice}, so that the usual decision (choice, margin, threshold) applies to
    each slot within its feasible set."""
    A = _best_per_value(encoding["actor"], mode)
    R = _best_per_value(encoding["partner"], mode)

    def ok(a, r):
        return a != r and not (action == "was" and a == SELF_VALUE)
    pairs = [(sa + sr, str(a), str(r), a, r) for a, sa in A.items() for r, sr in R.items() if ok(a, r)]
    if not pairs:
        return {"actor": [], "partner": []}
    _, _, _, a_star, r_star = max(pairs, key=lambda p: (p[0], p[1], p[2]))
    return {"actor": [x for x in encoding["actor"] if ok(x[1], r_star)],
            "partner": [x for x in encoding["partner"] if ok(a_star, x[1])]}


def decide_record(encoding: dict, taus: dict, mode: str = "sum") -> tuple[dict, list, dict]:
    """(record content, declared unknown slots, per-slot detail) from a recorded encoding.
    taus[slot] = threshold or None (no qualifying threshold: always unknown)."""
    from .analysis35 import DECODING
    content, unknown, detail = {}, [], {}
    restricted = {}
    if DECODING.get("joint_roles"):
        action = ranking(view(encoding["action"], mode))[0]
        restricted = joint_roles(encoding, action, mode)
    for slot in SLOTS:
        entries = restricted.get(slot, encoding[slot])
        if slot == "partner" and DECODING.get("receiver_differs_from_actor") and detail.get("actor", {}).get("status") != "unknown":
            entries = [x for x in entries if x[1] != detail["actor"]["value"]]
        value, margin, status = decide(view(entries, mode), taus.get(slot))
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
