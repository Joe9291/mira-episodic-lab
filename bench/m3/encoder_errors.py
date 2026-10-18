"""Error breakdown of the round 3.2 LM slot encoder (Astra's request after run 2).

Reads the stored world reports of a round 3.2 run and classifies every slot of every
encoded record against the template truth. Development analysis on data already used:
it informs the design of the next encoder; it is not a qualification.

Categories (per slot):
  correct            stored value equals the truth
  case_only          the reply equals the truth up to letter case (normalisable, no loss)
  base_form          action given in the base form of the true verb (normalisable, no loss)
  noun_only          object given without its adjective (information loss; reported with
                     whether the noun alone is unique among the world's objects)
  weekday            day answered with a weekday name (temporal information missing)
  wrong_number       day answered with another number
  missing            "none"/empty (for the partner: "none" although there is a partner)
  unknown            the slot was declared invalid/unknown by the encoder; never counted
                     as correct, even where the true value is "no partner" (Astra, v1 review)
  partner_norm_ok    the declared normalisation was actually applied (the valid reply for
                     the second person equals the first person) and the truth has no
                     partner: it helped
  partner_norm_bad   the normalisation was applied although the truth has a partner: it
                     hid a role error
  other              any other wrong value
The partner categories partner_norm_ok + partner_norm_bad together equal the number of
applications of the normalisation reported by the round 3.2 collector.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from episodic_lab.cells import INVALID, SLOT_QUESTIONS, _clean  # noqa: E402
from episodic_lab.symbolic import PAST  # noqa: E402

WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
LOSSLESS = ("case_only", "base_form", "partner_norm_ok")


def normalisation_applied(raw: dict) -> bool:
    """Exactly the round 3.2 collector's count: a valid second-person reply that equals
    the (cleaned) first-person reply."""
    partner = _clean(raw["partner"], "person")
    return partner not in (None, INVALID) and partner == _clean(raw["actor"], "person")


def classify(slot: str, raw: str, truth, stored, world_objects: set, actor_raw: str = "",
             invalid=(), applied: bool = False) -> tuple[str, str]:
    """(status, reason). status: correct / unknown (declared invalid by the encoder, never
    correct) / wrong. reason: why the stored value differs from the truth (see module doc),
    computed from the raw reply, also for declared unknowns."""
    kind = SLOT_QUESTIONS[slot][1]
    status = "unknown" if slot in invalid else ("correct" if stored == truth else "wrong")
    if slot == "partner" and applied:
        return status, "partner_norm_ok" if truth is None else "partner_norm_bad"
    if stored == truth and status == "correct":
        return status, "correct"
    cleaned = _clean(raw, kind)
    text = raw.strip().split("\n", 1)[0].strip().strip(".").strip()
    if slot == "partner":
        return status, "missing" if cleaned is None else "other"
    if cleaned is None or (isinstance(cleaned, str) and not cleaned):
        return status, "missing"
    if slot == "event_day":
        if text.lower() in WEEKDAYS:
            return status, "weekday"
        return status, "wrong_number" if isinstance(cleaned, int) else "other"
    if isinstance(cleaned, str) and isinstance(truth, str):
        if cleaned == truth:
            return status, "correct"
        if cleaned.lower() == truth.lower():
            return status, "case_only"
        if slot == "action" and PAST.get(cleaned.lower()) == truth:
            return status, "base_form"
        if slot == "object" and " " in truth and cleaned.lower() == truth.split(" ", 1)[1]:
            return status, "noun_only"
    return status, "other"


def wording(text: str) -> str:
    """The sentence frame of an episode (names, numbers, objects and verbs masked)."""
    shape = re.sub(r"[A-Z][a-z]+ [A-Z][a-z]+", "N", text)
    shape = re.sub(r"\d+", "D", shape)
    shape = re.sub(r"the [a-z]+ [a-z]+", "the O", shape)
    return re.sub(r" (" + "|".join(PAST.values()) + r"|hidden) ", " V ", shape)


def analyse(paths: list[Path]) -> dict:
    counts = {s: collections.Counter() for s in SLOT_QUESTIONS}
    status_counts = {s: collections.Counter() for s in SLOT_QUESTIONS}
    unique_noun = collections.Counter()
    per_world, strict_world = {}, {}
    records = 0
    frames = collections.defaultdict(collections.Counter)
    for p in paths:
        data = json.loads(p.read_text())
        world_ok, world_strict = [], []
        for cond in data["conditions"].values():
            recs = cond["encoder"]["records"]
            objects = {r["truth"]["object"] for r in recs}
            nouns = collections.Counter(o.split(" ", 1)[1] for o in objects if o and " " in o)
            for r in recs:
                records += 1
                cats = {}
                for slot in SLOT_QUESTIONS:
                    st, c = classify(slot, r["raw"][slot], r["truth"][slot], r["lm"][slot], objects,
                                     r["raw"]["actor"], r["invalid"], normalisation_applied(r["raw"]))
                    counts[slot][c] += 1
                    status_counts[slot][st] += 1
                    cats[slot] = (st, c)
                    if c == "noun_only":
                        unique_noun["unique" if nouns[r["truth"]["object"].split(" ", 1)[1]] == 1 else "shared"] += 1
                ok = all(c in ("correct",) + LOSSLESS and not (sl == "partner" and st == "unknown")
                         for sl, (st, c) in cats.items())
                strict = all(st == "correct" for st, _ in cats.values())
                world_strict.append(strict)
                world_ok.append(ok)
                f = frames[wording(r["text"])]
                f["n"] += 1
                f["weekday"] += cats["event_day"][1] == "weekday"
                f["partner_norm_bad"] += cats["partner"][1] == "partner_norm_bad"
                f["noun_only"] += cats["object"][1] == "noun_only"
                f["all_ok_lossless"] += ok
        per_world[p.name] = sum(world_ok) / len(world_ok)
        strict_world[p.name] = sum(world_strict) / len(world_strict)
    return {"records": records, "slots": {s: dict(c) for s, c in counts.items()},
            "status": {s: dict(c) for s, c in status_counts.items()},
            "all_slots_strict_per_world": strict_world,
            "noun_only_uniqueness": dict(unique_noun),
            "by_wording": {k: dict(v) for k, v in sorted(frames.items(), key=lambda kv: -kv[1]["n"])},
            "all_slots_after_lossless_normalisation_per_world": per_world}


def report(result: dict) -> str:
    cats = ["correct", "case_only", "base_form", "partner_norm_ok", "noun_only", "weekday", "wrong_number",
            "missing", "partner_norm_bad", "other"]
    n = result["records"]
    lines = [f"Records: {n}", "", "Status per slot (unknown = declared invalid by the encoder; never correct):", "",
             "| slot | correct | unknown | wrong |", "|---|---|---|---|"]
    for slot, c in result["status"].items():
        lines.append(f"| {slot} | {c.get('correct', 0)} | {c.get('unknown', 0)} | {c.get('wrong', 0)} |")
    lines += ["", "Reason per slot (from the raw reply; also for declared unknowns):", "",
              "| slot | " + " | ".join(cats) + " |", "|" + "---|" * (len(cats) + 1)]
    for slot, c in result["slots"].items():
        lines.append(f"| {slot} | " + " | ".join(str(c.get(k, 0)) for k in cats) + " |")
    strict = sorted(result["all_slots_strict_per_world"].values())
    loss = sorted(result["all_slots_after_lossless_normalisation_per_world"].values())
    lines += ["", f"Object given without adjective: {result['noun_only_uniqueness']} "
              "(unique = only one object with that noun in the world's episodes)",
              "", f"Records with every slot correct as stored, per world: min {strict[0]:.3f}, "
              f"median {strict[len(strict) // 2]:.3f}, max {strict[-1]:.3f}",
              f"... after LOSSLESS normalisation only (case, base form, the partner normalisation where it "
              f"helped; a declared unknown partner never counts): min {loss[0]:.3f}, "
              f"median {loss[len(loss) // 2]:.3f}, max {loss[-1]:.3f}"]
    lines += ["", "| sentence frame | n | weekday | partner_norm_bad | noun_only | all slots ok (lossless) |",
              "|---|---|---|---|---|---|"]
    for frame, v in result["by_wording"].items():
        lines.append(f"| {frame} | {v['n']} | {v['weekday']} | {v['partner_norm_bad']} | {v['noun_only']} | "
                     f"{v['all_ok_lossless']} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    res = analyse(sorted(Path(sys.argv[1]).glob("r32_*.json")))
    print(report(res))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
