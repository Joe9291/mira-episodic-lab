#!/usr/bin/env python3
"""Round 4.1 holdout freeze (docs/ROUND_4_1.md section 5): generates the holdout, lets R
compute every expected answer (BEFORE, AFTER, counterfactual) and records the digests
plus the SHA-256 of every code file. M is NOT run. With --write the freeze is stored in
the request.

usage: freeze41.py config/round41.json [--write]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_round41 as R  # noqa: E402


def main():
    path = Path(sys.argv[1])
    phases = {k: R.R40.Phase() for k in ("R", "R_interventions")}
    R.tracemalloc.start()
    _, digests = R.pass_reference("holdout", phases)
    freeze = {"generator": R.W.GENERATOR_VERSION, "digests": digests, "code": R.code_hashes()}
    print(json.dumps(freeze, indent=1, sort_keys=True))
    if "--write" in sys.argv[2:]:
        req = json.loads(path.read_text())
        req["freeze"] = freeze
        path.write_text(json.dumps(req, indent=1) + "\n")
        print(f"freeze written to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
