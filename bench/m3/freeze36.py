"""Round 3.6 freeze binding (docs/ROUND_3_6.md; same mechanism as round 3.5, bench/m3/freeze35.py): a frozen request
names the decoder version and the SHA-256 of every code file the round 3.5 jobs and the
collector run (the complete local import closure, models.py included). Checked three times:
before the plan of the workflow (no job starts on a mismatch), in every encode job before
the model is loaded, and by the collector (a mismatch is INCOMPLETE).

  python3 bench/m3/freeze36.py config/round36.json   exit 1 on a mismatch
  python3 bench/m3/freeze36.py --print               the current hashes (to write a freeze)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FROZEN_CODE = (
    "episodic_lab/__init__.py", "episodic_lab/questions36.py", "episodic_lab/env36.py", "episodic_lab/parser36.py",
    "episodic_lab/baseline36.py", "episodic_lab/analysis36.py", "episodic_lab/models.py",
    "episodic_lab/wordings35.py", "episodic_lab/env35.py", "episodic_lab/cands35.py", "episodic_lab/encoder35.py",
    "episodic_lab/analysis35.py",
    "episodic_lab/env.py", "episodic_lab/env_agent.py", "episodic_lab/env_reference.py",
    "episodic_lab/history_agent.py", "episodic_lab/history_env.py", "episodic_lab/history_reference.py",
    "episodic_lab/memory.py", "episodic_lab/questions.py", "episodic_lab/rng.py", "episodic_lab/symbolic.py",
    "episodic_lab/world.py",
    "bench/m3/freeze36.py", "bench/m3/run_round36.py", "bench/m3/collect_round36.py",
    "bench/m3/run_round33.py", "bench/m3/collect_round33.py", "bench/m3/run_round34.py",
    "bench/m3/collect_round34.py",
)


def code_hashes(root: Path = ROOT) -> dict:
    return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in FROZEN_CODE}


def decoder_version(root: Path = ROOT) -> str | None:
    m = re.search(r'^DECODER_VERSION = "([^"]+)"', (root / "episodic_lab/parser36.py").read_text(), re.M)
    return m.group(1) if m else None


def check(frozen: dict | None, root: Path = ROOT) -> list[str]:
    """Problems of a frozen request against the code (empty: bound and matching; no freeze: no check)."""
    if frozen is None:
        return []
    problems = []
    if frozen.get("decoder_version") != decoder_version(root):
        problems.append(f"decoder_version:{frozen.get('decoder_version')}:{decoder_version(root)}")
    want, have = frozen.get("code_sha256") or {}, code_hashes(root)
    bad = [p for p in FROZEN_CODE if want.get(p) != have[p]] + sorted(set(want) - set(have))
    if bad:
        problems.append("code_sha256:" + ",".join(bad))
    return problems


def main(argv: list[str]) -> int:
    if argv == ["--print"]:
        print(json.dumps({"decoder_version": decoder_version(), "code_sha256": code_hashes()}, indent=1))
        return 0
    req = json.loads(Path(argv[0]).read_text())
    if req.get("enabled") is not True:   # a disabled request starts no job (a finished freeze may be outdated)
        print("freeze check: request not enabled, nothing to check")
        return 0
    problems = check(req.get("frozen"))
    for p in problems:
        print(f"FROZEN MISMATCH {p}")
    print("freeze check:", "FAILED" if problems else ("OK" if req.get("frozen") else "no frozen configuration"))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
