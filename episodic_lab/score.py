"""Evaluator: answer extraction, scoring and world-level statistics (protocol section 6).

Answer rule (fixed before use): the answer counts only if it names exactly one candidate
of the asked type (or is a "none" form); several or no candidates make it invalid, and
invalid answers are wrong. People may be named by full name or first name, places by
full name or stem, objects by full name or noun; each short form is unique in a world.
"""
from __future__ import annotations

import math
import re

NONE_FORMS = ("none", "nobody", "no one", "noone", "nothing", "nowhere", "never",
              "unknown", "not mentioned", "no such event", "did not happen")


def normalise(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return " ".join(text.split())


def _mentions(norm: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", norm) is not None


def extract(answer: str, answer_type: str, candidates: dict) -> str | None:
    """Return the canonical answer, "none", or None for an invalid answer."""
    if not isinstance(answer, str):
        return None
    first_line = answer.strip().split("\n", 1)[0]
    norm = normalise(first_line)
    if not norm:
        return None
    is_none = any(_mentions(norm, form) for form in NONE_FORMS)
    if answer_type == "choice":
        found = set(re.findall(r"(?<![A-Za-z])([AB])(?![A-Za-z])", first_line))
        return found.pop() if len(found) == 1 else None
    if answer_type == "day":
        days = set(re.findall(r"\d+", norm))
        if len(days) == 1 and not is_none:
            return str(int(days.pop()))
        return "none" if is_none and not days else None
    names = candidates[answer_type]
    hits = set()
    for name in names:
        forms = [normalise(name)]
        if answer_type == "person":
            forms.append(normalise(name.split()[0]))
        elif answer_type == "place":
            forms.append(normalise(name.split()[0]))
        elif answer_type == "object":
            forms.append(normalise(name.split()[-1]))
        if any(_mentions(norm, f) for f in forms):
            hits.add(name)
    if len(hits) == 1 and not is_none:
        return hits.pop()
    if not hits and is_none:
        return "none"
    return None


def score_world(gold: dict, candidates: dict, answers: dict, phase: str) -> list[dict]:
    """One record per question of the phase; `answers` maps qid -> raw answer text."""
    rows = []
    for qid, g in sorted(gold.items()):
        if phase == "phase1" and not g["phase1"]:
            continue
        raw = answers.get(qid)
        got = extract(raw, g["answer_type"], candidates) if raw is not None else None
        rows.append({"qid": qid, "criterion": g["criterion"], "qtype": g["qtype"],
                     "phase": phase, "extracted": got, "valid": got is not None,
                     "correct": got is not None and got in g["gold"],
                     "false_recall": g["gold"] == ["none"] and got not in (None, "none"),
                     "targets": g["targets"]})
    return rows


def summarise(rows: list[dict]) -> dict:
    """Per-criterion accuracy for one world and phase; E5 also as false-recall rate."""
    out = {}
    for criterion in sorted({r["criterion"] for r in rows}):
        sub = [r for r in rows if r["criterion"] == criterion]
        out[criterion] = {"n": len(sub), "accuracy": sum(r["correct"] for r in sub) / len(sub),
                          "invalid": sum(not r["valid"] for r in sub)}
        if criterion == "E5":
            out[criterion]["false_recall"] = sum(r["false_recall"] for r in sub) / len(sub)
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
    """Mean over worlds with a two-sided 95% t-interval (worlds are the units)."""
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, float("nan"), float("nan")
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    half = t975(n - 1) * sd / math.sqrt(n)
    return mean, mean - half, mean + half


def paired_difference(a: list[float], b: list[float]) -> tuple[float, float, float]:
    """Paired per-world difference a - b with its 95% t-interval."""
    if len(a) != len(b):
        raise ValueError("paired comparison needs the same worlds")
    return mean_interval([x - y for x, y in zip(a, b)])


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
    """One-sided exact (Clopper-Pearson) upper bound; n may be an effective sample size."""
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


def false_recall_bound(errors_per_world: list[int], questions_per_world: list[int],
                       design_effect: float = 1.0) -> float:
    """E5 upper bound on the pooled count with an effective sample size n / design effect."""
    errors = sum(errors_per_world)
    n = sum(questions_per_world)
    deff = max(1.0, design_effect)
    return upper_bound(errors / deff, n / deff)
