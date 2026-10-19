"""Round 3.5 model-free analysis (docs/ROUND_3_5.md sections 2-4): everything after the
model's scores. Used by the collector and by the tests (with a fake scorer).

- truths per distinct text (from the generator's structured events);
- record quality per slot (correct / unknown / wrong), by role and absence, single-value
  slots separately;
- thresholds per slot on the calibration split;
- stores per world from the recorded encodings (declared unknowns kept), the reference
  store from the structured truth (oracle encoding), decisions with the fixed goal parser
  and unknown-aware operators, success per world kind x goal, pair success,
  confident-error rate and coverage, interventions separately;
- ENCODER_QUALIFIED and MILESTONE_ORIGINAL_RULES.
"""
from __future__ import annotations

import statistics

from .cands35 import NONE, SELF, SLOTS, STRUCTURAL, ranking, truth_value
from .encoder35 import DECISION_ORDER, decide_record, decide_slot, slot_view
from .env import PLACING, parse_goal
from .env35 import KINDS35, split_pairs
from .env_reference import plan as env_plan, predictions as env_predictions
from .history_agent import _act, decide as hist_decide
from .history_agent import history_place
from .history_reference import plan as hist_plan, predictions as hist_predictions
from .memory import EpisodeStore, Result, latest, match, possible, unknown

FIELDS = ("actor", "partner", "action", "object", "place", "event_day")
# decoding options (development proposals, set by the collector from the request):
#   receiver_differs_from_actor - the receiver's choice excludes the chosen actor's value
#   structural_slots            - a slot with only single-value cases in calibration accepts
#                                 single values (its rare choices stay unknown)
#   joint_roles                 - actor and receiver chosen jointly under the role constraints
#                                 (receiver differs from actor; a person seen is not the narrator)
#   object_two_tokens, gave_receiver_self - round 3.5b schema rules (decoder d3, see encoder35)
DECODING = {"receiver_differs_from_actor": False, "structural_slots": False, "joint_roles": False,
            "object_two_tokens": False, "gave_receiver_self": False}
DECODING_OFF = dict(DECODING)
MIN_ACCEPTED = 200
PRECISION = 0.99


# ----------------------------------------------------------------- truths and quality
def truths(split: str) -> dict:
    """{text: structured content}; a text always maps to one content (exact inverse parsers)."""
    out = {}
    for p in split_pairs(split):
        for w in p["worlds"].values():
            for e, c in zip(w["experiences"], w["truth_content"]):
                if out.setdefault(e["text"], c) != c:
                    raise AssertionError(f"one text, two contents: {e['text']}")
    return out


def role(slot: str, content: dict) -> str:
    """Role/absence class of a slot's truth (Astra's breakdown)."""
    v = content[slot]
    if slot in ("actor", "partner"):
        if v is None:
            return "absent"
        if v == SELF:
            return "You"
        return "giver" if content["action"] == "gave" and slot == "actor" else "observed_person"
    if slot == "object":
        return "absent" if v is None else "present"
    return "-"


def quality(encodings: dict, truth: dict, taus: dict, mode: str = "sum") -> dict:
    """Per slot correct/unknown/wrong over distinct texts, single-value slots separately,
    by role; complete records with every slot correct."""
    per = {s: {"correct": 0, "unknown": 0, "wrong": 0, "single": 0, "single_text": 0,
                 "single_schema": 0, "chosen_correct": 0, "chosen": 0} for s in SLOTS}
    roles = {}
    complete = 0
    n = 0
    for text, enc in encodings.items():
        if text not in truth:
            continue
        n += 1
        content, unk, detail = decide_record(enc, taus, mode)
        ok_all = True
        for s in SLOTS:
            want = truth_value(s, truth[text])
            d = detail[s]
            if d["status"] == "unknown":
                st = "unknown"
            else:
                st = "correct" if d["value"] == want else "wrong"
            per[s][st] += 1
            if d["status"] == "single":
                per[s]["single"] += 1
                per[s]["single_" + d["origin"]] += 1
            else:
                per[s]["chosen"] += 1
                per[s]["chosen_correct"] += st == "correct"
            key = f"{s}:{role(s, truth[text])}"
            roles.setdefault(key, {"correct": 0, "unknown": 0, "wrong": 0})[st] += 1
            ok_all &= st == "correct"
        complete += ok_all
    return {"texts": n, "slots": per, "roles": roles, "complete_records": complete / n if n else None}


