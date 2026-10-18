"""Collector of round 3.5 (docs/ROUND_3_5.md). Nothing is taken on trust: every planned
encode report must be present, valid, from the run's code commit and the request; every
decision is re-derived from the recorded scores.

Phases (config/round35.json "phase"):
  timing  cost per text, model loading, extrapolation to every split, cache check
  encode  for the listed splits; with "cal": thresholds per slot and the holdout gate;
          with "ho": ENCODER_QUALIFIED and MILESTONE_ORIGINAL_RULES with the frozen
          configuration given in the request ("frozen": {"model", "taus"})
"""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import collect_round33  # noqa: E402
import collect_round34  # noqa: E402
import run_round33  # noqa: E402
import run_round34  # noqa: E402
import run_round35  # noqa: E402
from episodic_lab import analysis35 as A  # noqa: E402
from episodic_lab.cands35 import SLOTS  # noqa: E402
from episodic_lab.env35 import SIZES  # noqa: E402

JOB_HOURS = 5.5   # usable part of the 6-hour job limit


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def planned(req: dict) -> list[tuple[str, str, int]]:
    if req["phase"] in ("timing", "probe"):
        return [(m, "dev", 0) for m in req["models"]]
    return [(m, s, c) for m in req["models"] for s in req["splits"] for c in range(req["chunks"])]


def load(req: dict, request_path: str, pins_path: str, dest: Path, commit: str | None):
    """{(model, split): {text: encoding}}, the reports, and the problems."""
    problems, reports, enc = [], {}, {}
    rsha, psha = sha256_file(request_path), sha256_file(pins_path)
    for model, split, chunk in planned(req):
        name = f"r35_{req['phase']}_{model}_{split}_{chunk}.json"
        try:
            d = json.loads((dest / name).read_text())
        except Exception as exc:
            problems.append(f"missing:{name}:{type(exc).__name__}")
            continue
        prov = d.get("provenance") or {}
        if (d.get("schema"), d.get("status"), d.get("phase"), d.get("model"), d.get("split"), d.get("chunk")) != (
                run_round35.SCHEMA, "OK", req["phase"], model, split, chunk):
            problems.append(f"identity_or_status:{name}")
            continue
        if prov.get("request_sha256") != rsha or prov.get("pins_sha256") != psha:
            problems.append(f"provenance:{name}")
        if commit is not None and prov.get("code_commit") != commit:
            problems.append(f"provenance:commit:{name}")
        reports[name] = d
        enc.setdefault((model, split), {}).update(d["encodings"])
    if req["phase"] == "encode":
        for model in req["models"]:
            for split in req["splits"]:
                want = set(run_round35.split_texts(split))
                if set(enc.get((model, split), {})) != want:
                    problems.append(f"texts:{model}:{split}")
    return enc, reports, problems


def timing_summary(req: dict, reports: dict) -> list[str]:
    L = ["# Round 3.5 timing run", ""]
    sizes = {s: len(run_round35.split_texts(s)) for s in ("dev", "cal", "ho")}
    for d in reports.values():
        secs = sorted(d["seconds"].values())
        mean = statistics.mean(secs)
        L += [f"## {d['model']}", "",
              f"- texts timed: {len(secs)}; seconds per text: mean {mean:.2f}, median {secs[len(secs) // 2]:.2f}, "
              f"max {secs[-1]:.2f}; model loading {d['load_seconds']:.0f} s",
              f"- cache check ({d['cache_check']['texts']} texts, all slots): max |cached - uncached| "
              f"{d['cache_check']['max_abs_diff']:.2e}, same choices {d['cache_check']['same_choices']} -> "
              f"{'OK' if d['cache_check']['ok'] else 'FAILED'}"]
        for split, n in sizes.items():
            hours = n * mean / 3600
            chunks = max(1, int(hours / JOB_HOURS) + 1)
            L.append(f"- {split}: {n} distinct texts, about {hours:.1f} h of encoding -> at least {chunks} chunk(s) "
                     f"of < {JOB_HOURS} h (plus loading)")
        L.append("")
    return L


