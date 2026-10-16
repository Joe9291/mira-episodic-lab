"""Evaluator: answer parsing, scoring and world-level statistics (protocol section 6).

Answer grammar (PARSER_VERSION, fixed before use). Only the first line counts. After
normalisation (case, punctuation) and removal of a fixed list of leading filler phrases,
the rest must be EXACTLY one allowed form:
- person: full name or first name; place: full name or name stem; object: full name or
  noun (an optional leading "the" is allowed); each short form is unique in a world;
- day: "<n>" or "day <n>"; choice: "a" or "b" (also "option a");
- rejection: one of NONE_FORMS; uncertainty: one of UNCERTAIN_FORMS.
Anything else (several names, negations, extra or contradicting words, unknown names)
is category "other" and counts as wrong. Categories per answer:
correct, wrong_value (an allowed in-world value, but wrong), none_answer (rejection
although an event exists), uncertain, other.
"""
from __future__ import annotations

import math
import re

PARSER_VERSION = "episodic_lab.parser.v2"
NONE_FORMS = ("none", "nobody", "no one", "nothing", "nowhere", "never",
              "no such event", "it did not happen", "that did not happen")
UNCERTAIN_FORMS = ("unknown", "i don't know", "i do not know", "not sure", "i am not sure",
                   "i'm not sure", "cannot tell", "can't tell")
FILLERS = ("the answer is", "answer is", "answer", "it was", "it is", "they were", "at", "in",
           "on")


def normalise(text: str) -> str:
    text = text.lower().replace("\u2019", "'")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return " ".join(text.split())


def _strip_fillers(norm: str) -> str:
    changed = True
    while changed:
        changed = False
        for filler in FILLERS:
            if norm.startswith(filler + " "):
                norm = norm[len(filler) + 1:]
                changed = True
    return norm


def _forms(name: str, answer_type: str) -> set[str]:
    full = normalise(name)
    short = {"person": full.split()[0], "place": full.split()[0], "object": full.split()[-1]}
    forms = {full, short[answer_type]}
    if answer_type in ("place", "object"):
        forms |= {"the " + f for f in forms}
    return forms


def parse(answer: str, answer_type: str, candidates: dict) -> tuple[str, str | None]:
    """Return (kind, value): kind is "value", "none", "uncertain" or "other"."""
    if not isinstance(answer, str) or not answer.strip():
        return "other", None
    norm = _strip_fillers(normalise(answer.strip().split("\n", 1)[0]))
    if norm in NONE_FORMS:
        return "none", "none"
    if norm in UNCERTAIN_FORMS:
        return "uncertain", None
    if answer_type == "choice":
        m = re.fullmatch(r"(?:option )?([ab])", norm)
        return ("value", m.group(1).upper()) if m else ("other", None)
    if answer_type == "day":
        m = re.fullmatch(r"(?:day )?(\d+)", norm)
        return ("value", str(int(m.group(1)))) if m else ("other", None)
    hits = [name for name in candidates[answer_type] if norm in _forms(name, answer_type)]
    return ("value", hits[0]) if len(hits) == 1 else ("other", None)


def extract(answer: str, answer_type: str, candidates: dict) -> str | None:
    """Canonical value, "none", or None (uncertain or other)."""
    kind, value = parse(answer, answer_type, candidates)
    return value if kind in ("value", "none") else None


def score_world(gold: dict, candidates: dict, answers: dict, phase: str) -> list[dict]:
    """One record per question of the phase; `answers` maps qid -> raw answer text."""
    rows = []
    for qid, g in sorted(gold.items()):
        if phase == "phase1" and not g["phase1"]:
            continue
        raw = answers.get(qid)
        kind, value = parse(raw, g["answer_type"], candidates)
        correct = kind in ("value", "none") and value in g["gold"]
        if correct:
            category = "correct"
        elif kind == "value":
            category = "wrong_value"
        elif kind == "none":
            category = "none_answer"
        else:
            category = kind
        rows.append({"qid": qid, "criterion": g["criterion"], "qtype": g["qtype"],
                     "phase": phase, "raw": raw, "parser": PARSER_VERSION,
                     "extracted": value, "category": category, "correct": correct,
                     "false_recall": g["gold"] == ["none"] and kind == "value",
                     "targets": g["targets"]})
        if "pair" in g:
            rows[-1]["pair"] = g["pair"]
    return rows


