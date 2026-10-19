"""Collector of round 3.6 (docs/ROUND_3_6.md). Nothing is taken on trust: every planned parse
report must be present, valid, from the run's code commit and the request; every outcome
is re-derived from the recorded scores.

Phases (config/round36.json "phase"):
  timing  cost per question, extrapolation, cache check
  probe   development texts: parser metrics with the best value (tau 0), baseline beside it
  encode  for the listed splits; with "cal": thresholds (decision table q1) and the dev/cal
          criteria; with a qualification split ("ho", or "res" by the logged procedure) and
          "frozen": PARSER_QUALIFIED and PARSER_MILESTONE_ORIGINAL_RULES
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
import freeze36  # noqa: E402
import run_round33  # noqa: E402
import run_round34  # noqa: E402
import run_round36  # noqa: E402
from episodic_lab import analysis36 as A  # noqa: E402
from episodic_lab.analysis35 import cells  # noqa: E402
from episodic_lab.baseline36 import parse_baseline  # noqa: E402
from episodic_lab.env36 import SIZES, split_questions  # noqa: E402
from episodic_lab.parser36 import DECODER_VERSION, calibrate, candidates, decide_question  # noqa: E402

JOB_HOURS = 5.5
QUALIFICATION = ("ho", "res")
REPORTS: dict = {}


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def planned(req: dict) -> list[tuple[str, str, int]]:
    if req["phase"] in ("timing", "probe"):
        return [(m, "dev", 0) for m in req["models"]]
    return [(m, s, c) for m in req["models"] for s in req["splits"] for c in range(req["chunks"])]


def load(req: dict, request_path: str, pins_path: str, dest: Path, commit: str | None):
    problems, reports, enc = [], {}, {}
    rsha, psha = sha256_file(request_path), sha256_file(pins_path)
    for model, split, chunk in planned(req):
        name = f"r36_{req['phase']}_{model}_{split}_{chunk}.json"
        try:
            d = json.loads((dest / name).read_text())
        except Exception as exc:
            problems.append(f"missing:{name}:{type(exc).__name__}")
            continue
        prov = d.get("provenance") or {}
        if (d.get("schema"), d.get("status"), d.get("phase"), d.get("model"), d.get("split"), d.get("chunk")) != (
                run_round36.SCHEMA, "OK", req["phase"], model, split, chunk):
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
                if set(enc.get((model, split), {})) != set(run_round36.split_texts(split)):
                    problems.append(f"texts:{model}:{split}")
    return enc, reports, problems


def fmt(kn) -> str:
    k, n = kn
    return f"{k}/{n}" + (f" ({k / n:.3f})" if n else "")


def metrics_lines(title: str, m: dict) -> list[str]:
    L = [f"#### {title}", "", "| measure | value |", "|---|---|"]
    for key in [k for k in m if k.startswith("exact:")]:
        L.append(f"| {key} | {fmt(m[key])} |")
    for key in ("wrong_accepted", "false_ok:CLARIFY", "false_ok:REFUSE", "handled:CLARIFY", "handled:REFUSE",
                "recognised_ambiguity", "unnecessary"):
        L.append(f"| {key} | {fmt(m[key])} |")
    L.append(f"| family macro CLARIFY / REFUSE | {m['family_macro:CLARIFY']} / {m['family_macro:REFUSE']} |")
    L += ["", "Families (right / texts): " + "; ".join(f"{k} {v[0]}/{v[1]}" for k, v in m["families"].items()),
          "", "Wordings (right / texts): " + "; ".join(f"{k} {v[0]}/{v[1]}" for k, v in m["wordings"].items()), ""]
    return L


def paired(lm: dict, base: dict, gold: dict) -> str:
    c = {"both right": 0, "only model right": 0, "only rules right": 0, "both wrong": 0}
    for t, g in gold.items():
        a, b = A.right(lm[t], g), A.right(base[t], g)
        c["both right" if a and b else "only model right" if a else "only rules right" if b else "both wrong"] += 1
    return "; ".join(f"{k} {v}" for k, v in c.items())


def causes(parses: dict, gold: dict) -> str:
    cnt = {}
    for t, g in gold.items():
        have = g["outcome"] == "REFUSE" or g["target"] in {c for _, c in candidates("target", t)}
        c = A.error_cause(parses[t], g, have)
        if c:
            cnt[c] = cnt.get(c, 0) + 1
    return "; ".join(f"{k} {v}" for k, v in sorted(cnt.items())) or "none"


def timing_summary(req: dict, reports: dict) -> list[str]:
    L = ["# Round 3.6 timing", ""]
    for name, d in sorted(reports.items()):
        secs = list(d["seconds"].values())
        mean = statistics.mean(secs)
        L.append(f"- {d['model']}: load {d['load_seconds']} s; {len(secs)} questions, mean {mean:.2f} s, "
                 f"max {max(secs):.2f} s; cache check {d['cache_check']}")
        for split in ("dev", "cal", "aud", "ho", "res"):
            n = len(run_round36.split_texts(split))
            hours = n * mean / 3600
            L.append(f"  - {split}: {n} texts, about {hours:.2f} h -> chunks needed {max(1, int(hours / JOB_HOURS) + 1)}")
    return L


def evaluate(split: str, enc: dict, taus: dict, label: str) -> tuple[list[str], dict]:
    gold = split_questions(split)
    parse_all = A.parse_table(split, enc, taus)
    parses = {t: parse_all[t] for t in gold}
    m = A.parser_metrics(parses, gold)
    base = {t: parse_baseline(t) for t in gold}
    mb = A.parser_metrics(base, gold)
    crit = A.parser_criteria(m)
    T = A.tasks(split, parse_all)
    c = cells(T["intact"])
    tcrit = A.task_criteria(c)
    passed = all(ok for _, ok in crit + tcrit)
    L = [f"### {split}, {label}: parser criteria {'all met' if passed else 'NOT met'}", ""]
    L += metrics_lines(f"LM parser ({split}, {label})", m)
    L += [f"Error causes: {causes(parses, gold)}", "",
          f"Rule baseline (development grammar): exact OK {sum(mb[k][0] for k in mb if k.startswith('exact:') and k.count(':') == 1)}"
          f"/{sum(mb[k][1] for k in mb if k.startswith('exact:') and k.count(':') == 1)}, handled CLARIFY "
          f"{fmt(mb['handled:CLARIFY'])}, handled REFUSE {fmt(mb['handled:REFUSE'])}, false OK CLARIFY "
          f"{fmt(mb['false_ok:CLARIFY'])}, false OK REFUSE {fmt(mb['false_ok:REFUSE'])}",
          f"Paired with the baseline (distinct texts): {paired(parses, base, gold)}", ""]
    for kind in ("uniform", "random"):
        ctl = {t: decide_question(_rescored(enc[t], kind, t), taus) for t in gold}
        mc = A.parser_metrics(ctl, gold)
        L.append(f"Control {kind} scores: right {sum(A.right(ctl[t], gold[t]) for t in gold)}/{len(gold)}; "
                 f"false OK CLARIFY {fmt(mc['false_ok:CLARIFY'])}, REFUSE {fmt(mc['false_ok:REFUSE'])}")
    L += ["", "| kind:goal | success LM | success reference | pair success | Wilson 95% | confident-error rate | coverage |",
          "|---|---|---|---|---|---|---|"]
    for k, v in c.items():
        lo, hi = A.wilson(round(v["pair_success"] * v["pairs"]), v["pairs"])
        cer = "-" if v["confident_error_rate"] is None else f"{v['confident_error_rate']:.3f}"
        L.append(f"| {k} | {v['success_lm']:.3f} | {v['success_ref']:.3f} | {v['pair_success']:.3f} | "
                 f"[{lo:.3f}, {hi:.3f}] | {cer} | {v['coverage']:.3f} |")
    L += ["", f"Control questions, agent behaviour per world: {A.control_outcomes(split, parse_all)}", ""]
    L += [f"- FAIL {t}" for t, ok in crit + tcrit if not ok][:30] + [""]
    return L, {"passed": passed, "T": T, "metrics": m}


def _rescored(encoding: dict, kind: str, text: str) -> dict:
    out = {}
    for slot, entries in encoding.items():
        rows = []
        for x in entries:
            if kind == "uniform":
                sc = 0.0
            else:
                h = hashlib.sha256(f"{text}|{slot}|{x[0]}".encode()).digest()
                sc = -10.0 * int.from_bytes(h[:8], "big") / 2 ** 64
            rows.append([x[0], x[1], sc] + list(x[3:]))
        out[slot] = rows
    return out


def encode_summary(req: dict, enc: dict) -> tuple[list[str], dict]:
    L, decisions = ["# Round 3.6 parse run", ""], {}
    for model in req["models"]:
        L += [f"## {model}", ""]
        taus = None
        dec = decisions.setdefault(model, {"decoder_version": DECODER_VERSION})
        if "cal" in req["splits"]:
            gold = split_questions("cal")
            cal = calibrate({t: enc[(model, "cal")][t] for t in gold}, gold)
            taus = {"intent": cal["intent"]["tau"], "target": cal["target"]["tau"]}
            dec.update(taus=taus, calibration=cal)
            L += [f"Thresholds (calibration split): intent {cal['intent']}; target {cal['target']}",
                  f"Calibration flow: {cal['flow']}", ""]
        if req.get("frozen"):
            taus = req["frozen"]["taus"]
        for split in req["splits"]:
            for label, t in (("best value (tau 0)", {"intent": 0.0, "target": 0.0}),) + (
                    (("thresholds", taus),) if taus else ()):
                lines, res = evaluate(split, enc[(model, split)], t, label)
                L += lines
                dec.setdefault("criteria", {})[f"{split}:{label}"] = res["passed"]
                if split in QUALIFICATION and req.get("frozen") and label == "thresholds":
                    T = res["T"]
                    orig = (collect_round33.criteria(run_round33.summarise(T["rows33"]), SIZES[split])
                            + collect_round34.criteria(run_round34.summarise(T["rows34"]), SIZES[split]))
                    dec["PARSER_QUALIFIED"] = "YES" if res["passed"] else "NO"
                    dec["PARSER_MILESTONE_ORIGINAL_RULES"] = "PASS" if all(ok for _, ok in orig) else "FAIL"
                    L += [f"Original round 3.3 / 3.4 milestone rules, correct store with the LM parser ({split}):", ""]
                    L += [f"- {'PASS' if ok else 'FAIL'} {text}" for text, ok in orig] + [""]
    return L, decisions


def probe_summary(req: dict, enc: dict) -> list[str]:
    L = ["# Round 3.6 probe (development texts, best value)", ""]
    gold_all = split_questions("dev", new_only=False)
    for model in req["models"]:
        e = enc[(model, "dev")]
        gold = {t: gold_all[t] for t in e if t in gold_all}
        parses = {t: decide_question(e[t], {"intent": 0.0, "target": 0.0}) for t in gold}
        m = A.parser_metrics(parses, gold)
        secs = [s for name, d in REPORTS.items() if d["model"] == model for s in d["seconds"].values()]
        L += [f"{model}: mean {statistics.mean(secs):.2f} s per question (max {max(secs):.2f})", ""]
        L += metrics_lines(f"{model}: {sum(A.right(parses[t], gold[t]) for t in gold)}/{len(gold)} right", m)
        L += [f"Error causes: {causes(parses, gold)}", ""]
        wrong = [t for t in gold if not A.right(parses[t], gold[t])][:25]
        L += [f"- {t!r}: gold {gold[t]['outcome']} {gold[t]['intent']} {gold[t]['target']} -> {parses[t]['outcome']} "
              f"{parses[t]['intent']} {parses[t]['target']} ({parses[t]['reason']})" for t in wrong] + [""]
    return L


def main(request_path: str, dest: str, pins_path: str, commit: str | None = None) -> int:
    req = json.loads(Path(request_path).read_text())
    dest = Path(dest)
    enc, reports, problems = load(req, request_path, pins_path, dest, commit)
    REPORTS.clear()
    REPORTS.update(reports)
    problems += freeze36.check(req.get("frozen"))
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
                if not all(d["cache_check"]["ok"] for d in reports.values()):
                    lines.append("FAILED cache_check")
                    verdict = "INCOMPLETE"
        elif verdict == "COMPLETE":
            summary, decisions = encode_summary(req, enc)
    except Exception as exc:
        verdict = "INCOMPLETE"
        lines.append(f"FAILED summary {type(exc).__name__}: {exc}")
    if req["phase"] == "encode" and any(x in req["splits"] for x in QUALIFICATION) and req.get("frozen"):
        for model in req["models"]:
            d = decisions.setdefault(model, {})
            if verdict != "COMPLETE":
                d["PARSER_QUALIFIED"] = "UNDECIDABLE"
                d["PARSER_MILESTONE_ORIGINAL_RULES"] = "FAIL"
    (dest / "CHECK.txt").write_text("\n".join(lines + ["", f"VERDICT {verdict}"]) + "\n")
    (dest / "SUMMARY.md").write_text("\n".join(summary) + "\n")
    (dest / "DECISIONS.json").write_text(json.dumps(decisions, indent=1, sort_keys=True, default=str) + "\n")
    (dest / "VERDICT").write_text(verdict + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:5]))