def probe_summary(req: dict, enc: dict) -> list[str]:
    """Development probe: quality with the best value (tau 0), per wording frame, examples."""
    from episodic_lab.cands35 import ranking, truth_value
    truth = A.truths("dev")
    frame = {e["text"]: e["frame"] for p in A.split_pairs("dev") for w in p["worlds"].values() for e in w["experiences"]}
    L = ["# Round 3.5 development probe", ""]
    for model in req["models"]:
        e = enc[(model, "dev")]
        q = A.quality(e, truth, {s: 0.0 for s in SLOTS})
        L += [f"## {model}: complete records {q['complete_records']:.3f} ({q['texts']} texts)", "",
              "| slot | correct | wrong |", "|---|---|---|"]
        L += [f"| {s} | {v['correct']} | {v['wrong'] + v['unknown']} |" for s, v in q["slots"].items()]
        L += ["", "By role: " + "; ".join(f"{k} {v['correct']}/{v['wrong'] + v['unknown']}" for k, v in sorted(q["roles"].items())), ""]
        per = {}
        for text, x in e.items():
            ok = all(ranking([tuple(y) for y in x[s]])[0] == truth_value(s, truth[text]) for s in SLOTS)
            per.setdefault(frame[text], [0, 0])
            per[frame[text]][0] += 1
            per[frame[text]][1] += ok
        L += ["By frame (texts/complete): " + "; ".join(f"{f} {n}/{k}" for f, (n, k) in sorted(per.items())), "",
              "Examples of wrong slots:", ""]
        shown = {}
        for text, x in sorted(e.items()):
            for s in SLOTS:
                v = ranking([tuple(y) for y in x[s]])[0]
                if v != truth_value(s, truth[text]) and shown.get(s, 0) < 4:
                    shown[s] = shown.get(s, 0) + 1
                    L.append(f"- {s}: \"{text}\" -> {v!r} (true {truth_value(s, truth[text])!r})")
        L.append("")
    return L


