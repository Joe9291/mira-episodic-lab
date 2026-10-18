"""Round 3.4 step 1 job: history goals with an identical final state (docs/ROUND_3_4.md).

Experience phase (this process): for each world the episodic store is written ONCE
(sealed) before any goal is handed to the agent; every intervention is derived from that encoded store
and written as a new sealed store; the state-only baseline reads the same experiences
and writes its state file (with its digest). Decision phase: every case (system x world
x intervention x goal) is decided by a new isolated interpreter that receives only one
store or state file, its seal and the decision text. Predictions come from the
independent reference (episodic_lab/history_reference.py). No model inference.
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

from episodic_lab.env import SELF  # noqa: E402
from episodic_lab.env_agent import derive_variant, materialize, write_store  # noqa: E402
from episodic_lab.history_agent import state_digest, state_only_encode  # noqa: E402
from episodic_lab.history_env import GOAL_NAMES, KINDS, generate_pair  # noqa: E402
from episodic_lab.history_reference import INTERVENTIONS, plan, predictions  # noqa: E402

SCHEMA = "episodic_lab.round34.v1"
DECIDE = ("import json, sys\nsys.path.insert(0, sys.argv[1])\n"
          "item = json.loads(sys.argv[2])\n"
          "if item['system'] == 'episodic':\n"
          "    from episodic_lab.memory import EpisodeStore\n"
          "    from episodic_lab.history_agent import decide\n"
          "    store = EpisodeStore(item['store'], expect=item['seal'])\n"
          "    out = decide(store.records, item['decision'])\n"
          "else:\n"
          "    from episodic_lab.history_agent import state_decide, state_digest\n"
          "    state = json.loads(open(item['store'], encoding='utf-8').read())\n"
          "    if state_digest(state) != item['seal']:\n"
          "        raise SystemExit('state file changed')\n"
          "    out = state_decide(state, item['decision'])\n"
          "print(json.dumps(out))\n")


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


def _seal_key(seal) -> str:
    return seal if isinstance(seal, str) else f"{seal['count']}:{seal['head']}"


def run(series: str, pairs_per_kind: int, workdir: Path) -> dict:
    rows, pair_hashes, probe, stored = [], {}, None, {}
    for kind in KINDS:
        for i in range(pairs_per_kind):
            seed = f"{series}-{i}"
            pair = generate_pair(seed, kind)
            pair_hashes[f"{kind}:{seed}"] = canonical_sha256(pair)
            for world in ("A", "B"):
                w = pair["worlds"][world]
                tag = f"{kind}_{i}_{world}"
                # 1. experience phase: everything is stored before any goal is handed over
                encoded = write_store(workdir / f"{tag}_encoded.jsonl", w["experiences"])
                state = state_only_encode(w["experiences"])
                state_path = workdir / f"{tag}_state.json"
                state_path.write_text(json.dumps(state, sort_keys=True))
                stored[f"{kind}:{seed}:{world}"] = {"records": len(encoded.records),
                                                    "state_entries": len(state["objects"]) + len(state["people"])}
                specs, preds = plan(pair, world), predictions(pair, world)
                stores = {}
                for name in INTERVENTIONS:
                    if specs[name] is None:
                        continue
                    contents = derive_variant(specs[name], encoded.records)
                    path = workdir / f"{tag}_{name}.jsonl"
                    stores[name] = (path, materialize(path, contents, [_source(c) for c in contents]).seal(),
                                    len(contents))
                # 2. decision phase: the goals are handed over now, one fresh process per case
                for goal in GOAL_NAMES:
                    decision = w["decisions"][goal]
                    truth = w["truth"][goal]
                    base = {"kind": kind, "seed": seed, "world": world, "goal": goal, "truth": truth}
                    item = {"system": "state_only", "store": str(state_path), "seal": state_digest(state),
                            "decision": decision}
                    d = fresh_decision(item, workdir)
                    if d is None:
                        raise RuntimeError(f"state-only decision failed: {tag} {goal}")
                    rows.append(dict(base, system="state_only", intervention="intact", available=True,
                                     seal=item["seal"], action=d["action"]["go"], policy=d["policy"],
                                     answer=d["answer"], result=d["result"], success=d["action"]["go"] == truth,
                                     predicted=None, as_predicted=None))
                    for name in INTERVENTIONS:
                        row = dict(base, system="episodic", intervention=name)
                        if name not in stores:
                            rows.append(dict(row, available=False))
                            continue
                        path, seal, n = stores[name]
                        item = {"system": "episodic", "store": str(path), "seal": seal, "decision": decision}
                        probe = probe or item
                        d = fresh_decision(item, workdir)
                        if d is None:
                            raise RuntimeError(f"decision process failed: {tag} {name} {goal}")
                        pred = preds[name][goal]
                        rows.append(dict(row, available=True, seal=_seal_key(seal), records=n,
                                         predicted=pred, action=d["action"]["go"], policy=d["policy"],
                                         answer=d["answer"], result=d["result"],
                                         success=d["action"]["go"] == truth, as_predicted=d["action"]["go"] == pred))
    lines = Path(probe["store"]).read_text().splitlines()
    (workdir / "cut.jsonl").write_text("\n".join(lines[:-1]) + "\n")
    changed = json.loads(lines[0])
    changed["place"] = changed["place"] + "x"
    (workdir / "changed.jsonl").write_text("\n".join([json.dumps(changed, sort_keys=True)] + lines[1:]) + "\n")
    refused = {name: fresh_decision(dict(probe, store=str(workdir / f"{name}.jsonl")), workdir) is None
               for name in ("cut", "changed")}
    return {"rows": rows, "pair_hashes": pair_hashes, "stored": stored, "refused": refused,
            "summary": summarise(rows)}


def summarise(rows: list) -> dict:
    """Per kind, system, intervention and goal; the intact action of the same world and
    goal is the reference for 'unchanged'."""
    intact = {(r["kind"], r["seed"], r["world"], r["goal"]): r["action"]
              for r in rows if r["system"] == "episodic" and r["intervention"] == "intact" and r["available"]}
    out = {}
    groups = {}
    for r in rows:
        groups.setdefault((r["kind"], r["system"], r["intervention"], r["goal"]), []).append(r)
    for (kind, system, name, goal), all_rows in sorted(groups.items()):
        sub = [r for r in all_rows if r["available"]]
        key = f"{kind}:{system}:{name}:{goal}"
        if not sub:
            out[key] = {"n": 0, "n_planned": len(all_rows)}
            continue
        by_pair = {}
        for r in sub:
            by_pair.setdefault(r["seed"], []).append(r["success"])
        v = {"n": len(sub), "n_planned": len(all_rows),
             "success": sum(r["success"] for r in sub) / len(sub),
             "pair_success": sum(len(x) == 2 and all(x) for x in by_pair.values()) / len(by_pair),
             "memory_branch": sum(r["policy"] == "memory" for r in sub) / len(sub)}
        if system == "episodic":
            informative = [r for r in sub if r["predicted"] != r["truth"]]
            v.update(as_predicted=sum(r["as_predicted"] for r in sub) / len(sub),
                     n_informative=len(informative),
                     as_predicted_informative=(sum(r["as_predicted"] for r in informative) / len(informative)
                                               if informative else None),
                     unchanged=sum(r["action"] == intact[(r["kind"], r["seed"], r["world"], r["goal"])]
                                   for r in sub) / len(sub))
        out[key] = v
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="hist-m34")
    ap.add_argument("--pairs", type=int, default=40)
    ap.add_argument("--request", default="config/round34.json")
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
