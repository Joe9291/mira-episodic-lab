"""Round 3.3 job: paired worlds, memory interventions, one fresh decision process per case.

Experience phase (this process): each world's experiences are encoded ONCE into a sealed
store; every intervention is derived from that encoded store and written as a new sealed
store. Decision phase: for EVERY case (world x intervention) a new isolated interpreter
receives only that case's store path, seal and decision text and returns the action with
its operator result (status, record ids, trace). Predictions come from the environment
side (episodic_lab/env_reference.py). No model inference is involved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from episodic_lab.env import KINDS, SELF, generate_pair  # noqa: E402
from episodic_lab.env_agent import derive_variant, materialize, write_store  # noqa: E402
from episodic_lab.env_reference import INTERVENTIONS, plan, predictions  # noqa: E402

SCHEMA = "episodic_lab.round33.v2"
DECIDE = ("import json, sys\nsys.path.insert(0, sys.argv[1])\n"
          "from episodic_lab.memory import EpisodeStore\nfrom episodic_lab.env_agent import decide\n"
          "item = json.loads(sys.argv[2])\n"
          "store = EpisodeStore(item['store'], expect=item['seal'])\n"
          "print(json.dumps(decide(store.records, item['decision'])))\n")


def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def fresh_decision(item: dict, workdir: Path):
    """One new isolated interpreter for one case; None if it refuses or fails."""
    script = workdir / "decide.py"
    if not script.exists():
        script.write_text(DECIDE)
    out = subprocess.run([sys.executable, "-I", str(script), str(ROOT), json.dumps(item)],
                         capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 else None


def _source(content: dict) -> dict:
    return {"kind": "own_action" if content["actor"] == SELF else "observed", "by": None}


def run(series: str, pairs_per_kind: int, workdir: Path) -> dict:
    rows, pair_hashes, probe = [], {}, None
    for kind in KINDS:
        for i in range(pairs_per_kind):
            seed = f"{series}-{i}"
            pair = generate_pair(seed, kind)
            pair_hashes[f"{kind}:{seed}"] = canonical_sha256(pair)
            for world in ("A", "B"):
                w = pair["worlds"][world]
                encoded = write_store(workdir / f"{kind}_{i}_{world}_encoded.jsonl", w["experiences"])
                specs, preds = plan(pair, world), predictions(pair, world)
                for name in INTERVENTIONS:
                    row = {"kind": kind, "seed": seed, "world": world, "intervention": name}
                    if specs[name] is None:
                        rows.append(dict(row, available=False))
                        continue
                    contents = derive_variant(specs[name], encoded.records)
                    path = workdir / f"{kind}_{i}_{world}_{name}.jsonl"
                    store = materialize(path, contents, [_source(c) for c in contents])
                    item = {"store": str(path), "seal": store.seal(), "decision": w["decision"]}
                    probe = probe or item
                    d = fresh_decision(item, workdir)
                    if d is None:
                        raise RuntimeError(f"decision process failed: {kind} {seed} {world} {name}")
                    rows.append(dict(row, available=True, predicted=preds[name], truth=w["truth"],
                                     records=len(contents), action=d["action"]["go"], policy=d["policy"],
                                     answer=d["answer"], result=d["result"],
                                     success=d["action"]["go"] == w["truth"],
                                     as_predicted=d["action"]["go"] == preds[name]))
    lines = Path(probe["store"]).read_text().splitlines()
    (workdir / "cut.jsonl").write_text("\n".join(lines[:-1]) + "\n")
    changed = json.loads(lines[0])
    changed["place"] = changed["place"] + "x"
    (workdir / "changed.jsonl").write_text("\n".join([json.dumps(changed, sort_keys=True)] + lines[1:]) + "\n")
    refused = {name: fresh_decision(dict(probe, store=str(workdir / f"{name}.jsonl")), workdir) is None
               for name in ("cut", "changed")}
    return {"rows": rows, "pair_hashes": pair_hashes, "refused": refused, "summary": summarise(rows)}


def summarise(rows: list) -> dict:
    out = {}
    for kind in KINDS:
        for name in INTERVENTIONS:
            all_rows = [r for r in rows if r["kind"] == kind and r["intervention"] == name]
            sub = [r for r in all_rows if r["available"]]
            if not sub:
                out[f"{kind}:{name}"] = {"n": 0, "n_planned": len(all_rows)}
                continue
            by_pair = {}
            for r in sub:
                by_pair.setdefault(r["seed"], []).append(r["success"])
            informative = [r for r in sub if r["predicted"] != r["truth"]]
            out[f"{kind}:{name}"] = {
                "n": len(sub), "n_planned": len(all_rows),
                "success": sum(r["success"] for r in sub) / len(sub),
                "pair_success": sum(len(v) == 2 and all(v) for v in by_pair.values()) / len(by_pair),
                "as_predicted": sum(r["as_predicted"] for r in sub) / len(sub),
                "n_informative": len(informative),
                "as_predicted_informative": (sum(r["as_predicted"] for r in informative) / len(informative)
                                             if informative else None),
                "memory_policy": sum(r["policy"] == "memory" for r in sub) / len(sub)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="env-m3")
    ap.add_argument("--pairs", type=int, default=40)
    ap.add_argument("--request", default="config/round33.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = {"schema": SCHEMA, "series": args.series, "pairs_per_kind": args.pairs, "status": "ERROR",
           "provenance": {"code_commit": os.environ.get("GITHUB_SHA", "local"),
                          "request_sha256": hashlib.sha256(Path(args.request).read_bytes()).hexdigest()}}
    with tempfile.TemporaryDirectory() as tmp:
        out.update(run(args.series, args.pairs, Path(tmp)))
    out["status"] = "OK"
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
