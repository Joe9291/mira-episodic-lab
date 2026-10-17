"""Round 3.1 diagnostic battery (docs/STRATEGY.md section 3).

Five reader sub-skills, each with short cases whose notes are given in the prompt (no
memory involved): which parts of an episodic memory can a small model carry itself, and
which must be done by explicit operators?

  S1 extract  - take one detail from a present episode (2 notes)
  S2 compare  - which of two dated events happened first (2 notes); content form (name
                the object of the earlier event) and letter form (A/B); every pair asked
                in both orders
  S3 binding  - full cue combination vs partial matches (3 notes in positive AND
                negative cases, every note matching a pair of cue details, so the number
                of notes never signals the answer)
  S4 link     - connect two episodes through a person (3 notes; without the link the
                answer is ambiguous)
  S5 source   - own observation vs someone's report vs a report that does not exist
                (2 notes, the same in all three question kinds)

Every case carries its gold answer by construction; tests re-derive it with an
independent rule-based solver. Candidates are the answer values the case allows (all
values of the asked type in the notes, one value not in the notes, and "none" where
abstention is a valid answer); the candidate channel scores them by model likelihood.
"""
from __future__ import annotations

import hashlib
import json

from .questions import BASE
from .rng import HashRng
from .world import FIRST, LAST, OBJ_ADJ, OBJ_NOUN, PLACE_KIND, PLACE_STEM

DIAG_SCHEMA = "episodic_lab.diagnostics.v1"
SKILLS = ("S1", "S2", "S3", "S4", "S5")
VERBS = ("repaired", "painted", "sold", "hid", "found", "measured", "cleaned", "carried")
TARGET = 0.95  # development target per sub-skill and channel (not confirmatory)


def _draw(rng: HashRng, n_people: int, n_places: int, n_objects: int, n_verbs: int) -> dict:
    """Distinct names; objects with distinct adjectives AND nouns, places with distinct
    stems AND kinds, people with distinct first AND last names (short forms unique)."""
    firsts, lasts = rng.sample(list(FIRST), n_people), rng.sample(list(LAST), n_people)
    stems, kinds = rng.sample(list(PLACE_STEM), n_places), rng.sample(list(PLACE_KIND), n_places)
    adjs, nouns = rng.sample(list(OBJ_ADJ), n_objects), rng.sample(list(OBJ_NOUN), n_objects)
    return {"people": [f"{f} {s}" for f, s in zip(firsts, lasts)],
            "places": [f"{s} {k}" for s, k in zip(stems, kinds)],
            "objects": [f"{a} {n}" for a, n in zip(adjs, nouns)],
            "verbs": rng.sample(list(VERBS), n_verbs)}


def sentence(day: int, person: str, verb: str, obj: str, place: str) -> str:
    return f"On day {day}, {person} {verb} the {obj} at {place}."


def _case(skill: str, kind: str, notes: list[str], question: str, answer_type: str,
          gold: str, candidates: list[str], **extra) -> dict:
    case = {"skill": skill, "kind": kind, "notes": notes, "question": question,
            "answer_type": answer_type, "gold": gold, "candidates": candidates, **extra}
    case["cid"] = "c" + hashlib.sha256(json.dumps(
        [skill, kind, notes, question], sort_keys=True).encode()).hexdigest()[:10]
    if gold not in candidates:
        raise AssertionError("gold must be a candidate")
    return case


