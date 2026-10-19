"""Round 3.6 worlds and questions (docs/ROUND_3_6.md, design v3, sections 1-2).

Worlds: the round 3.5 generator with new seeds r36-{split}-{index}[-r{attempt}]. Every pair
gets its goal questions (1 for hidden / moved / giver, 3 for object / person) and three
controls (not-in-memory, ambiguous, unsupported); worlds A and B of a pair share the same
question texts and gold specifications. Wording group by split (dev, cal, aud: template +
development; ho: holdout; res: reserve), wordings and control families chosen by a hash of
the pair seed and the question role. Constant wordings (no placeholder) only in dev, ho,
res. Parser metrics and calibration count each distinct text once, in the first split
(ORDER) where it occurs (implementation note 1 in docs/ROUND_3_6.md); holdout and reserve
texts cannot occur in the development group (their wordings differ; the audit checks it).
"""
from __future__ import annotations

from .env35 import KINDS35, generate_pair35
from .questions36 import (AMBIGUOUS, OBJECT_TYPES, PERSON_TYPES, SETS, TYPES, UNSUPPORTED, UNSUPPORTED_FAMILIES,
                          ambiguous_intent, choose, is_constant, render, wording_id, wordings)
from .world import FIRST, LAST, OBJ_ADJ, OBJ_NOUN

PLACING = ("put", "hid", "left")
SELF = "You"
SIZES = {"dev": 10, "cal": 30, "aud": 5, "ho": 40, "res": 40}   # pairs per kind
ORDER = ("dev", "cal", "aud", "ho", "res")
GROUP = {"dev": "dev", "cal": "dev", "aud": "dev", "ho": "holdout", "res": "reserve"}
FIRST_OF_GROUP = {"dev", "ho", "res"}   # the only splits with constant wordings
GOAL_TYPE = {("hidden", "find"): "object_current", ("moved", "find"): "object_current",
             ("giver", "find"): "giver",
             ("object", "current"): "object_current", ("object", "first"): "object_first",
             ("object", "previous"): "object_previous",
             ("person", "current"): "person_current", ("person", "first"): "person_first",
             ("person", "previous"): "person_previous"}


def goals(pair: dict) -> list[str]:
    return ["find"] if pair["family"] == "env" else ["current", "first", "previous"]


def target_of(pair: dict) -> str:
    return pair["object"] if pair["family"] == "env" else pair["target"]


def _choose_wording(family: str, split: str, key: str) -> tuple[str, str, int]:
    """(template, wording id, index) from the split's group; constants only in FIRST_OF_GROUP."""
    opts = []
    for group in SETS[GROUP[split]]:
        for i, w in enumerate(wordings(family, group)):
            if is_constant(w) and split not in FIRST_OF_GROUP:
                continue
            opts.append((w, wording_id(family, group, i), i, group))
    w, wid, i, group = choose(opts, key)
    return w, wid, i


def _entities(pair: dict) -> dict:
    evs = [e for w in pair["worlds"].values() for e in w["truth_content"]]
    objects = sorted({e["object"] for e in evs if e["object"]})
    people = sorted({p for e in evs for p in (e["actor"], e["partner"]) if p and p != SELF})
    for w in pair["worlds"].values():
        people = sorted(set(people) | set(w.get("final_state", {}).get("people", {})))
    return {"objects": objects, "people": people}


def _absent(pair: dict, is_object: bool, key: str) -> str:
    ent = _entities(pair)
    if is_object:
        pool = [f"{a} {n}" for a in OBJ_ADJ for n in OBJ_NOUN if f"{a} {n}" not in ent["objects"]]
    else:
        used = set(ent["people"])
        pool = [f"{f} {l}" for f in FIRST for l in LAST if f"{f} {l}" not in used]
    return choose(pool, key)


def _stable_placing(pair: dict) -> dict:
    """A placing event identical in both worlds (for "Who put the {o} at {p}?")."""
    A, B = pair["worlds"]["A"]["truth_content"], pair["worlds"]["B"]["truth_content"]
    same = [a for a, b in zip(A, B) if a == b and a["action"] in PLACING and a["object"]]
    return same[0] if same else None


