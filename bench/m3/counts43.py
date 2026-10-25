#!/usr/bin/env python3
"""Round 4.3: writes config/round43_counts.json - the model-free expected numbers per split
and family (episodic_lab/r43_world.family_counts) and the number of conformance checks
(Mode A: every check once; Mode T: every check at every cut 0 ... last report day + 1).

usage: counts43.py [OUT]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from episodic_lab import r43_world as W  # noqa: E402


def conformance_checks() -> int:
    d = json.loads((ROOT / "tests/fixtures/r40_conformance.json").read_text())
    n = 0
    for w in d["worlds"].values():
        last = max(row[1] for row in w["reports"])
        n += len(w["checks"]) * (1 + last + 2)
    return n


def main():
    out = {"schema": "episodic_lab.round43_counts.v2", "generator_version": W.GENERATOR_VERSION, "seeds": W.SEEDS,
           "conformance_checks": conformance_checks(), "splits": {}}
    for split in ("dev", "holdout"):
        fam = W.family_counts(split)
        keys = ("pairs", "instances") + W.COUNT_KEYS
        out["splits"][split] = {"families": fam, "total": {k: sum(f[k] for f in fam.values()) for k in keys}}
    text = json.dumps(out, indent=1, sort_keys=True) + "\n"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "config/round43_counts.json"
    path.write_text(text)
    print(hashlib.sha256(text.encode()).hexdigest())
    print(json.dumps({s: v["total"] for s, v in out["splits"].items()}, indent=1), out["conformance_checks"])


if __name__ == "__main__":
    main()