def _s1(rng: HashRng, i: int) -> dict:
    v = _draw(rng, 3, 3, 3, 2)
    (p, q, _), (pl, pl2, unseen_pl), (o, o2, unseen_o) = v["people"], v["places"], v["objects"]
    d, d2 = rng.sample(list(range(1, 15)), 2)
    a, a2 = v["verbs"]
    notes = [sentence(d, p, a, o, pl), sentence(d2, q, a2, o2, pl2)]
    notes = rng.shuffled(notes)
    kind = ("place", "object", "person", "day")[i % 4]
    unseen_day = next(x for x in range(1, 20) if x not in (d, d2))
    if kind == "place":
        return _case("S1", kind, notes, f"Where did {p} {BASE[a]} the {o}?", "place", pl,
                     [pl, pl2, unseen_pl, "none"])
    if kind == "object":
        return _case("S1", kind, notes, f"What did {p} {BASE[a]} at {pl}?", "object", o,
                     [o, o2, unseen_o, "none"])
    if kind == "person":
        return _case("S1", kind, notes, f"Who {a} the {o} at {pl}?", "person", p,
                     [p, q, v["people"][2], "none"])
    return _case("S1", kind, notes, f"On which day did {p} {BASE[a]} the {o} at {pl}?", "day",
                 f"Day {d}", [f"Day {d}", f"Day {d2}", f"Day {unseen_day}", "none"])


def _s2_pair(rng: HashRng, i: int) -> list[dict]:
    v = _draw(rng, 2, 2, 2, 2)
    (p, q), (pl, pl2), (o, o2) = v["people"], v["places"], v["objects"]
    a, a2 = v["verbs"]
    d_early, d_late = sorted(rng.sample(list(range(1, 15)), 2))
    early, late = (d_early, p, a, o, pl), (d_late, q, a2, o2, pl2)
    told = [early, late] if i % 2 == 0 else [late, early]  # half aligned, half inverted
    notes = [sentence(*e) for e in told]
    pair = f"s2-{i}"
    cases = []
    for flip in (False, True):
        x, y = (early, late) if not flip else (late, early)
        cases.append(_case("S2", "content", notes,
                           f"Which object was handled first, the {x[3]} or the {y[3]}?",
                           "object", o, [x[3], y[3]], pair=pair, aligned=i % 2 == 0))
        ea, eb = f"{x[1]} {x[2]} the {x[3]} at {x[4]}.", f"{y[1]} {y[2]} the {y[3]} at {y[4]}."
        cases.append(_case("S2", "letter", notes,
                           f"Which happened first? (A) {ea} (B) {eb} Answer A or B.",
                           "choice", "A" if not flip else "B", ["A", "B"], pair=pair,
                           aligned=i % 2 == 0))
    return cases


def _s3(rng: HashRng, i: int) -> dict:
    v = _draw(rng, 3, 3, 4, 2)
    (p, p_other, p_third), (pl, pl_other, pl_third), objs = v["people"], v["places"], v["objects"]
    a, a_other = v["verbs"]
    days = rng.sample(list(range(1, 15)), 3)
    o1, o2, o3, unseen = objs
    positive = i % 2 == 0
    # cue = (person p, action a, place pl); asked: the object
    if positive:
        rows = [(days[0], p, a, o1, pl),          # full match (target)
                (days[1], p, a, o2, pl_other),    # person + action
                (days[2], p_other, a, o3, pl)]    # action + place
        gold = o1
    else:
        rows = [(days[0], p, a, o1, pl_other),    # person + action
                (days[1], p, a_other, o2, pl),    # person + place
                (days[2], p_other, a, o3, pl)]    # action + place
        gold = "none"
    notes = rng.shuffled([sentence(*r) for r in rows])
    return _case("S3", "positive" if positive else "lure", notes,
                 f"What did {p} {BASE[a]} at {pl}?", "object", gold, [o1, o2, o3, unseen, "none"])


def _s4(rng: HashRng, i: int) -> dict:
    v = _draw(rng, 2, 4, 2, 2)
    (p, q), (pl1, pl2, pl3, unseen), (o1, o2) = v["people"], v["places"], v["objects"]
    a1, a2 = v["verbs"]
    days = rng.sample(list(range(1, 15)), 3)
    rows = [(days[0], p, a1, o1, pl1),   # identifies the person
            (days[1], p, a2, o2, pl2),   # answer episode
            (days[2], q, a2, o2, pl3)]   # same action and object by someone else
    notes = rng.shuffled([sentence(*r) for r in rows])
    return _case("S4", "link", notes,
                 f"Where did the person who {a1} the {o1} {BASE[a2]} the {o2}?", "place", pl2,
                 [pl1, pl2, pl3, unseen, "none"])


