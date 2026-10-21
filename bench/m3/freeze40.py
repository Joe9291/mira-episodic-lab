#!/usr/bin/env python3
"""Round 4.0 holdout freeze (docs/ROUND_4_0.md section 7): generates the holdout, lets the
reference R compute every expected answer (original and counterfactual worlds) and
records the digests of worlds, questions, expected answers and interventions together
with the SHA-256 of every code file. M is NOT run. With --write the freeze is stored in
the request; the holdout run refuses to start unless the freeze matches.

usage: freeze40.py config/round40.json [--write]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_round40 as R  # noqa: E402


def main():
    path = Path(sys.argv[1])
    phases = {k: R.Phase() for k in ("R", "R_interventions")}
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
