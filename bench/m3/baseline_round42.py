#!/usr/bin/env python3
"""Round 4.2: an unchangeable record of one development configuration (Astra's Q3 of the
development result review): code commit, split and note hashes, prompt and candidate
versions with the source hashes, every raw encoding file (results-branch path + SHA-256),
model revisions and weight digests, the development offsets, tau, and the complete
evaluation outputs (copied, gzip).

usage: baseline_round42.py --name p6 --commit SHA --results-ref REF --runs RUN_DIR ...
                           --offsets F ... --eval NAME=DIR ... --out DIR
(RUN_DIR: a results-branch directory such as round42/run_39902326532_1; files are read
with git show from the given results ref)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_round42_encode as ENC  # noqa: E402
from episodic_lab import r42_world as W  # noqa: E402


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*args) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--results-ref", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--offsets", nargs="+", required=True)
    ap.add_argument("--eval", nargs="+", required=True, help="NAME=DIR")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    man = {"name": a.name, "code_commit": a.commit, "results_ref": git("rev-parse", a.results_ref).decode().strip(),
           "sources": {p: sha(git("show", f"{a.commit}:{p}")) for p in
                       ("episodic_lab/encoder42.py", "episodic_lab/cands42.py", "episodic_lab/analysis42.py",
                        "episodic_lab/r42_world.py", "episodic_lab/r42_wordings.py", "episodic_lab/models.py",
                        "bench/m3/run_round42_encode.py", "bench/m3/analyse_round42.py", "config/model_pins.json")},
           "splits": {}, "encodings": [], "models": {}, "offsets": {}, "evaluations": {}}
    for split in ("dev", "cal"):
        keys = [n["key"] for n in ENC.split_notes(split)]
        man["splits"][split] = {"distinct_notes": len(keys), "note_keys_sha256": sha("\n".join(keys).encode()),
                                "seed": W.SEEDS[split], "pairs_per_family": W.PAIRS[split]}
    for run in a.runs:
        names = git("ls-tree", "--name-only", f"{a.results_ref}:{run}").decode().split()
        for n in sorted(names):
            if not n.startswith("r42_encode_"):
                continue
            raw = git("show", f"{a.results_ref}:{run}/{n}")
            d = json.loads(raw)
            man["encodings"].append({"path": f"{run}/{n}", "sha256": sha(raw), "status": d["status"],
                                     "model": d["model"], "split": d["split"], "chunk": d["chunk"],
                                     "notes": d.get("notes"), "prompt_version": d["prompt_version"],
                                     "candidate_version": d["candidate_version"],
                                     "code_commit": d["provenance"]["code_commit"]})
            man["models"].setdefault(d["model"], set()).add(d["weights_sha256"])
    man["models"] = {m: sorted(v) for m, v in man["models"].items()}
    for f in a.offsets:
        b = Path(f).read_bytes()
        man["offsets"][Path(f).name] = {"sha256": sha(b), "offsets": json.loads(b)["offsets"]}
    for spec in a.eval:
        name, d = spec.split("=", 1)
        entry = {}
        for f in sorted(Path(d).iterdir()):
            b = f.read_bytes()
            (out / f"{name}__{f.name}.gz").write_bytes(gzip.compress(b, mtime=0))
            entry[f.name] = sha(b)
        ev = json.loads((Path(d) / "evaluation.json").read_text())
        entry["summary"] = {k: ev[k] for k in ("scoring", "taus", "notes", "e2e", "pairs_right", "pairs")}
        entry["summary"]["rule6_cells_ok"] = sum(c["ok"] for c in ev["rule6"]["cells"].values())
        man["evaluations"][name] = entry
    (out / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: man[k] for k in ("name", "code_commit", "results_ref", "splits", "models")}, indent=1))
    print("encodings", len(man["encodings"]), "evaluations", list(man["evaluations"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
