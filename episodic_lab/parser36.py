"""Round 3.6 LM-assisted question parsing (docs/ROUND_3_6.md, design v3, section 3).

Slots: `intent` (seven supported types and `unsupported`) and `target` (candidate spans of
the question plus `none`). The model scores every candidate as the complete answer to a
fixed slot question; the recorded encoding keeps every candidate with its canonical value
and score; the outcome is derived model-free by the decision table q1 (`decide_question`)
and the thresholds from the calibration split (`calibrate`).
"""
from __future__ import annotations

import re

from .cands35 import decide, ranking
from .questions36 import INTENTS, OBJECT_TYPES, PERSON_TYPES, SUPPORTED, UNSUPPORTED

DECODER_VERSION = "q1"
NONE = "none"
SLOTS = ("intent", "target")
DETERMINERS = ("the", "a", "an")
INTENT_DESCRIPTIONS = {
    "object_current": "where an object is now (its latest placing)",
    "object_first": "where an object was placed first",
    "object_previous": "where an object was before it was last placed",
    "person_current": "where a person was seen last",
    "person_first": "where a person was seen first",
    "person_previous": "where a person was seen the time before the last time",
    "giver": "the person who gave you an object (go to that person)",
    "unsupported": "anything else: why, how many, the future, who owns something, what happened right "
                   "before or after another event, who did something",
}

_TOKEN = re.compile(r"[A-Za-z]+(?:'s)?|[0-9]+|[^\sA-Za-z0-9]")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text)


def _strip(tok: str) -> str:
    return tok[:-2] if tok.endswith("'s") else tok


def target_candidates(text: str, max_len: int = 3) -> list[tuple[str, str]]:
    """[(surface, canonical)]: capitalised 1-3 token spans (persons), lower-case 1-3 token spans
    directly after a determiner (objects; possessive 's removed), plus none. Spans never
    cross punctuation; the first token of a capitalised span may be the question's first
    word (the model and `none` decide)."""
    toks = tokens(text)
    out = []
    for i in range(len(toks)):
        for n in range(1, max_len + 1):
            span = toks[i:i + n]
            if len(span) < n or not all(re.fullmatch(r"[A-Za-z]+(?:'s)?", t) for t in span):
                continue
            if any(t.endswith("'s") for t in span[:-1]):
                continue
            words = [_strip(t) for t in span]
            if all(w[0].isupper() for w in words):
                out.append((" ".join(span), " ".join(words)))
            elif i > 0 and toks[i - 1].lower() in DETERMINERS and all(w.islower() for w in words):
                out.append((" ".join(span), " ".join(words)))
    seen, uniq = set(), []
    for s, c in out + [(NONE, NONE)]:
        if s not in seen:
            seen.add(s)
            uniq.append((s, c))
    return uniq


def admissible(intent: str, value: str) -> bool:
    """Schema type rule of q1: object types and giver - two lower-case tokens; person types -
    two capitalised tokens."""
    words = value.split()
    if len(words) != 2:
        return False
    if intent in OBJECT_TYPES:
        return all(w.islower() and w.isalpha() for w in words)
    if intent in PERSON_TYPES:
        return all(w[0].isupper() and w[1:].islower() and w.isalpha() for w in words)
    return False


SYSTEM = ("You read one request that a person gives to an agent with an episodic memory and fill in one field "
          "of a structured query. Answer with only the value, nothing else.")
QUESTIONS = {
    "intent": ("Field 'intent': what kind of request is this? One of: "
               + "; ".join(f"{k} = {v}" for k, v in INTENT_DESCRIPTIONS.items())
               + ". Answer with one of these labels."),
    "target": ("Field 'target': the object (adjective and noun) or the person (first and last name) the request "
               "is about, exactly as written. If the request names no complete object or person (only 'it', "
               "'them', a bare noun or a first name), answer: none."),
}
PROMPTS = ("q1", "q2", "q3", "q4")
# q3 / q4 (development change after probe 1: "unsupported" almost never chosen, long label
# strings compete with different lengths under the sum score, the target of giver questions
# answered "none"): the intent as a multiple choice with equally short letter answers A-H
# (canonical value = the label); the target question asks for the complete object or full
# name WRITTEN in the request. q3 with the worked examples of q2, q4 without.
LETTER_PROMPTS = ("q3", "q4")
LETTERS = "ABCDEFGH"
LETTER_OF = dict(zip(INTENTS, LETTERS))
Q_INTENT_LETTERS = ("Which option describes the request? "
                    + " ".join(f"{LETTER_OF[k]}) {v}." for k, v in INTENT_DESCRIPTIONS.items())
                    + " Answer with the letter only.")