def summarise(rows: list[dict]) -> dict:
    """Per criterion: accuracy and the share of every answer category. For E5,
    accuracy is the correct-rejection rate and false_recall the share of in-world claims;
    uncertain and other answers are reported separately and are not rejections."""
    out = {}
    for criterion in sorted({r["criterion"] for r in rows}):
        sub = [r for r in rows if r["criterion"] == criterion]
        n = len(sub)
        out[criterion] = {"n": n, "accuracy": sum(r["correct"] for r in sub) / n,
                          "categories": {c: sum(r["category"] == c for r in sub) / n
                                         for c in ("correct", "wrong_value", "none_answer",
                                                   "uncertain", "other")}}
        if criterion == "E5":
            out[criterion]["false_recall"] = sum(r["false_recall"] for r in sub) / n
        if any("pair" in r for r in sub):  # variant v1: E3a asked in both A/B orders
            pairs = {}
            for r in sub:
                pairs.setdefault(r["pair"], []).append(r["correct"])
            out[criterion]["pairs"] = {"n": len(pairs), "both_correct": sum(
                len(v) == 2 and all(v) for v in pairs.values()) / len(pairs)}
        if criterion == "E3b":  # the two subtypes are reported separately (protocol E3b)
            out[criterion]["by_qtype"] = {
                q: {"n": len(s), "accuracy": sum(r["correct"] for r in s) / len(s)}
                for q in sorted({r["qtype"] for r in sub})
                for s in [[r for r in sub if r["qtype"] == q]]}
    return out


# ---------------------------------------------------------------- statistics over worlds
_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
         9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
         16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 25: 2.060, 30: 2.042,
         40: 2.021, 60: 2.000, 120: 1.980}


def t975(df: int) -> float:
    if df < 1:
        raise ValueError("need at least two worlds")
    if df > 120:
        return 1.980  # conservative: value for df = 120
    # conservative: the largest tabulated df not above the actual df (larger quantile)
    return _T975[max(k for k in _T975 if k <= df)]


def mean_interval(values: list[float]) -> tuple[float, float, float]:
    """Mean over worlds with a two-sided 95% t-interval (worlds are the units).

    Descriptive: it assumes approximately normal world means and has zero width when all
    worlds score the same, which is no certainty about new worlds. Confirmatory decisions
    use `world_rate_bounds` on independent world-level indicators instead."""
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, float("nan"), float("nan")
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    half = t975(n - 1) * sd / math.sqrt(n)
    return mean, mean - half, mean + half


def paired_difference(a: dict, b: dict) -> tuple[float, float, float]:
    """Paired per-world difference a - b; a and b map world id -> score."""
    if set(a) != set(b):
        raise ValueError("paired comparison needs exactly the same worlds")
    return mean_interval([a[w] - b[w] for w in sorted(a)])


def _betacf(a: float, b: float, x: float) -> float:
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > 1e-300 else 1e-300
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def upper_bound(errors: float, n: float, confidence: float = 0.95) -> float:
    """One-sided Clopper-Pearson upper bound. Exact only for integer counts of
    independent trials; with fractional (effective) counts it is an approximation."""
    if n <= 0:
        return 1.0
    errors = min(errors, n)
    if errors >= n:
        return 1.0
    lo, hi = errors / n, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        # P(X <= errors | p = mid) = 1 - I_mid(errors + 1, n - errors)
        if 1.0 - betainc(errors + 1.0, n - errors, mid) > 1.0 - confidence:
            lo = mid
        else:
            hi = mid
    return hi


def lower_bound(successes: float, n: float, confidence: float = 0.95) -> float:
    """One-sided Clopper-Pearson lower bound (mirror of `upper_bound`)."""
    return 1.0 - upper_bound(n - successes, n, confidence)


def world_rate_bounds(indicators: dict, confidence: float = 0.95) -> tuple[float, float]:
    """Exact one-sided bounds for the probability that a new world has the property,
    from one independent 0/1 indicator per world (world id -> bool). Used for
    confirmatory decisions, e.g. "the world meets the E2 threshold" (lower bound) or
    "the world has at least one in-world false recall" (upper bound)."""
    if not indicators or any(type(v) is not bool for v in indicators.values()):
        raise ValueError("world indicators must be a non-empty map of real booleans")
    n = len(indicators)
    k = sum(indicators.values())
    return lower_bound(k, n, confidence), upper_bound(k, n, confidence)


def false_recall_bound(errors_per_world: list[int], questions_per_world: list[int],
                       design_effect: float = 1.0) -> float:
    """Descriptive E5 bound on the pooled count with an effective sample size
    n / design effect; it treats questions as independent when design_effect is 1 and
    is no confirmatory guarantee (see `world_rate_bounds`)."""
    errors = sum(errors_per_world)
    n = sum(questions_per_world)
    deff = max(1.0, design_effect)
    return upper_bound(errors / deff, n / deff)