def frame_quality(split: str, encodings: dict, taus: dict, mode: str = "sum") -> dict:
    """{wording frame: [distinct texts, complete records correct]} (development diagnosis)."""
    frames = {}
    for p in split_pairs(split):
        for w in p["worlds"].values():
            for e, c in zip(w["experiences"], w["truth_content"]):
                frames.setdefault(e["frame"], {})[e["text"]] = c
    out = {}
    for frame, items in sorted(frames.items()):
        ok = 0
        for text, c in items.items():
            content, unk, detail = decide_record(encodings[text], taus, mode)
            ok += all(detail[s]["status"] != "unknown" and detail[s]["value"] == truth_value(s, c) for s in SLOTS)
        out[frame] = [len(items), ok]
    return out


def class_diagnostics(split: str, encodings: dict, taus: dict, mode: str = "sum") -> dict:
    """Per value class, with denominators (round 3.5b): {class: [texts, wrong slots, unknown
    slots, smallest margin of a correct choice or None]} for the object adjective, the
    wording frame and the role of each slot (distinct texts). A small minimum margin is a
    search aid, not a reliability guarantee."""
    out = {}
    seen = set()
    for p in split_pairs(split):
        for w in p["worlds"].values():
            for e, c in zip(w["experiences"], w["truth_content"]):
                if e["text"] in seen:
                    continue
                seen.add(e["text"])
                det = decide_record(encodings[e["text"]], taus, mode)[2]
                keys = [f"frame:{e['frame']}"] + [f"role:{s}:{role(s, c)}" for s in SLOTS]
                if c["object"]:
                    keys.append(f"adjective:{c['object'].split()[0]}")
                wrong = sum(det[s]["status"] != "unknown" and det[s]["value"] != truth_value(s, c) for s in SLOTS)
                unk = sum(det[s]["status"] == "unknown" for s in SLOTS)
                margins = [det[s]["margin"] for s in SLOTS if det[s]["status"] == "ok"
                           and det[s]["value"] == truth_value(s, c) and det[s]["margin"] is not None]
                for k in keys:
                    if k.startswith("role:"):
                        sl = k.split(":")[1]
                        w_, u_ = (det[sl]["status"] != "unknown" and det[sl]["value"] != truth_value(sl, c),
                                  det[sl]["status"] == "unknown")
                        m_ = [det[sl]["margin"]] if (det[sl]["status"] == "ok" and not w_) else []
                    elif k.startswith("adjective:"):
                        d = det["object"]
                        w_, u_ = d["status"] != "unknown" and d["value"] != c["object"], d["status"] == "unknown"
                        m_ = [d["margin"]] if (d["status"] == "ok" and not w_) else []
                    else:
                        w_, u_, m_ = wrong, unk, margins
                    v = out.setdefault(k, [0, 0, 0, None])
                    v[0] += 1
                    v[1] += int(w_)
                    v[2] += int(u_)
                    if m_:
                        v[3] = min(m_) if v[3] is None else min(v[3], min(m_))
    return dict(sorted(out.items()))


def consequences(split: str, encodings: dict, taus: dict, mode: str = "sum") -> list[dict]:
    """Error consequences (round 3.5b): for every world and goal whose LM decision is wrong
    or not taken from memory: the wrong or unknown record fields of that world -> the
    policy (memory or fallback) -> the action and whether it is right."""
    out = []
    by = {(p["kind"], p["seed"]): p for p in split_pairs(split)}
    for r in tasks(split, encodings, taus, mode)["intact"]:
        if r["lm_action"] == r["truth"] and r["lm_policy"] == "memory":
            continue
        w = by[(r["kind"], r["seed"])]["worlds"][r["world"]]
        faults = []
        for i, (e, c) in enumerate(zip(w["experiences"], w["truth_content"])):
            det = decide_record(encodings[e["text"]], taus, mode)[2]
            for s in SLOTS:
                if det[s]["status"] == "unknown" or det[s]["value"] != truth_value(s, c):
                    faults.append(f"note {i} {s}: {det[s]['value'] if det[s]['status'] != 'unknown' else '?'} "
                                  f"(true {truth_value(s, c)}) | {e['text']}")
        out.append({"kind": r["kind"], "seed": r["seed"], "world": r["world"], "goal": r["goal"],
                    "policy": r["lm_policy"], "action": r["lm_action"], "truth": r["truth"],
                    "right": r["lm_action"] == r["truth"], "faults": faults})
    return out


