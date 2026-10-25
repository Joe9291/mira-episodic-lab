#!/usr/bin/env python3
"""Round 4.3 holdout freeze (docs/ROUND_4_3.md): R only, H is NOT run. Generates the
holdout, records per family the digests of the worlds (reports, questions, cuts) and of
R's answers, the R-only audit (bound counts, id contract, K3 collisions, informative cases
of the lossy controls), the SHA-256 of the counts file and of every code file. With --write
the freeze is stored in the request; the holdout jobs refuse to start unless it matches.

usage: freeze43.py config/round43.json [--write]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_round43 as R  # noqa: E402


def main():
    path = Path(sys.argv[1])
    fams = set(R.W.FAMILIES)
    audit = R.audit("holdout", fams)
    counts_file = json.loads((R.ROOT / "config/round43_counts.json").read_text())
    ok = audit["counts"] == counts_file["splits"]["holdout"]["families"] and audit["id_contract_violations"] == 0 \
        and audit["k3_collisions"] == 0 and audit["cross_fact_targets"] == 0
    controls_ok = all(v["informative"] >= 30 and v["pairs"] >= 10 for v in audit["controls"].values())
    freeze = {"generator": R.W.GENERATOR_VERSION, "families": R.gold_digest("holdout", fams),
              "counts_sha256": hashlib.sha256((R.ROOT / "config/round43_counts.json").read_bytes()).hexdigest(),
              "audit": {k: audit[k] for k in ("id_contract_violations", "k3_collisions", "cross_fact_targets", "controls")},
              "audit_ok": ok, "controls_sufficient": controls_ok, "code": R.code_hashes()}
    freeze["freeze_id"] = hashlib.sha256(json.dumps(freeze, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    print(json.dumps({k: freeze[k] for k in ("freeze_id", "audit_ok", "controls_sufficient", "audit")}, indent=1))
    if not (ok and controls_ok):
        print("NOT FROZEN: the audit or the controls fail (design revision needed before the freeze)")
        return 1
    if "--write" in sys.argv[2:]:
        req = json.loads(path.read_text())
        req["freeze"] = freeze
        path.write_text(json.dumps(req, indent=1) + "\n")
        print(f"freeze written to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