Q_TARGET_V2 = ("Which complete object (adjective and noun, for example 'green box') or full name (first and last "
               "name, for example 'Mara Lind') is written in the request? Answer with it exactly as written. "
               "If the request contains no complete object and no full name (only 'it', 'them', a bare noun "
               "or a first name), answer: none.")
# q2 = q1 plus worked examples as earlier chat turns (development: names, places and objects
# outside the world vocabulary; every intent and both control kinds)
EXAMPLES_Q2 = [
    ("Where is the green box now?", {"intent": "object_current", "target": "green box"}),
    ("Where did you see Mara Lind for the first time?", {"intent": "person_first", "target": "Mara Lind"}),
    ("Go to the person you got the old key from.", {"intent": "giver", "target": "old key"}),
    ("Where was the small drum before its last move?", {"intent": "object_previous", "target": "small drum"}),
    ("Find the box.", {"intent": "object_current", "target": "none"}),
    ("Why did Tom Reed hide the red bell?", {"intent": "unsupported", "target": "none"}),
    ("Where did you go after Ida Voss met you?", {"intent": "unsupported", "target": "none"}),
    ("Go to Mara.", {"intent": "person_current", "target": "none"}),
]


# q5 / q6 (development change after probe 2: "unsupported" has a very low label prior - its
# gold label ranks 4-6 - and person_current is often confused; examples with target "none"
# biased q3 towards CLARIFY): q4's letter intent and written-target question PLUS three
# recorded development slots for an offline comparison of a factorised decoder (answerable
# yes/no, kind object/person/giver, time latest/first/previous) and content-free scores
# ("(no request)") of every label slot for an offline prior correction. q5 with balanced
# per-slot worked examples (the target examples answer "none" only once), q6 without.
PROMPTS = PROMPTS + ("q5", "q6")
LETTER_PROMPTS = LETTER_PROMPTS + ("q5", "q6")
FACTOR_PROMPTS = ("q5", "q6")
FACTOR_SLOTS = ("answerable", "kind", "when")
FACTOR_LABELS = {"answerable": ("yes", "no"), "kind": ("object", "person", "giver"),
                 "when": ("latest", "first", "previous")}
FACTOR_QUESTIONS = {
    "answerable": ("Can this request be answered from memory by naming ONE place: where an object is now, was "
                   "first placed, or was before its last placing; where a person was seen last, first, or the time "
                   "before the last; or where the person who gave you an object is now? Answer yes or no."),
    "kind": ("Is the request about the place of an object, the place of a person, or the person who gave you an "
             "object? Answer object, person, or giver."),
    "when": ("Which time does the request ask for: the latest one (now, last), the first one, or the one before "
             "the latest? Answer latest, first, or previous."),
}
NULL_REQUEST = "(no request)"
EXAMPLES_Q5 = [
    ("Where is the green box now?", {"intent": "object_current", "target": "green box", "answerable": "yes",
                                     "kind": "object", "when": "latest"}),
    ("Go to where the small drum was first placed.", {"intent": "object_first", "target": "small drum",
                                                      "answerable": "yes", "kind": "object", "when": "first"}),
    ("Where was the old key before its last move?", {"intent": "object_previous", "target": "old key",
                                                     "answerable": "yes", "kind": "object", "when": "previous"}),
    ("Where is Mara Lind now?", {"intent": "person_current", "target": "Mara Lind", "answerable": "yes",
                                 "kind": "person", "when": "latest"}),
    ("Where did you see Tom Reed for the first time?", {"intent": "person_first", "target": "Tom Reed",
                                                        "answerable": "yes", "kind": "person", "when": "first"}),
    ("Where did you see Ida Voss before the last time?", {"intent": "person_previous", "target": "Ida Voss",
                                                          "answerable": "yes", "kind": "person", "when": "previous"}),
    ("Go to the person you got the red bell from.", {"intent": "giver", "target": "red bell", "answerable": "yes",
                                                     "kind": "giver", "when": "latest"}),
    ("Find the box.", {"intent": "object_current", "target": "none", "answerable": "yes", "kind": "object",
                       "when": "latest"}),
    ("Why did Tom Reed hide the green box?", {"intent": "unsupported", "answerable": "no"}),
    ("Where will the old key be tomorrow?", {"intent": "unsupported", "answerable": "no"}),
    ("Where was Mara Lind just after she met you?", {"intent": "unsupported", "answerable": "no"}),
]


