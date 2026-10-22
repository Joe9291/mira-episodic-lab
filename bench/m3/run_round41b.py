#!/usr/bin/env python3
"""Round 4.1b continued-instance check (docs/ROUND_4_1b.md), dev worlds of round 4.1.

Per world (pair side A / B, each delay) ONE LiveMemory instance on a file store:
  start with the reports of days <= d3 - 1
  Q1 current @ d3 - 1            Q2 current @ d3   (c not yet received)
  ingest c
  Q3 current @ d3 (same query time as Q2)          Q4 current @ d3 + 1
  ingest the irrelevant reports of the delay
  Q5 current @ now   Q6 history @ now   Q7 believed_at(d3 - 1) @ now
  Q8 why_changed(v = d3, k1 = d3 - 1, k2 = now) @ now
  restart: the store is reopened (seal checked) as a NEW LiveMemory; Q5 is asked again
  (warming the cache at now), one further own observation of day now arrives;
  Q9 current @ now (same query time), Q10 history @ now
Gold for every question: R on exactly the reports received so far. Afterwards a second
process reloads every final store (seal checked) and answers Q9-Q10 again.
DEV_OK requires every answer equal to R, the reload, and the expected counts: 400
instances, 400 answers per step, 200 Q2 / Q3 pairs in which c changes the gold.

usage: run_round41b.py --out DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_round40 as R40  # noqa: E402
from episodic_lab import r41_world as W  # noqa: E402
from episodic_lab.r40_memory import ReportStore  # noqa: E402
from episodic_lab.r40_reference import reference_answers  # noqa: E402
from episodic_lab.r41b_memory import LiveMemory  # noqa: E402

CODE_FILES = ("episodic_lab/r41b_memory.py", "bench/m3/run_round41b.py", "episodic_lab/r40_memory.py",
              "episodic_lab/r40_reference.py", "episodic_lab/r41_world.py", "tests/test_round41b.py")


def sequence(pair, inst, world, tmp):
    """Run one world through the live protocol; returns rows and the persistence item."""
    reports = inst[world]["reports"]
    d3, now = pair["d3"], inst["now"]
    fact = {"subject": pair["fact"][0], "attribute": pair["fact"][1]}
    crit = next(r for r in reports if r["report_id"] == inst["crit_id"])
    first = [r for r in reports if r["report_day"] <= d3 - 1]
    rest = [r for r in reports if r["report_day"] > d3]
    path = Path(tmp) / f"{pair['pair']}_{inst['delay']}_{world}.jsonl"
    store = ReportStore(path)
    store.extend(first)
    live = LiveMemory(store)
    received = list(first)
    rows = []
    current = {"m": live}

    def ask(name, q):
        q = dict(q, qid=f"{pair['pair']}-{world}-{inst['delay']}-{name}", **fact)
        gold = reference_answers(received, [q])[0][q["qid"]]
        got = current["m"].answer(q)
        rows.append({"qid": q["qid"], "family": pair["family"], "world": world, "delay": inst["delay"],
                     "step": name, "op": q["op"], "gold": gold, "M": got, "ok": got == gold})
        return q
    ask("Q1", {"op": "current", "now": d3 - 1})
    ask("Q2", {"op": "current", "now": d3})
    live.ingest([crit])
    received.append(crit)
    ask("Q3", {"op": "current", "now": d3})
    ask("Q4", {"op": "current", "now": d3 + 1})
    live.ingest(rest)
    received.extend(rest)
    ask("Q5", {"op": "current", "now": now})
    ask("Q6", {"op": "history", "now": now})
    ask("Q7", {"op": "believed_at", "t": d3 - 1, "now": now})
    ask("Q8", {"op": "why_changed", "v": d3, "k1": d3 - 1, "k2": now, "now": now})
    current["m"] = LiveMemory(ReportStore(path, expect=store.seal()))          # restart
    current["m"].answer(dict(fact, qid="warm", op="current", now=now))
    rid = f"r{len(received) + 1:05d}"
    extra = {"report_id": rid, "report_day": now, "source": "self", "rank": pair["ranks"]["self"],
             "origin": "o-" + rid, "subject": fact["subject"], "attribute": fact["attribute"], "kind": "assert",
             "value": "seen after restart", "valid_from": now, "target_report_id": None}
    current["m"].ingest([extra])
    received.append(extra)
    final = [ask("Q9", {"op": "current", "now": now}), ask("Q10", {"op": "history", "now": now})]
    expect = hashlib.sha256(R40.dumps([r["M"] for r in rows[-2:]])).hexdigest()
    return rows, {"path": str(path), "seal": current["m"].store.seal(), "questions": final, "expect": expect}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    rows, persist = [], []
    phases = {"persist_reload": R40.Phase()}
    with tempfile.TemporaryDirectory() as tmp:
        for pair in W.iter_pairs("dev"):
            for inst in pair["instances"]:
                for world in ("A", "B"):
                    r, p = sequence(pair, inst, world, tmp)
                    rows += r
                    persist.append(p)
        persist_res = R40.run_persistence(persist, tmp, phases)
    by_step = {s: {"ok": sum(r["ok"] for r in rows if r["step"] == s), "n": sum(1 for r in rows if r["step"] == s)}
               for s in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10")}
    changed_by_c = sum(1 for r2, r3 in zip([r for r in rows if r["step"] == "Q2"], [r for r in rows if r["step"] == "Q3"])
                       if r2["gold"] != r3["gold"])
    res = {"schema": "episodic_lab.round41b_result.v1", "split": "dev", "by_step": by_step,
           "all_ok": all(r["ok"] for r in rows), "persistence": persist_res,
           "same_time_cases_where_c_changes_the_gold": changed_by_c,
           "worlds": len(persist), "seconds": round(time.perf_counter() - t0, 1),
           "code": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in CODE_FILES}}
    res["expected_counts"] = (res["worlds"] == 400 and all(v["n"] == 400 for v in by_step.values())
                              and changed_by_c == 200 and persist_res.get("stores") == 400)
    res["verdict"] = "DEV_OK" if res["all_ok"] and persist_res["ok"] and res["expected_counts"] else "DEV_PROBLEMS"
    (out / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    with open(out / "rows.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    lines = [f"# Round 4.1b continued-instance check - dev", "", f"Verdict: **{res['verdict']}**", "",
             "| step | right / n |", "|---|---|"]
    lines += [f"| {s} | {v['ok']}/{v['n']} |" for s, v in by_step.items()]
    lines += ["", f"Worlds (one live instance each): {res['worlds']}. Same-time pairs Q2 / Q3 where c changes the gold: "
              f"{changed_by_c}. Expected counts met: {res['expected_counts']}. Reload in a second process: {persist_res['stores']} stores, ok = {persist_res['ok']}. "
              f"{res['seconds']} s."]
    (out / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    (out / "VERDICT").write_text(res["verdict"] + "\n")
    print(res["verdict"], json.dumps(by_step))
    return 0


if __name__ == "__main__":
    sys.exit(main())