def calibrate(encodings: dict, truth: dict, mode: str = "sum") -> dict:
    """Per slot, in DECISION_ORDER and with the same decision steps as decide_record (a later
    slot sees the earlier slots decided with their calibrated thresholds): the threshold with
    the highest acceptance rate subject to precision >= 0.99 and >= 200 accepted values among
    the multi-value cases; ties to the smaller threshold; None if no threshold qualifies (the
    slot is then always unknown).
    basis: "multi" (multi-value cases exist), "single_only" (every evaluable case had one value:
    with structural_slots the slot is STRUCTURAL if >= 200 single values with precision >= 0.99,
    else None) or "none" (no evaluable case: None)."""
    usable = [(enc, truth[text]) for text, enc in encodings.items() if text in truth]
    details = [{} for _ in usable]
    out = {}
    for s in DECISION_ORDER:
        items, singles = [], []
        for (enc, t), det in zip(usable, details):
            value, margin, n = ranking(slot_view(enc, s, det, mode))
            if n >= 2:
                items.append((margin, value == truth_value(s, t)))
            elif n == 1:
                singles.append(value == truth_value(s, t))
        sprec = sum(singles) / len(singles) if singles else None
        base = {"items": len(items), "singles": len(singles), "single_precision": sprec}
        if not items:
            ok = (DECODING.get("structural_slots") and len(singles) >= MIN_ACCEPTED and sprec >= PRECISION)
            out[s] = {"tau": STRUCTURAL if ok else None, "acceptance": None, "precision": None, "accepted": 0,
                      "basis": "single_only" if singles else "none", **base}
        else:
            best = None
            for tau in sorted({m for m, _ in items if m > 0} | {0.0}):
                acc = [ok for m, ok in items if m > 0 and m >= tau]
                if len(acc) < MIN_ACCEPTED:
                    continue
                prec = sum(acc) / len(acc)
                rate = len(acc) / len(items)
                if prec >= PRECISION and (best is None or rate > best[1]):
                    best = (tau, rate, prec, len(acc))
            out[s] = {"tau": best[0] if best else None, "acceptance": best[1] if best else 0.0,
                      "precision": best[2] if best else None, "accepted": best[3] if best else 0,
                      "basis": "multi", **base}
        for (enc, _), det in zip(usable, details):
            det[s] = decide_slot(enc, s, det, out[s]["tau"], mode)
    return {s: out[s] for s in SLOTS}


def rescored(encodings: dict, kind: str) -> dict:
    """Schema-constrained controls: the same candidates and the same decoder, the model's
    scores replaced by "uniform" (all equal: only what candidates and constraints determine)
    or "random" (deterministic pseudo-random scores per text, slot and surface)."""
    import hashlib
    out = {}
    for text, enc in encodings.items():
        new = {}
        for slot, entries in enc.items():
            rows = []
            for x in entries:
                if kind == "uniform":
                    sc = 0.0
                elif kind == "random":
                    h = hashlib.sha256(f"{text}|{slot}|{x[0]}".encode()).digest()
                    sc = -10.0 * int.from_bytes(h[:8], "big") / 2 ** 64
                else:
                    raise ValueError(kind)
                rows.append([x[0], x[1], sc] + list(x[3:]))
            new[slot] = rows
        out[text] = new
    return out


# ----------------------------------------------------------------- stores and operators
def _records(rows: list[tuple[dict, list]]) -> list[dict]:
    s = EpisodeStore()
    for i, (c, unk) in enumerate(rows):
        s.append(f"e{i}", {k: c[k] for k in FIELDS}, extra={"unknown": list(unk)} if unk else None)
    return s.records