def encode_summary(req: dict, enc: dict) -> tuple[list[str], dict]:
    L, decisions = ["# Round 3.5 encode run", ""], {}
    truth = {s: A.truths(s) for s in req["splits"]}
    for model in req["models"]:
        L += [f"## {model}", ""]
        zero = {s: 0.0 for s in SLOTS}
        taus = None
        if "cal" in req["splits"]:
            cal = A.calibrate(enc[(model, "cal")], truth["cal"])
            taus = {s: cal[s]["tau"] for s in SLOTS}
            decisions[model] = {"taus": taus, "calibration": cal}
            L += ["Thresholds (calibration split): " + "; ".join(
                f"{s} tau={'none' if cal[s]['tau'] is None else round(cal[s]['tau'], 4)} acceptance "
                f"{cal[s]['acceptance']:.3f} precision {'-' if cal[s]['precision'] is None else round(cal[s]['precision'], 4)} "
                f"({cal[s]['accepted']}/{cal[s]['items']})" for s in SLOTS), ""]
        if req.get("frozen"):
            taus = req["frozen"]["taus"]
        for split in req["splits"]:
            for label, t in (("best value (tau 0)", zero),) + ((("thresholds", taus),) if taus else ()):
                q = A.quality(enc[(model, split)], truth[split], t)
                L += [f"### {split}, {label}: complete records {q['complete_records']:.3f} ({q['texts']} texts)", "",
                      "| slot | correct | unknown | wrong | single-value | accuracy where chosen |", "|---|---|---|---|---|---|"]
                for s, v in q["slots"].items():
                    ch = f"{v['chosen_correct'] / v['chosen']:.3f}" if v["chosen"] else "-"
                    L.append(f"| {s} | {v['correct']} | {v['unknown']} | {v['wrong']} | {v['single']} | {ch} |")
                if split != "ho":
                    fq = A.frame_quality(split, enc[(model, split)], t)
                    L += ["", "By wording frame (distinct texts / complete records correct): " + "; ".join(
                        f"{f} {n}/{ok}" for f, (n, ok) in fq.items())]
                L += ["", "By role and absence: " + "; ".join(
                    f"{k} {v['correct']}/{v['unknown']}/{v['wrong']}" for k, v in sorted(q["roles"].items())), ""]
                T = A.tasks(split, enc[(model, split)], t)
                c = A.cells(T["intact"])
                L += ["| kind:goal | success LM | success reference | pair success | confident-error rate | coverage | min world |",
                      "|---|---|---|---|---|---|---|"]
                for k, v in c.items():
                    cer = "-" if v["confident_error_rate"] is None else f"{v['confident_error_rate']:.3f}"
                    L.append(f"| {k} | {v['success_lm']:.3f} | {v['success_ref']:.3f} | {v['pair_success']:.3f} | {cer} | "
                             f"{v['coverage']:.3f} | {v['world_success_min']:.0f} |")
                checks = A.encoder_qualified(q, c)
                passed = all(ok for _, ok in checks)
                L += ["", f"3.5 criteria on {split} ({label}): {'all met' if passed else 'NOT met'}", ""]
                L += [f"- {'PASS' if ok else 'FAIL'} {text}" for text, ok in checks if not ok][:20] + [""]
                decisions.setdefault(model, {}).setdefault("criteria", {})[f"{split}:{label}"] = passed
                if split == "ho" and req.get("frozen") and label == "thresholds":
                    s33 = run_round33.summarise(T["rows33"])
                    s34 = run_round34.summarise(T["rows34"])
                    orig = collect_round33.criteria(s33, SIZES["ho"]) + collect_round34.criteria(s34, SIZES["ho"])
                    decisions[model]["ENCODER_QUALIFIED"] = "YES" if passed else "NO"
                    decisions[model]["MILESTONE_ORIGINAL_RULES"] = "PASS" if all(ok for _, ok in orig) else "FAIL"
                    L += ["Original round 3.3 / 3.4 milestone rules on the LM system (holdout):", ""]
                    L += [f"- {'PASS' if ok else 'FAIL'} {text}" for text, ok in orig] + [""]
    return L, decisions


def main(request_path: str, dest: str, pins_path: str, commit: str | None = None) -> int:
    req = json.loads(Path(request_path).read_text())
    dest = Path(dest)
    enc, reports, problems = load(req, request_path, pins_path, dest, commit)
    verdict = "COMPLETE" if not problems else "INCOMPLETE"
    lines = [f"FAILED {p}" for p in problems] or ["OK every planned report present, valid and from this run"]
    summary, decisions = [], {}
    try:
        if req["phase"] == "timing":
            summary = timing_summary(req, reports)
            if not all(d["cache_check"]["ok"] for d in reports.values()):
                lines.append("FAILED cache_check")
                verdict = "INCOMPLETE"
        elif req["phase"] == "probe":
            if verdict == "COMPLETE":
                summary = probe_summary(req, enc)
        elif verdict == "COMPLETE":
            summary, decisions = encode_summary(req, enc)
    except Exception as exc:
        verdict = "INCOMPLETE"
        lines.append(f"FAILED summary {type(exc).__name__}: {exc}")
    if req["phase"] == "encode" and "ho" in req["splits"]:
        for model in req["models"]:
            d = decisions.setdefault(model, {})
            if verdict != "COMPLETE":
                d["ENCODER_QUALIFIED"] = "UNDECIDABLE"
                d["MILESTONE_ORIGINAL_RULES"] = "FAIL"
    (dest / "CHECK.txt").write_text("\n".join(lines + ["", f"VERDICT {verdict}"]) + "\n")
    (dest / "SUMMARY.md").write_text("\n".join(summary) + "\n")
    (dest / "DECISIONS.json").write_text(json.dumps(decisions, indent=1, sort_keys=True) + "\n")
    (dest / "VERDICT").write_text(verdict + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:5]))