def questions(pair: dict, split: str) -> list[dict]:
    """The pair's questions: [{role, family, wording, text, gold: {intent, target, outcome}, goal}]."""
    seed, kind = pair["seed"], pair["kind"]
    out = []
    tgt = target_of(pair)
    for g in goals(pair):
        qtype = GOAL_TYPE[(kind, g)]
        w, wid, _ = _choose_wording(qtype, split, f"{seed}:{kind}:goal:{g}")
        fill = {"o": tgt} if qtype in OBJECT_TYPES else {"x": tgt}
        out.append({"role": f"goal:{g}", "family": qtype, "wording": wid, "text": render(w, fill),
                    "gold": {"intent": qtype, "target": tgt, "outcome": "OK"}, "goal": g})
    first_type = GOAL_TYPE[(kind, goals(pair)[0])]
    is_obj = first_type in OBJECT_TYPES
    # not-in-memory: same type as the first goal, an entity absent from both worlds
    absent = _absent(pair, is_obj, f"{seed}:{kind}:absent")
    w, wid, _ = _choose_wording(first_type, split, f"{seed}:{kind}:absent:wording")
    out.append({"role": "absent", "family": first_type, "wording": wid,
                "text": render(w, {"o": absent} if is_obj else {"x": absent}),
                "gold": {"intent": first_type, "target": absent, "outcome": "OK"}, "goal": None})
    # ambiguous: about the first goal's target
    fams = ["bare_noun", "pronoun"] if is_obj else ["first_name"]
    opts = []
    for fam in fams:
        for group in SETS[GROUP[split]]:
            for i, (wtext, _) in enumerate(AMBIGUOUS[fam].get(group, [])):
                if is_constant(wtext) and split not in FIRST_OF_GROUP:
                    continue
                opts.append((fam, group, i, wtext))
    fam, group, i, wtext = choose(opts, f"{seed}:{kind}:ambiguous")
    fill = {"noun": tgt.split()[1]} if is_obj else {"first": tgt.split()[0]}
    out.append({"role": "ambiguous", "family": fam, "wording": wording_id(fam, group, i),
                "text": render(wtext, fill),
                "gold": {"intent": ambiguous_intent(fam, group, i), "target": "none", "outcome": "CLARIFY"},
                "goal": None})
    # unsupported: a family filled with the pair's entities
    ent = _entities(pair)
    stable = _stable_placing(pair)
    opts = []
    for fam in sorted(UNSUPPORTED_FAMILIES):
        for group in SETS[GROUP[split]]:
            for i, wtext in enumerate(UNSUPPORTED_FAMILIES[fam].get(group, [])):
                if is_constant(wtext) and split not in FIRST_OF_GROUP:
                    continue
                if "{p}" in wtext and stable is None:
                    continue
                opts.append((fam, group, i, wtext))
    fam, group, i, wtext = choose(opts, f"{seed}:{kind}:unsupported")
    obj = stable["object"] if "{p}" in wtext else (tgt if is_obj else choose(ent["objects"], f"{seed}:uo"))
    person = pair["person"] if pair.get("person") else choose(ent["people"], f"{seed}:up")
    fill = {"o": obj, "x": person, "p": stable["place"] if stable else None}
    out.append({"role": "unsupported", "family": fam, "wording": wording_id(fam, group, i),
                "text": render(wtext, fill), "gold": {"intent": UNSUPPORTED, "target": None, "outcome": "REFUSE"},
                "goal": None})
    return out


def check_conditions(pair: dict) -> list[str]:
    """Design v3 section 1: the generator conditions per world kind (empty list = all hold)."""
    problems = []
    kind, tgt = pair["kind"], target_of(pair)
    for wn, w in pair["worlds"].items():
        T = w["truth_content"]
        if kind in ("object", "hidden", "moved"):
            pl = sorted([e for e in T if e["object"] == tgt and e["action"] in PLACING], key=lambda e: e["event_day"])
            other = [e for e in T if e["object"] == tgt and e["action"] not in PLACING]
            want = {"object": 3, "hidden": 1, "moved": 2}[kind]
            days = [e["event_day"] for e in pl]
            if len(pl) != want or other or len(set(days)) != len(days):
                problems.append(f"{kind}:{wn}:placings")
            if any(a["place"] == b["place"] for a, b in zip(pl, pl[1:])):
                problems.append(f"{kind}:{wn}:same_place")
        elif kind == "person":
            recs = [e for e in T if tgt in (e["actor"], e["partner"])]
            days = [e["event_day"] for e in recs]
            if len(recs) != 3 or any(e["action"] != "was" for e in recs) or len(set(days)) != 3:
                problems.append(f"person:{wn}:records")
        elif kind == "giver":
            ev = [e for e in T if e["object"] == tgt]
            if len(ev) != 1 or ev[0]["action"] != "gave" or ev[0]["partner"] != SELF:
                problems.append(f"giver:{wn}:gave")
            else:
                g = ev[0]["actor"]
                days = [e["event_day"] for e in T if g in (e["actor"], e["partner"])]
                if not days or days.count(max(days)) != 1:
                    problems.append(f"giver:{wn}:giver_latest")
    return problems


def is_constant_text(q: dict) -> bool:
    fam, group, idx = q["wording"].split(":")
    return is_constant(wordings(fam, group)[int(idx)])


_CACHE: dict = {}


def split_pairs(split: str) -> list[dict]:
    """The pairs of a split (with "questions"); a pair whose generator conditions fail is
    regenerated with the next attempt (seed suffix -r<attempt>)."""
    if split in _CACHE:
        return _CACHE[split]
    out = []
    for kind in KINDS35:
        for i in range(SIZES[split]):
            attempt = 0
            while True:
                p = generate_pair35(split, i, kind, attempt, prefix="r36")
                if not check_conditions(p):
                    break
                attempt += 1
            p["questions"] = questions(p, split)
            out.append(p)
    _CACHE[split] = out
    return out


def split_questions(split: str, new_only: bool = True) -> dict:
    """{distinct question text: gold} of a split - the unit of the parser metrics and of the
    calibration. With new_only (default), a text that already occurs in an earlier split
    (ORDER) is not counted again here: within the development group (dev, cal, aud) low-
    entropy texts ("Find the {noun}.", "Go to {first}.") repeat across splits, and a
    repetition must not raise the number of cases; the parse is still made and reused for
    the task metrics. Raises if one text has two different gold specifications."""
    out = {}
    earlier = set()
    if new_only:
        for e in ORDER[:ORDER.index(split)]:
            earlier |= set(split_questions(e, new_only=False))
    for p in split_pairs(split):
        for q in p["questions"]:
            if q["text"] in earlier:
                continue
            g = dict(q["gold"], family=q["family"], wording=q["wording"], role=q["role"].split(":")[0])
            if q["text"] in out and {k: out[q["text"]][k] for k in ("intent", "target", "outcome")} != \
                    {k: g[k] for k in ("intent", "target", "outcome")}:
                raise AssertionError(f"inconsistent gold for {q['text']!r}")
            out.setdefault(q["text"], dict(g, roles=[]))
            if g["role"] not in out[q["text"]]["roles"]:
                out[q["text"]]["roles"] = sorted(out[q["text"]]["roles"] + [g["role"]])
    return out