def variant(spec: dict, rows: list[tuple[dict, list]]) -> list[tuple[dict, list]]:
    """An intervention on (content, unknown slots) rows; unknown flags travel with their
    values (a swapped field swaps its unknown flag too)."""
    rows = [(dict(c), list(u)) for c, u in rows]
    op = spec["op"]
    if op == "keep":
        return rows
    if op == "clear":
        return []
    if op == "replace":
        return [({k: e[k] for k in FIELDS}, []) for e in spec["events"]]
    if op == "remove":
        return [r for n, r in enumerate(rows) if n != spec["i"]]
    if op == "swap":
        f, i, j = spec["field"], spec["i"], spec["j"]
        (ci, ui), (cj, uj) = rows[i], rows[j]
        ci[f], cj[f] = cj[f], ci[f]
        fi, fj = f in ui, f in uj
        ui = [x for x in ui if x != f] + ([f] if fj else [])
        uj = [x for x in uj if x != f] + ([f] if fi else [])
        rows[i], rows[j] = (ci, ui), (cj, uj)
        return rows
    raise ValueError(op)


def giver_of(records, obj: str) -> Result:
    """The unique person who gave the agent the object; a record that could be another such
    "gave" (unknown action, object or partner) makes it ambiguous."""
    exact = [r for r in match(records, action="gave", obj=obj) if r["partner"] == SELF]
    maybe = [r for r in possible(records, action="gave", obj=obj)
             if (r["partner"] == SELF or unknown(r, "partner")) and r not in exact]
    trace = [("giver", obj, [r["id"] for r in exact + maybe])]
    if len(exact) != 1 or maybe:
        status = "no_observation" if not exact and not maybe else ("insufficient_evidence" if not exact else "ambiguous")
        return Result(None, status, [r["id"] for r in exact + maybe], trace)
    if not isinstance(exact[0]["actor"], str):
        return Result(None, "ambiguous", [exact[0]["id"]], trace)
    return Result(exact[0]["actor"], "ok", [exact[0]["id"]], trace)


def decide_env(records, decision: dict) -> dict:
    """Round 3.3 goals with unknown-aware operators: the object's latest placing (history
    operator "current"); the giver's latest appearance (memory.latest)."""
    parsed = parse_goal(decision["goal"])
    result = Result(None, "no_observation")
    if parsed:
        kind, obj = parsed
        if kind == "object":
            result = history_place(records, "object", obj, "current")
        else:
            g = giver_of(records, obj)
            result = g if g.status != "ok" else latest(records, g.value)
    return _act(result, decision)


def state_from_truth(events: list[dict]) -> dict:
    """The round 3.4 current-state baseline with perfect reading (from the true events)."""
    state = {"objects": {}, "people": {}}
    for c in events:
        if c["action"] in PLACING and c["object"]:
            state["objects"][c["object"]] = c["place"]
        for who in (c["actor"], c["partner"]):
            if who and who != SELF:
                state["people"][who] = c["place"]
    return state


# ----------------------------------------------------------------- tasks
def lm_rows(world: dict, encodings: dict, taus: dict, mode: str = "sum") -> list[tuple[dict, list]]:
    return [decide_record(encodings[e["text"]], taus, mode)[:2] for e in world["experiences"]]


def oracle_rows(world: dict) -> list[tuple[dict, list]]:
    return [({k: c[k] for k in FIELDS}, []) for c in world["truth_content"]]


