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
  partner_norm_ok    second person repeated the first and the truth has no partner
                     (the declared normalisation helped)
  partner_norm_bad   second person repeated the first although the truth has a partner
                     (the normalisation hid a role error)
  other              any other wrong value
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


def classify(slot: str, raw: str, truth, stored, world_objects: set, actor_raw: str = "") -> str:
    kind = SLOT_QUESTIONS[slot][1]
    if stored == truth:
        if slot == "partner" and truth is None:
            cleaned = _clean(raw, "person")
            return "partner_norm_ok" if cleaned not in (None, INVALID) else "correct"
        return "correct"
    cleaned = _clean(raw, kind)
    text = raw.strip().split("\n", 1)[0].strip().strip(".").strip()
    if slot == "partner":
        if truth is not None and stored is None and cleaned not in (None, INVALID) and cleaned == _clean(actor_raw, "person"):
            return "partner_norm_bad"
        return "missing" if cleaned is None else "other"
    if cleaned is None or (isinstance(cleaned, str) and not cleaned):
        return "missing"
    if slot == "event_day":
        if text.lower() in WEEKDAYS:
            return "weekday"
        return "wrong_number" if isinstance(cleaned, int) else "other"
    if isinstance(cleaned, str) and isinstance(truth, str):
        if cleaned.lower() == truth.lower():
            return "case_only"
        if slot == "action" and PAST.get(cleaned.lower()) == truth:
            return "base_form"
        if slot == "object" and " " in truth and cleaned.lower() == truth.split(" ", 1)[1]:
            return "noun_only"
    return "other"


def wording(text: str) -> str:
    """The sentence frame of an episode (names, numbers, objects and verbs masked)."""
    shape = re.sub(r"[A-Z][a-z]+ [A-Z][a-z]+", "N", text)
    shape = re.sub(r"\d+", "D", shape)
    shape = re.sub(r"the [a-z]+ [a-z]+", "the O", shape)
    return re.sub(r" (" + "|".join(PAST.values()) + r"|hidden) ", " V ", shape)


def analyse(paths: list[Path]) -> dict:
    counts = {s: collections.Counter() for s in SLOT_QUESTIONS}
    unique_noun = collections.Counter()
    per_world = {}
    records = 0
    frames = collections.defaultdict(collections.Counter)
    for p in paths:
        data = json.loads(p.read_text())
        world_ok = []
        for cond in data["conditions"].values():
            recs = cond["encoder"]["records"]
            objects = {r["truth"]["object"] for r in recs}
            nouns = collections.Counter(o.split(" ", 1)[1] for o in objects if o and " " in o)
            for r in recs:
                records += 1
                cats = {}
                for slot in SLOT_QUESTIONS:
                    c = classify(slot, r["raw"][slot], r["truth"][slot], r["lm"][slot], objects, r["raw"]["actor"])
                    counts[slot][c] += 1
                    cats[slot] = c
                    if c == "noun_only":
                        unique_noun["unique" if nouns[r["truth"]["object"].split(" ", 1)[1]] == 1 else "shared"] += 1
                ok = all(c in ("correct",) + LOSSLESS for c in cats.values())
                world_ok.append(ok)
                f = frames[wording(r["text"])]
                f["n"] += 1
                f["weekday"] += cats["event_day"] == "weekday"
                f["partner_norm_bad"] += cats["partner"] == "partner_norm_bad"
                f["noun_only"] += cats["object"] == "noun_only"
                f["all_ok_lossless"] += ok
        per_world[p.name] = sum(world_ok) / len(world_ok)
    return {"records": records, "slots": {s: dict(c) for s, c in counts.items()},
            "noun_only_uniqueness": dict(unique_noun),
            "by_wording": {k: dict(v) for k, v in sorted(frames.items(), key=lambda kv: -kv[1]["n"])},
            "all_slots_after_lossless_normalisation_per_world": per_world}


def report(result: dict) -> str:
    cats = ["correct", "case_only", "base_form", "partner_norm_ok", "noun_only", "weekday", "wrong_number",
            "missing", "partner_norm_bad", "other"]
    n = result["records"]
    lines = [f"Records: {n}", "", "| slot | " + " | ".join(cats) + " |", "|" + "---|" * (len(cats) + 1)]
    for slot, c in result["slots"].items():
        lines.append(f"| {slot} | " + " | ".join(str(c.get(k, 0)) for k in cats) + " |")
    pw = result["all_slots_after_lossless_normalisation_per_world"]
    vals = sorted(pw.values())
    lines += ["", f"Object given without adjective: {result['noun_only_uniqueness']} "
              "(unique = only one object with that noun in the world's episodes)",
              "", "Share of records with every slot correct after LOSSLESS normalisation only "
              f"(case, base form, helpful partner normalisation), per world: min {vals[0]:.3f}, "
              f"median {vals[len(vals) // 2]:.3f}, max {vals[-1]:.3f}"]
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
