"""Collector of round 3.5 (docs/ROUND_3_5.md). Nothing is taken on trust: every planned
encode report must be present, valid, from the run's code commit and the request; every
decision is re-derived from the recorded scores.

Phases (config/round35.json "phase"):
  timing  cost per text, model loading, extrapolation to every split, cache check
  encode  for the listed splits; with "cal": thresholds per slot and the holdout gate;
          with a qualification split ("ho" in round 3.5, "res" in round 3.5b):
          ENCODER_QUALIFIED and MILESTONE_ORIGINAL_RULES with the frozen configuration given
          in the request ("frozen": {"model", "decoder_version", "taus", "code_sha256"}),
          plus comparison decodings, class diagnostics and error consequences (3.5b)
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
import freeze35  # noqa: E402
import run_round33  # noqa: E402
import run_round34  # noqa: E402
import run_round35  # noqa: E402
from episodic_lab import analysis35 as A  # noqa: E402
from episodic_lab.cands35 import SLOTS  # noqa: E402
from episodic_lab.encoder35 import DECODER_VERSION  # noqa: E402
from episodic_lab.env35 import SIZES  # noqa: E402

JOB_HOURS = 5.5   # usable part of the 6-hour job limit
QUALIFICATION = ("ho", "res")   # splits on which a frozen configuration qualifies (once each)
COMPARISONS = {"d2 (no schema rules F1/F2)": {"object_two_tokens": False, "gave_receiver_self": False},
               "F1 only": {"object_two_tokens": True, "gave_receiver_self": False},
               "F2 only": {"object_two_tokens": False, "gave_receiver_self": True}}


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
    """Development probe: quality with the best value (tau 0) under each scoring mode the
    encodings allow (sum = the approved definition; mean and pmi = development
    comparisons), per wording frame, and examples."""
    from episodic_lab.cands35 import ranking, truth_value
    from episodic_lab.encoder35 import view
    truth = A.truths("dev")
    frame = {e["text"]: e["frame"] for p in A.split_pairs("dev") for w in p["worlds"].values() for e in w["experiences"]}
    L = ["# Round 3.5 development probe", ""]
    for model in req["models"]:
        e = enc[(model, "dev")]
        first = next(iter(e.values()))["actor"][0]
        modes = ["sum"] + (["mean", "pmi"] if len(first) >= 5 and first[3] is not None and first[4] else [])
        for mode in modes:
            q = A.quality(e, truth, {s: 0.0 for s in SLOTS}, mode)
            L += [f"## {model}, scoring {mode}: complete records {q['complete_records']:.3f} ({q['texts']} texts)", "",
                  "| slot | correct | wrong |", "|---|---|---|"]
            L += [f"| {s} | {v['correct']} | {v['wrong'] + v['unknown']} |" for s, v in q["slots"].items()]
            L += ["", "By role: " + "; ".join(f"{k} {v['correct']}/{v['wrong'] + v['unknown']}" for k, v in sorted(q["roles"].items())), ""]
            per = {}
            for text, x in e.items():
                ok = all(ranking(view(x[s], mode))[0] == truth_value(s, truth[text]) for s in SLOTS)
                per.setdefault(frame[text], [0, 0])
                per[frame[text]][0] += 1
                per[frame[text]][1] += ok
            L += ["By frame (texts/complete): " + "; ".join(f"{f} {n}/{k}" for f, (n, k) in sorted(per.items())), "",
                  "Examples of wrong slots:", ""]
            shown = {}
            for text, x in sorted(e.items()):
                for s in SLOTS:
                    v = ranking(view(x[s], mode))[0]
                    if v != truth_value(s, truth[text]) and shown.get(s, 0) < 3:
                        shown[s] = shown.get(s, 0) + 1
                        L.append(f"- {s}: \"{text}\" -> {v!r} (true {truth_value(s, truth[text])!r})")
            L.append("")
    return L


def comparisons(split: str, enc: dict, truth: dict, taus: dict) -> list[str]:
    """Comparison decodings on the same encodings and thresholds (not the primary result)."""
    L = ["Comparison decodings (same encodings and thresholds; the primary result is the frozen decoding above):", ""]
    saved = dict(A.DECODING)
    try:
        for name, opts in COMPARISONS.items():
            A.DECODING.update(opts)
            q = A.quality(enc, truth, taus)
            c = A.cells(A.tasks(split, enc, taus)["intact"])
            met = all(ok for _, ok in A.encoder_qualified(q, c))
            weak = "; ".join(f"{k} {v['success_lm']:.3f}/{v['pair_success']:.3f}" for k, v in c.items()
                             if v["success_lm"] < 1 or v["pair_success"] < 1) or "every cell 1.000"
            L.append(f"- {name}: complete records {q['complete_records']:.3f}; 3.5 criteria {'met' if met else 'NOT met'}; "
                     f"cells below 1 (success/pair): {weak}")
    finally:
        A.DECODING.clear()
        A.DECODING.update(saved)
    return L + [""]


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
            decisions[model] = {"taus": taus, "calibration": cal, "decoder_version": DECODER_VERSION,
                                "decoding": dict(A.DECODING)}
            L += ["Thresholds (calibration split): " + "; ".join(
                f"{s} tau={cal[s]['tau'] if not isinstance(cal[s]['tau'], float) else round(cal[s]['tau'], 4)} acceptance "
                f"{'-' if cal[s]['acceptance'] is None else round(cal[s]['acceptance'], 3)} precision {'-' if cal[s]['precision'] is None else round(cal[s]['precision'], 4)} "
                f"({cal[s]['accepted']}/{cal[s]['items']}; basis {cal[s]['basis']}, single-value cases {cal[s]['singles']}"
                f"{'' if cal[s]['single_precision'] is None else ' precision ' + str(round(cal[s]['single_precision'], 4))})"
                for s in SLOTS), ""]
        if req.get("frozen"):
            taus = req["frozen"]["taus"]
        for split in req["splits"]:
            for label, t in (("best value (tau 0)", zero),) + ((("thresholds", taus),) if taus else ()):
                q = A.quality(enc[(model, split)], truth[split], t)
                L += [f"### {split}, {label}: complete records {q['complete_records']:.3f} ({q['texts']} texts)", "",
                      "| slot | correct | unknown | wrong | single-value (from text / from schema) | accuracy where chosen |",
                      "|---|---|---|---|---|---|"]
                for s, v in q["slots"].items():
                    ch = f"{v['chosen_correct'] / v['chosen']:.3f}" if v["chosen"] else "-"
                    L.append(f"| {s} | {v['correct']} | {v['unknown']} | {v['wrong']} | {v['single']} "
                             f"({v['single_text']} / {v['single_schema']}) | {ch} |")
                if label == "thresholds":
                    ctl = []
                    for kind in ("uniform", "random"):
                        qc = A.quality(A.rescored(enc[(model, split)], kind), truth[split], t)
                        det = sum(v["correct"] + v["wrong"] for v in qc["slots"].values())
                        cor = sum(v["correct"] for v in qc["slots"].values())
                        ctl.append(f"{kind} scores: complete records {qc['complete_records']:.3f}, slots decided "
                                   f"{det}/{qc['texts'] * len(SLOTS)}, of these correct {cor / det if det else 0:.3f}")
                    L += ["", "Schema-constrained controls (same candidates, decoder and thresholds, model scores "
                          "replaced): " + "; ".join(ctl)]
                fq = A.frame_quality(split, enc[(model, split)], t)
                L += ["", "By wording frame (distinct texts / complete records correct): " + "; ".join(
                    f"{f} {n}/{ok}" for f, (n, ok) in fq.items())]
                if label == "thresholds":
                    cd = A.class_diagnostics(split, enc[(model, split)], t)
                    L += ["", "Class diagnostics (texts / wrong / unknown / smallest correct margin): " + "; ".join(
                        f"{k} {v[0]}/{v[1]}/{v[2]}/{'-' if v[3] is None else round(v[3], 2)}" for k, v in cd.items())]
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
                if split in QUALIFICATION and req.get("frozen") and label == "thresholds":
                    s33 = run_round33.summarise(T["rows33"])
                    s34 = run_round34.summarise(T["rows34"])
                    orig = collect_round33.criteria(s33, SIZES[split]) + collect_round34.criteria(s34, SIZES[split])
                    decisions[model]["ENCODER_QUALIFIED"] = "YES" if passed else "NO"
                    decisions[model]["MILESTONE_ORIGINAL_RULES"] = "PASS" if all(ok for _, ok in orig) else "FAIL"
                    L += [f"Original round 3.3 / 3.4 milestone rules on the LM system ({split}):", ""]
                    L += [f"- {'PASS' if ok else 'FAIL'} {text}" for text, ok in orig] + [""]
                    L += comparisons(split, enc[(model, split)], truth[split], t)
                    cons = A.consequences(split, enc[(model, split)], t)
                    decisions[model]["consequences"] = cons
                    L += [f"Error consequences ({len(cons)} world decisions wrong or not from memory; "
                          f"{sum(not x['right'] for x in cons)} wrong):", ""]
                    for x in cons:
                        L.append(f"- {x['kind']} {x['seed']} {x['world']} {x['goal']}: policy {x['policy']}, action "
                                 f"{x['action']} ({'right' if x['right'] else 'wrong'}, true {x['truth']}); "
                                 f"faults: {' || '.join(x['faults']) or 'none'}")
                    L.append("")
    return L, decisions


def main(request_path: str, dest: str, pins_path: str, commit: str | None = None) -> int:
    req = json.loads(Path(request_path).read_text())
    A.DECODING.update(A.DECODING_OFF, **req.get("decoding", {}))
    dest = Path(dest)
    enc, reports, problems = load(req, request_path, pins_path, dest, commit)
    problems += freeze35.check(req.get("frozen"))   # frozen decoder and code = running decoder and code
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
                checks = {name: d.get("cache_check") for name, d in reports.items()}
                summary += ["Cache checks: " + "; ".join(
                    f"{n}: max diff {c['max_abs_diff']:.2e}, same choices {c['same_choices']}" for n, c in checks.items() if c)]
                if not all(c and c["ok"] for c in checks.values()):
                    lines.append("FAILED cache_check")
                    verdict = "INCOMPLETE"
        elif verdict == "COMPLETE":
            summary, decisions = encode_summary(req, enc)
    except Exception as exc:
        verdict = "INCOMPLETE"
        lines.append(f"FAILED summary {type(exc).__name__}: {exc}")
    if req["phase"] == "encode" and any(x in req["splits"] for x in QUALIFICATION):
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
