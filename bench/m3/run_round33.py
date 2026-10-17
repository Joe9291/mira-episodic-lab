"""Round 3.3 job: paired worlds, memory interventions, decisions in a fresh process.

Experience phase (this process): every world's experiences - intact or intervened - are
written into an episodic store file with its seal. Decision phase: ONE fresh, isolated
interpreter receives only a manifest of (store path, seal, decision text) and returns the
actions; it never sees experiences, truths or predictions. The environment then scores
every action. No model inference is involved.
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

from episodic_lab.env import KINDS, generate_pair  # noqa: E402
from episodic_lab.env_agent import INTERVENTIONS, intervene, write_store  # noqa: E402

SCHEMA = "episodic_lab.round33.v1"
DECIDE = ("import json, sys\nsys.path.insert(0, sys.argv[1])\n"
          "from episodic_lab.memory import EpisodeStore\nfrom episodic_lab.env_agent import decide\n"
          "out = []\nfor item in json.loads(open(sys.argv[2]).read()):\n"
          "    store = EpisodeStore(item['store'], expect=item['seal'])\n"
          "    out.append(decide(store.records, item['decision']))\n"
          "print(json.dumps(out))\n")


def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def fresh_decisions(root: Path, manifest: list, workdir: Path) -> list | None:
    (workdir / "decide.py").write_text(DECIDE)
    (workdir / "manifest.json").write_text(json.dumps(manifest))
    out = subprocess.run([sys.executable, "-I", str(workdir / "decide.py"), str(root),
                          str(workdir / "manifest.json")], capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 else None


def run(series: str, pairs_per_kind: int, workdir: Path) -> dict:
    rows, manifest, pair_hashes = [], [], {}
    for kind in KINDS:
        for i in range(pairs_per_kind):
            seed = f"{series}-{i}"
            pair = generate_pair(seed, kind)
            pair_hashes[f"{kind}:{seed}"] = canonical_sha256(pair)
            for world in ("A", "B"):
                variants = intervene(pair, world)
                for name in INTERVENTIONS:
                    v = variants[name]
                    if v is None:
                        rows.append({"kind": kind, "seed": seed, "world": world, "intervention": name,
                                     "available": False})
                        continue
                    exps, content, predicted = v
                    path = workdir / f"{kind}_{i}_{world}_{name}.jsonl"
                    store = write_store(path, exps, None if name == "intact" else content)
                    manifest.append({"store": str(path), "seal": store.seal(),
                                     "decision": pair["worlds"][world]["decision"]})
                    rows.append({"kind": kind, "seed": seed, "world": world, "intervention": name,
                                 "available": True, "predicted": predicted,
                                 "truth": pair["worlds"][world]["truth"], "records": len(exps)})
    decisions = fresh_decisions(ROOT, manifest, workdir)
    if decisions is None or len(decisions) != len(manifest):
        raise RuntimeError("decision process failed")
    it = iter(decisions)
    for row in rows:
        if row["available"]:
            d = next(it)
            row.update(action=d["action"]["go"], policy=d["policy"], status=d["result"]["status"],
                       answer=d["answer"], success=d["action"]["go"] == row["truth"],
                       as_predicted=d["action"]["go"] == row["predicted"])
    # integrity of the restart: a cut-off and a changed store must be refused
    probe = manifest[0]
    lines = Path(probe["store"]).read_text().splitlines()
    (workdir / "cut.jsonl").write_text("\n".join(lines[:-1]) + "\n")
    changed = json.loads(lines[0])
    changed["place"] = changed["place"] + "x"
    (workdir / "changed.jsonl").write_text("\n".join([json.dumps(changed, sort_keys=True)] + lines[1:]) + "\n")
    refused = {name: fresh_decisions(ROOT, [dict(probe, store=str(workdir / f"{name}.jsonl"))], workdir) is None
               for name in ("cut", "changed")}
    return {"rows": rows, "pair_hashes": pair_hashes, "refused": refused, "summary": summarise(rows)}


def summarise(rows: list) -> dict:
    out = {}
    for kind in KINDS:
        for name in INTERVENTIONS:
            sub = [r for r in rows if r["kind"] == kind and r["intervention"] == name and r["available"]]
            if not sub:
                continue
            by_pair = {}
            for r in sub:
                by_pair.setdefault(r["seed"], []).append(r["success"])
            informative = [r for r in sub if r["predicted"] != r["truth"]]
            out[f"{kind}:{name}"] = {
                "n": len(sub), "success": sum(r["success"] for r in sub) / len(sub),
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
    out = {"schema": SCHEMA, "series": args.series, "pairs_per_kind": args.pairs,
           "provenance": {"code_commit": os.environ.get("GITHUB_SHA", "local"),
                          "request_sha256": hashlib.sha256(Path(args.request).read_bytes()).hexdigest()}}
    with tempfile.TemporaryDirectory() as tmp:
        out.update(run(args.series, args.pairs, Path(tmp)))
    out["status"] = "OK"
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