def _s5(rng: HashRng, i: int) -> dict:
    v = _draw(rng, 3, 3, 1, 1)
    (p, teller, absent), (seen_pl, told_pl, unseen), (o,), (a,) = (
        v["people"], v["places"], v["objects"], v["verbs"])
    d = rng.below(14) + 1
    notes = rng.shuffled([f"You saw it yourself: {sentence(d, p, a, o, seen_pl)}",
                          f"{teller} told you: {sentence(d, p, a, o, told_pl)}"])
    kind = ("observed", "reported", "missing")[i % 3]
    cands = [seen_pl, told_pl, unseen, "none"]
    if kind == "observed":
        return _case("S5", kind, notes, f"According to what you saw yourself, where did {p} "
                     f"{BASE[a]} the {o}?", "place", seen_pl, cands)
    if kind == "reported":
        return _case("S5", kind, notes, f"According to {teller}, where did {p} {BASE[a]} the {o}?",
                     "place", told_pl, cands)
    return _case("S5", kind, notes, f"According to {absent}, where did {p} {BASE[a]} the {o}?",
                 "place", "none", cands)


def build_battery(seed: str = "diag-m3", per_skill: int = 20) -> dict:
    cases = []
    for i in range(per_skill):
        cases.append(_s1(HashRng(f"diag:{seed}:S1:{i}"), i))
    for i in range(per_skill // 2):
        cases.extend(_s2_pair(HashRng(f"diag:{seed}:S2:{i}"), i))
    for i in range(per_skill):
        cases.append(_s3(HashRng(f"diag:{seed}:S3:{i}"), i))
    for i in range(per_skill):
        cases.append(_s4(HashRng(f"diag:{seed}:S4:{i}"), i))
    for i in range(per_skill + 1):  # 21 = 7 of each source kind
        cases.append(_s5(HashRng(f"diag:{seed}:S5:{i}"), i))
    if len({c["cid"] for c in cases}) != len(cases):
        raise AssertionError("duplicate case")
    return {"schema": DIAG_SCHEMA, "seed": seed, "target": TARGET, "cases": cases}


def candidate_names(case: dict) -> dict:
    """Name lists for the strict answer grammar (score.parse) of the free-text channel."""
    names = [c for c in case["candidates"] if c != "none"]
    return {"person": names, "place": names, "object": names}


def summarise(rows: list[dict]) -> dict:
    """Per skill and channel: accuracy; S2 also pair scores per form; S3 and S5 per kind.
    Channels are those present in every row ("cand" is absent in the reasoning modes)."""
    out = {}
    channels = [ch for ch in ("free", "cand") if rows and all(ch in r for r in rows)]
    for skill in SKILLS:
        sub = [r for r in rows if r["skill"] == skill]
        if not sub:
            continue
        entry = {"n": len(sub)}
        for ch in channels:
            entry[ch] = sum(r[ch]["correct"] for r in sub) / len(sub)
            kinds = {}
            for kind in sorted({r["kind"] for r in sub}):
                ks = [r for r in sub if r["kind"] == kind]
                kinds[kind] = sum(r[ch]["correct"] for r in ks) / len(ks)
            entry[f"{ch}_by_kind"] = kinds
            if skill == "S2":
                pairs = {}
                for r in sub:
                    pairs.setdefault((r["kind"], r["pair"]), []).append(r[ch]["correct"])
                entry[f"{ch}_pairs"] = {
                    kind: sum(all(v) for (k, _), v in pairs.items() if k == kind)
                    / sum(1 for (k, _) in pairs if k == kind)
                    for kind in ("content", "letter")}
        out[skill] = entry
    return out
