"""Round 3.5 model-free checks (docs/ROUND_3_5.md sections 1 and 3).

  python3 bench/m3/audit35.py            development, calibration and audit splits
  python3 bench/m3/audit35.py --frozen   additionally the holdout (only AFTER the freeze;
                                         a failure consumes the holdout, see the doc)
  python3 bench/m3/audit35.py --reserve  round 3.5b: additionally the reserve (only AFTER the
                                         3.5b freeze; model-free, no performance data)

Checks: disjoint episode texts across splits; meaning roundtrip (every sentence parses
back to its generating event with its template's exact inverse); pair invariance (the
worlds of a pair differ only in the critical episode); usage per frame (occurrences and
distinct texts; holdout >= 30 distinct texts per frame); candidate coverage (must be 1.0);
the two model-free extraction baselines (position rules, word-list rule for the action;
both built from the template and development wordings only).
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from episodic_lab.cands35 import NONE, SELF, SLOTS, coverage, truth_value  # noqa: E402
from episodic_lab.env35 import split_pairs  # noqa: E402
from episodic_lab.wordings35 import WORDINGS, parse  # noqa: E402

_NAME = re.compile(r"[A-Z][a-z]+ [A-Z][a-z]+")
# word lists from the template and the development wordings only
_ACTION_WORDS = [("hid", ("hid", "hide", "hidden")), ("left", ("left", "leave")),
                 ("put", ("put", "placed")), ("gave", ("gave", "handed", "got")),
                 ("went", ("went", "walked", "visited", "way")), ("was", ("saw", "met", "spotted", "was"))]


def baseline(text: str) -> dict:
    """Position and word-list rules (a surface-regularity control, no model)."""
    names = _NAME.findall(text)
    words = re.findall(r"[a-z]+", text.lower())
    action = next((label for label, ws in _ACTION_WORDS if any(w in words for w in ws)), "was")
    m = re.search(r"\bthe ([a-z]+ [a-z]+)", text)
    day = re.search(r"\d+", text)
    actor = names[0] if names and action not in ("went",) and not (action == "put" and len(names) < 2) else SELF
    return {"actor": actor, "partner": SELF if action == "gave" else NONE, "action": action,
            "object": m.group(1) if m else NONE, "place": names[-1] if names else NONE,
            "event_day": int(day.group()) if day else NONE}


def pairs(split: str):
    return split_pairs(split)


def audit(splits: list[str]) -> dict:
    out = {"problems": [], "usage": {}, "coverage": {}, "baseline": {}, "texts": {}}
    texts = {}
    for split in splits:
        usage = collections.defaultdict(lambda: [0, set()])
        cov = collections.Counter()
        base = collections.Counter()
        records = collections.Counter()
        seen = set()
        for p in pairs(split):
            A, B = p["worlds"]["A"], p["worlds"]["B"]
            diff = [j for j, (x, y) in enumerate(zip(A["experiences"], B["experiences"])) if x["text"] != y["text"]]
            if diff != [p["critical"]]:
                out["problems"].append(f"pair_invariance:{split}:{p['kind']}:{p['index']}")
            for w in (A, B):
                for e, c in zip(w["experiences"], w["truth_content"]):
                    etype, group, idx = e["frame"].split(":")
                    if parse(e["text"], etype, WORDINGS[etype][group][int(idx)]) != c:
                        out["problems"].append(f"roundtrip:{split}:{e['text']}")
                    usage[e["frame"]][0] += 1
                    usage[e["frame"]][1].add(e["text"])
                    if e["text"] in seen:
                        continue
                    seen.add(e["text"])
                    b = baseline(e["text"])
                    all_ok = True
                    for slot in SLOTS:
                        cov[slot] += coverage(slot, e["text"], c)
                        ok = b[slot] == truth_value(slot, c)
                        base[slot] += ok
                        all_ok &= ok
                    base["all_slots"] += all_ok
                    records[split] += 1
        n = records[split]
        texts[split] = seen
        out["usage"][split] = {f: [v[0], len(v[1])] for f, v in sorted(usage.items())}
        out["coverage"][split] = {s: cov[s] / n for s in SLOTS}
        out["baseline"][split] = {s: base[s] / n for s in list(SLOTS) + ["all_slots"]}
        out["texts"][split] = n
        if any(v < 1.0 for v in out["coverage"][split].values()):
            out["problems"].append(f"coverage:{split}")
        if split in ("ho", "res") and any(v[1] < 30 for v in out["usage"][split].values()):
            out["problems"].append(f"usage:{split}")
    names = list(texts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if texts[a] & texts[b]:
                out["problems"].append(f"texts_shared:{a}:{b}:{len(texts[a] & texts[b])}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen", action="store_true")
    ap.add_argument("--reserve", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    res = audit(["dev", "cal", "aud"] + (["ho"] if args.frozen or args.reserve else []) + (["res"] if args.reserve else []))
    print(json.dumps({k: res[k] for k in ("problems", "texts", "coverage", "baseline")}, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
