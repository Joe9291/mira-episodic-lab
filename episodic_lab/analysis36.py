"""Round 3.6 model-free analysis (docs/ROUND_3_6.md, design v3, sections 4-5): outcomes per
distinct question text, the parser criteria with explicit denominators, task decisions of
the agent with a given store (phase A: the correct store) and the parsed specification,
the original 3.3/3.4 intervention rows, PARSER_QUALIFIED.
"""
from __future__ import annotations

import collections
import math

from .analysis35 import cells, giver_of, oracle_rows, state_from_truth, variant, _records
from .env36 import split_pairs, split_questions
from .env_reference import plan as env_plan, predictions as env_predictions
from .history_agent import _act, history_place, state_decide
from .history_reference import plan as hist_plan, predictions as hist_predictions
from .memory import Result, latest
from .parser36 import decide_question
from .questions36 import SUPPORTED

WHICH = {"object_current": ("object", "current"), "object_first": ("object", "first"),
         "object_previous": ("object", "previous"), "person_current": ("person", "current"),
         "person_first": ("person", "first"), "person_previous": ("person", "previous")}


def answer(records, intent: str, target: str) -> Result:
    if intent == "giver":
        g = giver_of(records, target)
        return g if g.status != "ok" else latest(records, g.value)
    kind, which = WHICH[intent]
    return history_place(records, kind, target, which)


def act(records, parse: dict, decision: dict) -> dict:
    """The agent's action for a parsed question: OK -> operator and act (memory / explore);
    CLARIFY / REFUSE -> no movement."""
    if parse["outcome"] != "OK":
        return {"action": {"go": None}, "policy": parse["outcome"].lower()}
    return _act(answer(records, parse["intent"], parse["target"]), decision)


def gold_parse(gold: dict) -> dict:
    return {"outcome": gold["outcome"], "intent": gold["intent"] if gold["outcome"] == "OK" else None,
            "target": gold["target"] if gold["outcome"] == "OK" else None, "reason": None}


def outcomes(encodings: dict, taus: dict, texts) -> dict:
    return {t: decide_question(encodings[t], taus) for t in texts}


def right(parse: dict, gold: dict) -> bool:
    if parse["outcome"] != gold["outcome"]:
        return False
    return gold["outcome"] != "OK" or (parse["intent"], parse["target"]) == (gold["intent"], gold["target"])


def error_cause(parse: dict, gold: dict, candidates_have_gold: bool) -> str | None:
    """Astra's causes: missing gold candidate, wrong intent, wrong target, low confidence;
    None if right."""
    if right(parse, gold):
        return None
    if gold["outcome"] != "REFUSE" and not candidates_have_gold:
        return "gold_not_among_candidates"
    if parse.get("reason") == "low_confidence":
        return "low_confidence"
    if parse["intent"] != gold["intent"] and not (gold["outcome"] == "CLARIFY" and parse["outcome"] == "CLARIFY"):
        return "wrong_intent"
    return "wrong_target"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - h) / d), min(1.0, (c + h) / d))


