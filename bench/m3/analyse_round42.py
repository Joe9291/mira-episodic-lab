#!/usr/bin/env python3
"""Round 4.2 model-free analysis of recorded encodings (docs/ROUND_4_2.md sections 3, 5, 6).

  inspect   per slot: raw top-choice accuracy and margins of the encoded notes (any
            phase), with the wrong cases listed - development diagnostics
  evaluate  thresholds calibrated on the calibration encodings (or given), decisions on
            the evaluated split, arms G / E, both comparisons per question, causes, repair
            check, extraction measures, pass criteria

  fit       variant D (Astra's decision): label offsets fitted on the DISTINCT development
            notes of one model (analysis42.fit_offsets), written to a JSON file

usage: analyse_round42.py inspect ENCODE.json [ENCODE.json ...] [--priors | --prior-file=F]
       analyse_round42.py fit --enc DEV.json ... --out OFFSETS.json
       analyse_round42.py evaluate --split dev --cal CAL.json ... --enc ENC.json ...
                          --scoring offsets --offsets OFFSETS.json --out DIR
       (--scoring raw | prior | offsets; the official variant is offsets, raw and prior
       are reported next to it only)
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_round42_encode as ENC  # noqa: E402
from episodic_lab import analysis42 as A  # noqa: E402
from episodic_lab import cands42 as C  # noqa: E402
from episodic_lab import r40_analysis as A40  # noqa: E402
from episodic_lab import r40_world as W40  # noqa: E402
from episodic_lab import r42_world as W  # noqa: E402


def load(paths, priors=False, prior_files=(), offsets=None):
    """Encodings of the files (one model). priors=True: content-free correction with the
    priors recorded in each file (or from a prior-phase file of the same model); offsets:
    variant D, {slot: {label: b}} added to the label scores."""
    extra = {}
    for p in prior_files:
        d = json.loads(Path(p).read_text())
        extra[d["model"]] = d["priors"]
    enc, meta = {}, []
    for p in paths:
        d = json.loads(Path(p).read_text())
        if d.get("status") != "OK":
            raise SystemExit(f"{p}: status {d.get('status')} {d.get('error')}")
        pri = (d.get("priors") or extra[d["model"]]) if priors else None
        enc.update({k: A.apply_offsets(A.apply_priors(e, pri), offsets) for k, e in d["encodings"].items()})
        meta.append({k: d.get(k) for k in ("model", "split", "chunk", "chunks", "prompt_version", "candidate_version")})
    if len({m["model"] for m in meta}) != 1:
        raise SystemExit("files of more than one model")
    return enc, meta


def truths(split):
    """note key -> (truth, header | text) for every note of a split."""
    out = {}
    for p in W.iter_pairs(split):
        for inst in p["instances"]:
            for w in ("A", "B"):
                reps = inst[w]["reports"]
                by_id = {r["report_id"]: r for r in reps}
                for r, n in zip(reps, inst[w]["notes"]):
                    ctx = {"author": n["author"], "report_day": n["report_day"], "sources": p["sources"]}
                    out.setdefault(ENC.note_key(n["header"], n["text"], ctx),
                                   (C.truth(n, r, by_id), n["header"] + " | " + n["text"]))
    return out


def inspect(paths, priors=False, prior_files=()):
    enc, meta = load(paths, priors, prior_files)
    split = meta[0]["split"]
    tr = truths(split)
    ok, n, errs, margins = collections.Counter(), collections.Counter(), [], collections.defaultdict(list)
    for k, e in enc.items():
        t, txt = tr[k]
        v, m, _ = C.ranking([tuple(x) for x in e["type"]])
        n["type"] += 1
        ok["type"] += v == t["type"]
        margins["type"].append((m, v == t["type"]))
        if v != t["type"]:
            errs.append(("type", v, t["type"], txt))
        for slot in C.used_slots(t["type"], t):
            if slot not in e:
                continue
            v, m, _ = C.ranking([tuple(x) for x in e[slot] if C.allowed_surface(slot, x[0], t["type"])])
            n[slot] += 1
            ok[slot] += v == t[slot]
            margins[slot].append((m, v == t[slot]))
            if v != t[slot]:
                errs.append((slot, v, t[slot], txt))
    print(meta[0]["model"], meta[0]["prompt_version"], meta[0]["candidate_version"], "notes", len(enc),
          "label priors applied" if priors else "raw scores")
    for s in n:
        wrong_m = sorted(m for m, good in margins[s] if not good and m is not None)
        print(f"  {s:11s} {ok[s]}/{n[s]}  largest wrong margin {wrong_m[-1] if wrong_m else '-'}")
    for e in errs:
        print("   ", e)


def notes_of_world(pair, inst, world):
    out = []
    for n in inst[world]["notes"]:
        ctx = {"author": n["author"], "report_day": n["report_day"], "sources": pair["sources"]}
        out.append({"note_id": n["note_id"], "author": n["author"], "report_day": n["report_day"],
                    "key": ENC.note_key(n["header"], n["text"], ctx)})
    return out


def evaluate(split, enc, taus):
    rows, notes_out, violations = [], {}, []
    for pair in W.iter_pairs(split):
        for inst in pair["instances"]:
            for world in ("A", "B"):
                gold = inst[world]["reports"]
                by_id = {r["report_id"]: r for r in gold}
                notes = notes_of_world(pair, inst, world)
                truth = {n["note_id"]: C.truth(gn, r, by_id) for n, gn, r in zip(notes, inst[world]["notes"], gold)}
                decisions = {n["note_id"]: A.decide_note(enc[n["key"]], taus) for n in notes}
                stored, log = A.collect(notes, decisions, pair["ranks"])
                for bad in A.collector_errors(notes, decisions, stored, pair["ranks"]):
                    violations.append(f"collector {pair['pair']} d{inst['delay']} {world} {bad}")
                status = A.note_status(gold, stored)
                for n, entry in zip(notes, log):
                    notes_out.setdefault(n["key"], {"status": status[n["note_id"]], "type_pred": entry["type"],
                                                    "type_true": truth[n["note_id"]]["type"], "reason": entry["reason"],
                                                    "fields_correct": A.fields_correct(decisions[n["note_id"]], truth[n["note_id"]])
                                                    if decisions[n["note_id"]]["status"] == "ok" else None})
                qs = inst[world]["questions"]
                m_e, r_e = A.answer_all(stored, qs)
                _, r_g = A.answer_all(gold, qs)
                cz = A.causes(gold, stored, notes, decisions, truth, pair["fact"], pair["anchor"])
                for q in qs:
                    e2e = A40.hit(q["op"], r_g[q["qid"]], m_e[q["qid"]])
                    row = {"qid": q["qid"], "pair": pair["pair"], "family": pair["family"], "delay": inst["delay"],
                           "world": world, "op": q["op"], "memory_ok": m_e[q["qid"]] == r_e[q["qid"]],
                           "e2e": e2e, "gold": r_g[q["qid"]], "E": m_e[q["qid"]]}
                    if not e2e:
                        fixed = A.repair(gold, stored, set(cz["repair_scope"]), pair["fact"], pair["anchor"])
                        audit = W40.audit_world(fixed, pair["ranks"], pair["anchor"], pair["fact"], False)
                        rep_ans = A.answer_all(fixed, [q])[0][q["qid"]]
                        repaired = (not audit) and A40.hit(q["op"], r_g[q["qid"]], rep_ans)
                        minimal = list(cz["repair_scope"])
                        if repaired:                    # greedy reduction (Astra's idea): report only
                            for rid in list(minimal):
                                trial = [x for x in minimal if x != rid]
                                fx = A.repair(gold, stored, set(trial), pair["fact"], pair["anchor"])
                                if not W40.audit_world(fx, pair["ranks"], pair["anchor"], pair["fact"], False) and \
                                        A40.hit(q["op"], r_g[q["qid"]], A.answer_all(fx, [q])[0][q["qid"]]):
                                    minimal = trial
                        row.update(causes={k: cz[k] for k in ("direct", "follow_up", "injected")},
                                   repaired=repaired, repair_set=cz["repair_scope"], repair_set_greedy=minimal,
                                   repair_audit=audit)
                    rows.append(row)
    A.mark_critical(rows)
    return rows, notes_out, violations


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - r) / d, 4), round((c + r) / d, 4)]


def fit(paths, out_path):
    enc, meta = load(paths)
    if meta[0]["split"] != "dev":
        raise SystemExit("offsets are fitted on the development split only")
    tr = truths("dev")
    notes = [{"key": k, "truth": tr[k][0]} for k in sorted(enc)]
    if len(notes) != len(tr):
        raise SystemExit(f"development encodings incomplete: {len(notes)} of {len(tr)} distinct notes")
    res = {"model": meta[0]["model"], "prompt_version": meta[0]["prompt_version"],
           "candidate_version": meta[0]["candidate_version"], "notes": len(notes), "slots": {}}
    for slot in A.LABEL_SLOTS:
        labels = [s for s, _ in C.candidates(slot, "", {"author": "self", "report_day": 0, "sources": []})]
        res["slots"][slot] = A.fit_offsets(A.offset_rows(notes, enc, slot), labels)
    res["offsets"] = {s: r["offsets"] for s, r in res["slots"].items()}
    Path(out_path).write_text(json.dumps(res, indent=1, sort_keys=True))
    print(json.dumps({s: {k: r[k] for k in ("offsets", "right_raw", "right", "n", "at_grid_edge")}
                      for s, r in res["slots"].items()}, indent=1))


def label_top1(notes, enc_raw, enc_cor):
    """Per label slot: right top-1 raw / corrected over the notes whose TRUE type uses the
    slot; for change also per true class (distinct notes)."""
    out = {}
    for slot in A.LABEL_SLOTS:
        r = {"n": 0, "raw": 0, "corrected": 0}
        for n in notes:
            t = n["truth"]
            if slot != "type" and slot not in C.used_slots(t["type"], t):
                continue
            r["n"] += 1
            r["raw"] += C.ranking([tuple(x) for x in enc_raw[n["key"]][slot]])[0] == t[slot]
            ok = C.ranking([tuple(x) for x in enc_cor[n["key"]][slot]])[0] == t[slot]
            r["corrected"] += ok
            if slot == "change":
                c = r.setdefault("per_class", {}).setdefault(t["change"], {"n": 0, "corrected": 0})
                c["n"] += 1
                c["corrected"] += ok
        out[slot] = r
    return out


def occurrences(split):
    """Distinct notes and occurrences per correction change class (Astra: report both)."""
    import collections
    dist, occ = {}, collections.Counter()
    for p in W.iter_pairs(split):
        for inst in p["instances"]:
            for w in ("A", "B"):
                reps = inst[w]["reports"]
                by_id = {r["report_id"]: r for r in reps}
                for r, n in zip(reps, inst[w]["notes"]):
                    t = C.truth(n, r, by_id)
                    if t["type"] == "correction":
                        ctx = {"author": n["author"], "report_day": n["report_day"], "sources": p["sources"]}
                        dist[ENC.note_key(n["header"], n["text"], ctx)] = t["change"]
                        occ[t["change"]] += 1
    return {c: {"distinct": sum(1 for v in dist.values() if v == c), "occurrences": occ[c]} for c in sorted(occ)}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "inspect":
        args = sys.argv[2:]
        pri = [a.split("=", 1)[1] for a in args if a.startswith("--prior-file=")]
        files = [a for a in args if not a.startswith("--")]
        inspect(files, "--priors" in args or bool(pri), pri)
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("fit", "evaluate"))
    ap.add_argument("--split")
    ap.add_argument("--cal", nargs="*", default=[])
    ap.add_argument("--taus")
    ap.add_argument("--enc", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scoring", choices=("raw", "prior", "offsets"), default="offsets")
    ap.add_argument("--offsets", help="variant D offsets file (analyse_round42.py fit)")
    a = ap.parse_args()
    if a.cmd == "fit":
        fit(a.enc, a.out)
        return 0
    offsets = None
    if a.scoring == "offsets":
        if not a.offsets:
            raise SystemExit("--scoring offsets needs --offsets")
        off = json.loads(Path(a.offsets).read_text())
        offsets = off["offsets"]
    priors = a.scoring == "prior"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {"scoring": a.scoring, "offsets": offsets}
    cal_meta = None
    if a.taus:
        taus = json.loads(Path(a.taus).read_text())
    else:
        cal_enc, cal_meta = load(a.cal, priors, offsets=offsets)
        cal_raw, _ = load(a.cal)
        tr = truths("cal")
        if len(cal_enc) != len(tr):
            raise SystemExit(f"calibration encodings incomplete: {len(cal_enc)} of {len(tr)} distinct notes")
        cal_notes = [{"key": k, "truth": tr[k][0]} for k in sorted(cal_enc)]
        cases = A.calibration_cases(cal_notes, cal_enc)
        taus = {s: A.calibrate(c) for s, c in cases.items()}
        report["calibration"] = {"cases": {s: {"n": len(c), "right_top1": sum(ok for _, ok in c)} for s, c in cases.items()},
                                 "slots": A.slot_report(cal_notes, cal_enc, taus),
                                 "label_top1": label_top1(cal_notes, cal_raw, cal_enc),
                                 "change_classes": occurrences("cal")}
    enc, meta = load(a.enc, priors, offsets=offsets)
    enc_raw, _ = load(a.enc)
    if cal_meta and meta[0]["model"] != cal_meta[0]["model"]:
        raise SystemExit("calibration and evaluation files of different models")
    trs = truths(a.split)
    split_notes = [{"key": k, "truth": trs[k][0]} for k in sorted(enc)]
    rows, notes_out, violations = evaluate(a.split, enc, taus)
    by_cell = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        by_cell[f"{r['family']}|{r['delay']}"][0] += r["e2e"]
        by_cell[f"{r['family']}|{r['delay']}"][1] += 1
    st = collections.Counter(v["status"] for v in notes_out.values())
    res = dict(report, split=a.split, meta=meta, taus=taus, notes=dict(st), violations=violations[:50],
               slots=A.slot_report(split_notes, enc, taus), label_top1=label_top1(split_notes, enc_raw, enc),
               change_classes=occurrences(a.split),
               fully_correct_stored=sum(1 for v in notes_out.values() if v["status"] == "correct"),
               memory_ok=all(r["memory_ok"] for r in rows),
               unexplained=[r["qid"] for r in rows if not r["e2e"] and not r.get("repaired")],
               e2e={"right": sum(r["e2e"] for r in rows), "n": len(rows)},
               e2e_by_cell={k: {"right": v[0], "n": v[1], "rate": round(v[0] / v[1], 4)} for k, v in sorted(by_cell.items())},
               pairs_right=sum(1 for p in {r["pair"] for r in rows} if all(r["e2e"] for r in rows if r["pair"] == p)),
               pairs=len({r["pair"] for r in rows}))
    res["pairs_right_wilson"] = wilson(res["pairs_right"], res["pairs"])
    res["rule6"] = A.rule6(rows, W.FAMILIES, W.DELAYS, W.PAIRS[a.split],
                           {f: len(W40.QUESTION_TABLE[f]) for f in W.FAMILIES})
    (out / "evaluation.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    (out / "taus.json").write_text(json.dumps(taus, indent=1, sort_keys=True))
    with open(out / "rows.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    (out / "notes.json").write_text(json.dumps(notes_out, sort_keys=True))
    print(json.dumps({k: res[k] for k in ("scoring", "taus", "notes", "fully_correct_stored", "memory_ok", "e2e",
                                         "pairs_right", "pairs")}, indent=1))
    print("rule6", res["rule6"]["ok"], "unexplained", len(res["unexplained"]), "violations", len(violations))
    return 0


if __name__ == "__main__":
    sys.exit(main())