def tasks(split: str, encodings: dict, taus: dict, mode: str = "sum") -> dict:
    """Intact decisions of the LM system and the reference per pair/world/goal, plus the
    intervention rows in the round 3.3 / 3.4 formats (for the original milestone rules)."""
    from .history_agent import state_decide
    intact, rows33, rows34 = [], [], []
    for p in split_pairs(split):
        kind, seed = p["kind"], p["seed"]
        for wname, w in p["worlds"].items():
            lm = lm_rows(w, encodings, taus, mode)
            ref = oracle_rows(w)
            if p["family"] == "env":
                goals = {"find": w["decision"]}
                truth = {"find": w["truth"]}
                dec = decide_env
            else:
                goals = w["decisions"]
                truth = w["truth"]
                dec = hist_decide
            for g, d in goals.items():
                a_lm, a_ref = dec(_records(lm), d), dec(_records(ref), d)
                intact.append({"kind": kind, "seed": seed, "world": wname, "goal": g, "truth": truth[g],
                               "lm_action": a_lm["action"]["go"], "lm_policy": a_lm["policy"],
                               "ref_action": a_ref["action"]["go"], "ref_policy": a_ref["policy"]})
            # interventions on the LM-written store (original rules, reported separately)
            if p["family"] == "env":
                specs, preds = env_plan(p, wname), env_predictions(p, wname)
                for name, spec in specs.items():
                    row = {"kind": kind, "seed": seed, "world": wname, "intervention": name}
                    if spec is None:
                        rows33.append(dict(row, available=False))
                        continue
                    d = decide_env(_records(variant(spec, lm)), w["decision"])
                    rows33.append(dict(row, available=True, predicted=preds[name], truth=w["truth"],
                                       action=d["action"]["go"], policy=d["policy"],
                                       success=d["action"]["go"] == w["truth"],
                                       as_predicted=d["action"]["go"] == preds[name]))
            else:
                specs, preds = hist_plan(p, wname), hist_predictions(p, wname)
                state = state_from_truth(w["truth_content"])
                for g, d in w["decisions"].items():
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
                        a = hist_decide(_records(variant(spec, lm)), d)
                        pred = preds[name][g]
                        rows34.append(dict(row, available=True, predicted=pred, action=a["action"]["go"],
                                           policy=a["policy"], success=a["action"]["go"] == w["truth"][g],
                                           as_predicted=a["action"]["go"] == pred))
    return {"intact": intact, "rows33": rows33, "rows34": rows34}


def cells(intact: list) -> dict:
    """Per world kind x goal: success (mean over pairs of the mean over the two worlds) for
    the LM system and the reference, pair success, confident-error rate, coverage, and the
    per-world success values."""
    out = {}
    for kind in KINDS35:
        for goal in sorted({r["goal"] for r in intact if r["kind"] == kind}):
            rows = [r for r in intact if r["kind"] == kind and r["goal"] == goal]
            by_pair = {}
            for r in rows:
                by_pair.setdefault(r["seed"], []).append(r)
            lm = statistics.mean(statistics.mean(x["lm_action"] == x["truth"] for x in v) for v in by_pair.values())
            ref = statistics.mean(statistics.mean(x["ref_action"] == x["truth"] for x in v) for v in by_pair.values())
            pair = statistics.mean(all(x["lm_action"] == x["truth"] for x in v) and len(v) == 2 for v in by_pair.values())
            mem = [r for r in rows if r["lm_policy"] == "memory"]
            cer = (sum(r["lm_action"] != r["truth"] for r in mem) / len(mem)) if mem else None
            worlds = [float(r["lm_action"] == r["truth"]) for r in rows]
            out[f"{kind}:{goal}"] = {"pairs": len(by_pair), "success_lm": lm, "success_ref": ref, "pair_success": pair,
                                     "confident_error_rate": cer, "coverage": len(mem) / len(rows),
                                     "world_success_min": min(worlds), "world_success_mean": statistics.mean(worlds)}
    return out


def encoder_qualified(q: dict, c: dict) -> list[tuple[str, bool]]:
    """The 3.5 technical criteria (an undefined rate never passes)."""
    checks = [("complete records with every slot correct >= 0.95",
               q["complete_records"] is not None and q["complete_records"] >= 0.95)]
    for key, v in c.items():
        checks.append((f"{key}: success LM {v['success_lm']:.3f} >= reference {v['success_ref']:.3f} - 0.02",
                       v["success_lm"] >= v["success_ref"] - 0.02))
        checks.append((f"{key}: pair success {v['pair_success']:.3f} >= 0.95", v["pair_success"] >= 0.95))
        cer = v["confident_error_rate"]
        checks.append((f"{key}: confident-error rate {'undefined' if cer is None else f'{cer:.3f}'} <= 0.05",
                       cer is not None and cer <= 0.05))
    return checks