def parser_metrics(parses: dict, gold: dict) -> dict:
    """The parser criteria of design v3 section 5 with numerators and denominators (distinct
    texts), plus family counts and macro means."""
    m = {}
    for t in SUPPORTED:
        for role in ("goal", "absent"):
            texts = [x for x, g in gold.items() if g["outcome"] == "OK" and g["intent"] == t and role in g["roles"]]
            m[f"exact:{t}:{role}"] = (sum(right(parses[x], gold[x]) for x in texts), len(texts))
        texts = [x for x, g in gold.items() if g["outcome"] == "OK" and g["intent"] == t]
        m[f"exact:{t}"] = (sum(right(parses[x], gold[x]) for x in texts), len(texts))
    ok_out = [x for x in gold if parses[x]["outcome"] == "OK"]
    m["wrong_accepted"] = (sum(not right(parses[x], gold[x]) for x in ok_out), len(ok_out))
    for cls, want in (("CLARIFY", "CLARIFY"), ("REFUSE", "REFUSE")):
        texts = [x for x, g in gold.items() if g["outcome"] == cls]
        m[f"false_ok:{cls}"] = (sum(parses[x]["outcome"] == "OK" for x in texts), len(texts))
        m[f"handled:{cls}"] = (sum(parses[x]["outcome"] == want for x in texts), len(texts))
    amb = [x for x, g in gold.items() if g["outcome"] == "CLARIFY"]
    m["recognised_ambiguity"] = (sum(parses[x]["outcome"] == "CLARIFY" and parses[x]["reason"] == "no_referent"
                                     for x in amb), len(amb))
    okg = [x for x, g in gold.items() if g["outcome"] == "OK"]
    m["unnecessary"] = (sum(parses[x]["outcome"] != "OK" for x in okg), len(okg))
    fam = collections.defaultdict(lambda: [0, 0])
    for x, g in gold.items():
        if g["outcome"] != "OK":
            fam[f"{g['outcome']}:{g['family']}"][0] += right(parses[x], g)
            fam[f"{g['outcome']}:{g['family']}"][1] += 1
    m["families"] = {k: tuple(v) for k, v in sorted(fam.items())}
    for cls in ("CLARIFY", "REFUSE"):
        rates = [k / n for f, (k, n) in fam.items() if f.startswith(cls) and n]
        m[f"family_macro:{cls}"] = sum(rates) / len(rates) if rates else None
    wording = collections.defaultdict(lambda: [0, 0])
    for x, g in gold.items():
        wording[g["wording"]][0] += right(parses[x], g)
        wording[g["wording"]][1] += 1
    m["wordings"] = {k: tuple(v) for k, v in sorted(wording.items())}
    return m


def _rate(kn):
    k, n = kn
    return k / n if n else None


def parser_criteria(m: dict) -> list[tuple[str, bool]]:
    """Design v3 section 5, criteria 1-5 (an empty denominator never passes)."""
    out = []
    for t in SUPPORTED:
        r = _rate(m[f"exact:{t}"])
        out.append((f"exact specification {t}: {m[f'exact:{t}'][0]}/{m[f'exact:{t}'][1]} >= 0.95",
                    r is not None and r >= 0.95))
    r = _rate(m["wrong_accepted"])
    out.append((f"wrong accepted specifications {m['wrong_accepted'][0]}/{m['wrong_accepted'][1]} <= 0.02",
                r is not None and r <= 0.02))
    for cls in ("CLARIFY", "REFUSE"):
        r = _rate(m[f"false_ok:{cls}"])
        out.append((f"false OK among gold-{cls} {m[f'false_ok:{cls}'][0]}/{m[f'false_ok:{cls}'][1]} <= 0.02",
                    r is not None and r <= 0.02))
        r = _rate(m[f"handled:{cls}"])
        out.append((f"{cls} among gold-{cls} {m[f'handled:{cls}'][0]}/{m[f'handled:{cls}'][1]} >= 0.90",
                    r is not None and r >= 0.90))
    r = _rate(m["unnecessary"])
    out.append((f"unnecessary CLARIFY/REFUSE among gold-OK {m['unnecessary'][0]}/{m['unnecessary'][1]} <= 0.05",
                r is not None and r <= 0.05))
    return out


def task_criteria(c: dict) -> list[tuple[str, bool]]:
    out = []
    for key, v in c.items():
        out.append((f"{key}: success LM {v['success_lm']:.3f} >= reference {v['success_ref']:.3f} - 0.02",
                    v["success_lm"] >= v["success_ref"] - 0.02))
        out.append((f"{key}: pair success {v['pair_success']:.3f} >= 0.95", v["pair_success"] >= 0.95))
        cer = v["confident_error_rate"]
        out.append((f"{key}: confident-error rate {'undefined' if cer is None else f'{cer:.3f}'} <= 0.05",
                    cer is not None and cer <= 0.05))
    return out