def factor_messages(slot: str, text: str, prompt: str) -> list[dict]:
    question = FACTOR_QUESTIONS[slot]
    turns = [{"role": "system", "content": SYSTEM}]
    for req, answers in (EXAMPLES_Q5 if prompt == "q5" else []):
        if slot in answers:
            turns += [{"role": "user", "content": f"Request: {req}\n\nQuestion: {question}"},
                      {"role": "assistant", "content": answers[slot]}]
    return turns + [{"role": "user", "content": f"Request: {text}\n\nQuestion: {question}"}]


def messages(slot: str, text: str, prompt: str = "q1") -> list[dict]:
    if prompt not in PROMPTS:
        raise ValueError(prompt)
    if slot in FACTOR_SLOTS:
        return factor_messages(slot, text, prompt)
    question = QUESTIONS[slot]
    if prompt in LETTER_PROMPTS:
        question = Q_INTENT_LETTERS if slot == "intent" else Q_TARGET_V2
    turns = [{"role": "system", "content": SYSTEM}]
    for req, answers in {"q2": EXAMPLES_Q2, "q3": EXAMPLES_Q2, "q5": EXAMPLES_Q5}.get(prompt, []):
        if slot not in answers:
            continue
        answer = LETTER_OF[answers[slot]] if (slot == "intent" and prompt in LETTER_PROMPTS) else answers[slot]
        turns += [{"role": "user", "content": f"Request: {req}\n\nQuestion: {question}"},
                  {"role": "assistant", "content": answer}]
    return turns + [{"role": "user", "content": f"Request: {text}\n\nQuestion: {question}"}]


def candidates(slot: str, text: str, prompt: str = "q1") -> list[tuple[str, str]]:
    """[(surface scored by the model, canonical value)]."""
    if slot in FACTOR_SLOTS:
        return [(x, x) for x in FACTOR_LABELS[slot]]
    if slot == "intent":
        if prompt in LETTER_PROMPTS:
            return [(LETTER_OF[k], k) for k in INTENTS]
        return [(k, k) for k in INTENTS]
    return target_candidates(text)


def encode_question(scorer, text: str, ntokens=None, prompt: str = "q1") -> dict:
    """{slot: [[surface, canonical, score, None, tokens], ...]} (score = total log-probability
    of the complete answer after the slot question)."""
    out = {}
    for slot in SLOTS + (FACTOR_SLOTS if prompt in FACTOR_PROMPTS else ()):
        cands = candidates(slot, text, prompt)
        surf = [s for s, _ in cands]
        scores = scorer(messages(slot, text, prompt), surf)
        nulls = ([None] * len(surf) if (slot == "target" or prompt not in FACTOR_PROMPTS)
                 else null_scores(scorer, slot, prompt, surf))
        out[slot] = [[s, c, float(x), None if n is None else float(n), ntokens(s) if ntokens else None]
                     for (s, c), x, n in zip(cands, scores, nulls)]
    return out


_NULL_CACHE: dict = {}


def null_scores(scorer, slot: str, prompt: str, surfaces: list[str]) -> list[float]:
    """Content-free scores of a label slot ("(no request)"), cached per process."""
    key = (slot, prompt, tuple(surfaces))   # one model per process
    if key not in _NULL_CACHE:
        _NULL_CACHE[key] = list(scorer(messages(slot, NULL_REQUEST, prompt), surfaces))
    return _NULL_CACHE[key]


