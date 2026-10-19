"""Round 3.6 model-free audit (docs/ROUND_3_6.md, design v3, section 2).

  python3 bench/m3/audit36.py            development group (dev, cal, aud)
  python3 bench/m3/audit36.py --frozen   additionally the holdout (only AFTER the freeze)
  python3 bench/m3/audit36.py --reserve  additionally the reserve (only by the logged procedure)

Checks: roundtrip of every question to its wording; gold consistency; constants only in the
first split of their group; no text shared between groups; generator conditions per world
kind; candidate coverage of every gold target (must be 1.0); calibration counts on cal
(>= 300 intent-calibratable and >= 300 target-calibratable distinct texts); the rule
baseline per split.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from episodic_lab import analysis36 as A  # noqa: E402
from episodic_lab.baseline36 import parse_baseline, provenance  # noqa: E402
from episodic_lab.env36 import FIRST_OF_GROUP, GROUP, check_conditions, split_pairs, split_questions  # noqa: E402
from episodic_lab.parser36 import NONE, admissible, target_candidates  # noqa: E402
from episodic_lab.questions36 import is_constant, parse, wordings  # noqa: E402


def audit(splits: list[str]) -> dict:
    out = {"problems": [], "texts": {}, "coverage": {}, "baseline": {}, "counts": {}}
    if provenance():
        out["problems"].append(f"baseline_provenance:{provenance()}")
    groups = collections.defaultdict(set)
    for split in splits:
        for p in split_pairs(split):
            for msg in check_conditions(p):
                out["problems"].append(f"conditions:{split}:{p['seed']}:{msg}")
            for q in p["questions"]:
                fam, group, idx = q["wording"].split(":")
                w = wordings(fam, group)[int(idx)]
                if parse(q["text"], w) is None:
                    out["problems"].append(f"roundtrip:{split}:{q['text']}")
                if is_constant(w) and split not in FIRST_OF_GROUP:
                    out["problems"].append(f"constant:{split}:{q['text']}")
                groups[GROUP[split]].add(q["text"])
        gold = split_questions(split)   # raises on inconsistent gold
        out["texts"][split] = len(gold)
        need = [t for t, g in gold.items() if g["outcome"] != "REFUSE"]
        miss = [t for t in need if gold[t]["target"] not in {c for _, c in target_candidates(t)}]
        out["coverage"][split] = 1 - len(miss) / len(need) if need else None
        if miss:
            out["problems"].append(f"coverage:{split}:{miss[:3]}")
        base = {t: parse_baseline(t) for t in gold}
        out["baseline"][split] = {"right": sum(A.right(base[t], g) for t, g in gold.items()), "texts": len(gold)}
        if split == "cal":
            tc = [t for t in need if any(c != NONE and admissible(gold[t]["intent"], c)
                                         for _, c in target_candidates(t))]
            out["counts"] = {"intent_calibratable": len(gold), "target_calibratable": len(tc)}
            if len(gold) < 300 or len(tc) < 300:
                out["problems"].append(f"calibration_counts:{out['counts']}")
    names = sorted(groups)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if groups[a] & groups[b]:
                out["problems"].append(f"texts_shared:{a}:{b}:{len(groups[a] & groups[b])}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen", action="store_true")
    ap.add_argument("--reserve", action="store_true")
    args = ap.parse_args()
    splits = ["dev", "cal", "aud"] + (["ho"] if args.frozen or args.reserve else []) + (["res"] if args.reserve else [])
    print(json.dumps(audit(splits), indent=1))