def tasks(split: str, parse_of: dict, store: str = "correct", rows_of=None) -> dict:
    """Intact decisions per pair/world/goal with the parsed goal question (parse_of: text ->
    parse) and the reference with the gold specification, on the correct store (phase A) or
    another store (rows_of(world) -> rows, phase B); intervention rows in the 3.3 / 3.4
    formats on the same store with the parsed specification."""
    rows_fn = rows_of or oracle_rows
    intact, rows33, rows34 = [], [], []
    for p in split_pairs(split):
        kind, seed = p["kind"], p["seed"]
        qs = {q["goal"]: q for q in p["questions"] if q["goal"]}
        for wname, w in p["worlds"].items():
            rows = rows_fn(w)
            if p["family"] == "env":
                goals, truth = {"find": w["decision"]}, {"find": w["truth"]}
            else:
                goals, truth = w["decisions"], w["truth"]
            for g, d in goals.items():
                q = qs[g]
                lm = act(_records(rows), parse_of[q["text"]], d)
                ref = act(_records(oracle_rows(w)), gold_parse(q["gold"]), d)
                intact.append({"kind": kind, "seed": seed, "world": wname, "goal": g, "truth": truth[g],
                               "lm_action": lm["action"]["go"], "lm_policy": lm["policy"],
                               "ref_action": ref["action"]["go"], "ref_policy": ref["policy"],
                               "outcome": parse_of[q["text"]]["outcome"]})
            if p["family"] == "env":
                specs, preds = env_plan(p, wname), env_predictions(p, wname)
                parse = parse_of[qs["find"]["text"]]
                for name, spec in specs.items():
                    row = {"kind": kind, "seed": seed, "world": wname, "intervention": name}
                    if spec is None:
                        rows33.append(dict(row, available=False))
                        continue
                    a = act(_records(variant(spec, rows)), parse, w["decision"])
                    rows33.append(dict(row, available=True, predicted=preds[name], truth=w["truth"],
                                       action=a["action"]["go"], policy=a["policy"],
                                       success=a["action"]["go"] == w["truth"],
                                       as_predicted=a["action"]["go"] == preds[name]))
            else:
                specs, preds = hist_plan(p, wname), hist_predictions(p, wname)
                state = state_from_truth(w["truth_content"])
                for g, d in w["decisions"].items():
                    parse = parse_of[qs[g]["text"]]
                    base = {"kind": kind, "seed": seed, "world": wname, "goal": g, "truth": w["truth"][g]}
                    s = state_decide(state, d)
                    rows34.append(dict(base, system="state_only", intervention="intact", available=True,
                                       action=s["action"]["go"], policy=s["policy"],
                                       success=s["action"]["go"] == w["truth"][g], predicted=None, as_predicted=None))
                    for name, spec in specs.items():
                        row = dict(base, system="episodic", intervention=name)
                        if spec is None:
                            rows34.append(dict(row, available=False))
                            continue
                        a = act(_records(variant(spec, rows)), parse, d)
                        pred = preds[name][g]
                        rows34.append(dict(row, available=True, predicted=pred, action=a["action"]["go"],
                                           policy=a["policy"], success=a["action"]["go"] == w["truth"][g],
                                           as_predicted=a["action"]["go"] == pred))
    return {"intact": intact, "rows33": rows33, "rows34": rows34}


def control_outcomes(split: str, parse_of: dict) -> dict:
    """Agent behaviour on the control questions with the correct store: not-in-memory ->
    {memory, explore, clarify, refuse} (explore = "I do not remember", the wanted one);
    ambiguous / unsupported -> outcome counts. Per world (both worlds)."""
    out = collections.defaultdict(collections.Counter)
    for p in split_pairs(split):
        for q in p["questions"]:
            if q["goal"]:
                continue
            for wname, w in p["worlds"].items():
                d = w["decision"] if p["family"] == "env" else next(iter(w["decisions"].values()))
                a = act(_records(oracle_rows(w)), parse_of[q["text"]], d)
                out[q["role"]][a["policy"]] += 1
    return {k: dict(v) for k, v in out.items()}


def parse_table(split: str, encodings: dict, taus: dict) -> dict:
    """text -> parse for EVERY question text of the split (repeated texts included)."""
    texts = {q["text"] for p in split_pairs(split) for q in p["questions"]}
    return outcomes(encodings, taus, texts)


def gold_of(split: str) -> dict:
    return split_questions(split)