def _scored(entries: list) -> list[tuple]:
    return [(x[0], x[1], x[2]) for x in entries]


def target_view(encoding: dict, intent: str) -> list[tuple]:
    """The target candidates admissible for a supported intent, plus none."""
    return [x for x in _scored(encoding["target"]) if x[1] == NONE or admissible(intent, x[1])]


def decide_question(encoding: dict, taus: dict) -> dict:
    """Decision table q1 (design v3, section 3): exactly one outcome per question.
    {outcome: OK | CLARIFY | REFUSE, reason, intent, target, detail}."""
    value, margin, status = decide(_scored(encoding["intent"]), taus.get("intent"))
    det = {"intent": {"value": value, "margin": margin, "status": status}}
    if status == "unknown":
        return {"outcome": "CLARIFY", "reason": "low_confidence", "intent": None, "target": None, "detail": det}
    if value == UNSUPPORTED:
        return {"outcome": "REFUSE", "reason": None, "intent": UNSUPPORTED, "target": None, "detail": det}
    view = target_view(encoding, value)
    if not any(x[1] != NONE for x in view):
        det["target"] = {"value": NONE, "margin": None, "status": "no_admissible"}
        return {"outcome": "CLARIFY", "reason": "no_referent", "intent": value, "target": None, "detail": det}
    tv, tm, ts = decide(view, taus.get("target"))
    det["target"] = {"value": tv, "margin": tm, "status": ts}
    if ts == "unknown":
        return {"outcome": "CLARIFY", "reason": "low_confidence", "intent": value, "target": None, "detail": det}
    if tv == NONE:
        return {"outcome": "CLARIFY", "reason": "no_referent", "intent": value, "target": None, "detail": det}
    return {"outcome": "OK", "reason": None, "intent": value, "target": tv, "detail": det}


MIN_ACCEPTED = 200
PRECISION = 0.99


def _threshold(items: list[tuple[float, bool]]) -> dict:
    best = None
    for tau in sorted({m for m, _ in items if m > 0} | {0.0}):
        acc = [ok for m, ok in items if m > 0 and m >= tau]
        if len(acc) < MIN_ACCEPTED:
            continue
        prec = sum(acc) / len(acc)
        rate = len(acc) / len(items)
        if prec >= PRECISION and (best is None or rate > best[1]):
            best = (tau, rate, prec, len(acc))
    return {"tau": best[0] if best else None, "acceptance": best[1] if best else 0.0,
            "precision": best[2] if best else None, "accepted": best[3] if best else 0, "items": len(items)}


def calibrate(encodings: dict, gold: dict) -> dict:
    """Design v3: tau_intent over all distinct texts with a gold intent; tau_target over the
    texts with a defined gold target (gold-unsupported excluded) whose intent is ACCEPTED
    as supported with tau_intent and that have >= 2 values among admissible + none.
    Returns {slot: {...}, "flow": {...}} (Astra's calibration flow)."""
    texts = [t for t in encodings if t in gold]
    items = []
    for t in texts:
        value, margin, n = ranking(_scored(encodings[t]["intent"]))
        if n >= 2:
            items.append((margin, value == gold[t]["intent"]))
    out = {"intent": _threshold(items)}
    tau_i = out["intent"]["tau"]
    calibratable = [t for t in texts if gold[t]["outcome"] in ("OK", "CLARIFY")]
    after_intent, titems = [], []
    for t in calibratable:
        value, margin, status = decide(_scored(encodings[t]["intent"]), tau_i)
        if status == "unknown" or value not in SUPPORTED:
            continue
        after_intent.append(t)
        tv, tm, n = ranking(target_view(encodings[t], value))
        if n >= 2:
            titems.append((tm, tv == gold[t]["target"]))
    out["target"] = _threshold(titems)
    out["flow"] = {"distinct": len(texts), "intent_items": len(items), "target_calibratable": len(calibratable),
                   "after_accepted_intent": len(after_intent), "target_items": len(titems),
                   "target_accepted": out["target"]["accepted"]}
    return out
