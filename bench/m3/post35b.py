"""Round 3.5b post-run analysis (Astra's non-blocking ideas; NOT part of the frozen code and
NOT a decision input - the qualification is the collector's result).

  python3 bench/m3/post35b.py RUN_DIR [--split res]

1. Paired change table of the four decodings d2, F1 only, F2 only, d3 on the same
   encodings and thresholds: per record and per world decision, which cases each variant
   fixes or breaks relative to d2.
2. Uncertainty over world pairs: Wilson 95% intervals of pair success per kind x goal
   (40 pairs per kind); the frozen pass criteria are unchanged.
3. Class findings as texts / wrong fields / unknown fields / affected records.
4. Decision consequences under d3: for every wrong or non-memory world decision, the
   operator status and the memories it used (note indices), then the wrong or unknown
   fields of the used notes, and separately the other wrong notes of the world (possible
   influences only).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from episodic_lab import analysis35 as A  # noqa: E402
from episodic_lab.cands35 import SLOTS, truth_value  # noqa: E402
from episodic_lab.encoder35 import decide_record  # noqa: E402
from episodic_lab.env35 import split_pairs  # noqa: E402
from episodic_lab.history_agent import decide as hist_decide  # noqa: E402

VARIANTS = {"d2": (False, False), "F1": (True, False), "F2": (False, True), "d3": (True, True)}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - h) / d), min(1.0, (c + h) / d))


def set_variant(base: dict, name: str):
    f1, f2 = VARIANTS[name]
    A.DECODING.clear()
    A.DECODING.update(base, object_two_tokens=f1, gave_receiver_self=f2)


def main(run_dir: str, split: str) -> int:
    run = Path(run_dir)
    req = json.loads((run / "request.json").read_text())
    base = dict(A.DECODING_OFF, **req.get("decoding", {}))
    taus = req["frozen"]["taus"]
    enc = {}
    for f in sorted(run.glob(f"r35_encode_*_{split}_*.json")):
        enc.update(json.loads(f.read_text())["encodings"])
    truth = A.truths(split)
    pairs = split_pairs(split)
    rec_ok, dec_ok = {}, {}
    for name in VARIANTS:
        set_variant(base, name)
        rec_ok[name] = {t: all(d["status"] != "unknown" and d["value"] == truth_value(s, c)
                               for s, d in decide_record(enc[t], taus)[2].items()) for t, c in truth.items()}
        dec_ok[name] = {(r["kind"], r["seed"], r["world"], r["goal"]): r["lm_action"] == r["truth"]
                        for r in A.tasks(split, enc, taus)["intact"]}
    L = [f"# Round 3.5b post-run analysis ({split}; not a decision input)", "", "## 1. Paired changes relative to d2", "",
         "| variant | records correct | fixed vs d2 | broken vs d2 | decisions right | fixed vs d2 | broken vs d2 |",
         "|---|---|---|---|---|---|---|"]
    for name in VARIANTS:
        rf = sum(rec_ok[name][t] and not rec_ok["d2"][t] for t in truth)
        rb = sum(not rec_ok[name][t] and rec_ok["d2"][t] for t in truth)
        df = sum(dec_ok[name][k] and not dec_ok["d2"][k] for k in dec_ok["d2"])
        db = sum(not dec_ok[name][k] and dec_ok["d2"][k] for k in dec_ok["d2"])
        L.append(f"| {name} | {sum(rec_ok[name].values())}/{len(truth)} | {rf} | {rb} | "
                 f"{sum(dec_ok[name].values())}/{len(dec_ok[name])} | {df} | {db} |")
    changed = [k for k in dec_ok["d2"] if dec_ok["d3"][k] != dec_ok["d2"][k]]
    L += ["", "World decisions changed between d2 and d3: " + ("; ".join(
        f"{k[0]} {k[1]} {k[2]} {k[3]} {'fixed' if dec_ok['d3'][k] else 'broken'}" for k in changed[:30]) or "none")]
    set_variant(base, "d3")
    T = A.tasks(split, enc, taus)["intact"]
    L += ["", "## 2. Pair success with Wilson 95% intervals (d3)", "", "| kind:goal | pairs | pair success | interval |",
          "|---|---|---|---|"]
    cells = {}
    for r in T:
        cells.setdefault(f"{r['kind']}:{r['goal']}", {}).setdefault(r["seed"], []).append(r["lm_action"] == r["truth"])
    for key, by in sorted(cells.items()):
        k = sum(all(v) and len(v) == 2 for v in by.values())
        lo, hi = wilson(k, len(by))
        L.append(f"| {key} | {len(by)} | {k / len(by):.3f} | [{lo:.3f}, {hi:.3f}] |")
    cd = A.class_diagnostics(split, enc, taus)
    L += ["", "## 3. Class findings (texts / wrong fields / unknown fields / affected records, d3)", ""]
    frames = {}
    for p in pairs:
        for w in p["worlds"].values():
            for e in w["experiences"]:
                frames[e["text"]] = e["frame"]
    affected = {}
    for t, c in truth.items():
        det = decide_record(enc[t], taus)[2]
        if any(d["status"] == "unknown" or d["value"] != truth_value(s, c) for s, d in det.items()):
            affected[f"frame:{frames[t]}"] = affected.get(f"frame:{frames[t]}", 0) + 1
    for key, v in cd.items():
        if v[1] or v[2]:
            L.append(f"- {key}: {v[0]} texts / {v[1]} wrong fields / {v[2]} unknown fields"
                     + (f" / {affected.get(key, 0)} affected records" if key.startswith("frame:") else ""))
    L += ["", "## 4. Decision consequences (d3)", ""]
    by = {(p["kind"], p["seed"]): p for p in pairs}
    for r in T:
        if r["lm_action"] == r["truth"] and r["lm_policy"] == "memory":
            continue
        p = by[(r["kind"], r["seed"])]
        w = p["worlds"][r["world"]]
        rows = A.lm_rows(w, enc, taus)
        recs = A._records(rows)
        d = (A.decide_env(recs, w["decision"]) if p["family"] == "env" else hist_decide(recs, w["decisions"][r["goal"]]))
        idx = {rec["id"]: i for i, rec in enumerate(recs)}
        used = sorted({idx[i] for i in d["result"]["ids"] if i in idx}
                      | {idx[i] for step in d["result"]["trace"] for i in step[-1] if i in idx})
        faults = {}
        for i, (e, c) in enumerate(zip(w["experiences"], w["truth_content"])):
            det = decide_record(enc[e["text"]], taus)[2]
            bad = [f"{s}={det[s]['value'] if det[s]['status'] != 'unknown' else '?'} (true {truth_value(s, c)})"
                   for s in SLOTS if det[s]["status"] == "unknown" or det[s]["value"] != truth_value(s, c)]
            if bad:
                faults[i] = f"note {i}: {', '.join(bad)} | {e['text']}"
        L.append(f"- {r['kind']} {r['seed']} {r['world']} {r['goal']}: operator status {d['result']['status']}, "
                 f"memories used {used}; policy {r['lm_policy']}; action {r['lm_action']} "
                 f"({'right' if r['lm_action'] == r['truth'] else 'wrong'}, true {r['truth']})")
        for i in used:
            if i in faults:
                L.append(f"    used and faulty: {faults[i]}")
        for i, txt in faults.items():
            if i not in used:
                L.append(f"    other faulty note (possible influence only): {txt}")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    raise SystemExit(main(args[0], args[args.index("--split") + 1] if "--split" in args else "res"))
