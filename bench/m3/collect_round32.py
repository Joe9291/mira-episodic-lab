"""Collector of round 3.2. Nothing published is taken on trust:

- the world and question set of every cell are regenerated from series and index and must
  match the recorded hashes; every expected (phase, qid) must be answered exactly once;
- every answer row is re-scored from its raw answer with the regenerated gold
  (category, correctness, false recall, pair ids) and every summary and retention is
  recomputed from the re-scored rows;
- the deterministic cells (lex3+ops, struct3+ops, full+ops, random3+ops) are re-run
  completely by the collector and must give the same raw answers; the selections of the
  reader cells are replayed; the LM-encoder cell is replayed from its recorded records;
- encoder slot accuracies, the misbound control and the restart flags are recomputed or
  type-checked; provenance (request and pins hashes, one code commit) must agree.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from episodic_lab.cells import CELLS, INVALID, SLOT_QUESTIONS, _clean, diagnose, postprocess, slot_accuracy  # noqa: E402
from episodic_lab.memory import STATUSES, answer_query, misbind, parse_question, regex_encode  # noqa: E402
from episodic_lab.questions import make_world  # noqa: E402
from episodic_lab.runner import retention, run_world  # noqa: E402
from episodic_lab.score import score_world, summarise  # noqa: E402

SCHEMA = "episodic_lab.round32_cell.v2"
CELL_NAMES = ("A0", "A1", "lex3+reader", "lex3+ops", "struct3+reader", "struct3+ops", "full+ops",
              "random3+ops", "full+ops/lm-encoder")
DETERMINISTIC = ("lex3+ops", "struct3+ops", "full+ops", "random3+ops")
SELECTING = ("lex3+reader", "lex3+ops", "struct3+reader", "struct3+ops", "full+ops", "random3+ops",
             "full+ops/lm-encoder")
CONTENT = ("actor", "partner", "action", "object", "place", "event_day")
SLIM = ("qid", "criterion", "qtype", "phase", "raw", "category", "correct", "false_recall")
CRIT = ("E2", "E3a", "E3b", "E4", "E5", "E7")


def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def slim(rows):
    return [{k: r[k] for k in SLIM + ("pair",) if k in r} for r in rows]


def rescore(rows, questions):
    """Re-score from raw answers; returns slim rows in the scorer's order, or None."""
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        return None
    out = []
    for phase in ("phase1", "final"):
        expected = [q["qid"] for q in questions["public"][phase]]
        got = {r.get("qid"): r.get("raw") for r in rows if r.get("phase") == phase}
        if sorted(got) != sorted(expected) or len([r for r in rows if r.get("phase") == phase]) != len(expected):
            return None
        if not all(isinstance(v, str) for v in got.values()):
            return None
        out += slim(score_world(questions["gold"], questions["candidates"], got, phase))
    return out


def check_cell(name, cell, world, questions, problems, where):
    if not isinstance(cell, dict) or cell.get("status") != "OK":
        problems.append(f"cell_status:{where}")
        return
    rows = cell.get("rows")
    fresh = rescore(rows, questions)
    if fresh is None:
        problems.append(f"items:{where}")
        return
    stored = sorted((json.dumps({k: r[k] for k in r if k != "diag"}, sort_keys=True) for r in rows))
    if stored != sorted(json.dumps(r, sort_keys=True) for r in fresh):
        problems.append(f"rows_vs_rescore:{where}")
    for phase in ("phase1", "final"):
        if not same(cell.get(phase), summarise([r for r in fresh if r["phase"] == phase])):
            problems.append(f"summary:{where}:{phase}")
    if not same(cell.get("retention"), retention({"rows": fresh})):
        problems.append(f"retention:{where}")
    cost = cell.get("cost")
    if not (isinstance(cost, dict) and all(isinstance(cost.get(k), int) and cost[k] >= 0
                                           for k in ("calls", "prompt_tokens", "new_tokens"))):
        problems.append(f"cost:{where}")


class _NoModel:
    """Stands in for the reader model when only the selection is replayed."""
    def weights_digest(self, recompute=False):
        return ""


def presented(world):
    """Episode texts in the runner's encoding order (early block, then follow-ups)."""
    return [e["text"] for blk in ("early", "followup") for e in world["episodes"] if e["block"] == blk]


def replay(name, world, questions, encoder=None):
    """Re-create a cell's store exactly; deterministic cells are re-run completely."""
    if name == "full+ops/lm-encoder":
        recs = iter(encoder["records"])

        def enc(text):
            r = next(recs)
            if r["text"] != text:
                raise ValueError("encoder records out of order")
            return {k: r["lm"][k] for k in CONTENT}, list(r["invalid"])
        cell = CELLS["full+ops"](encoder=enc, encoder_name=encoder["encoder_name"])
    elif name in DETERMINISTIC:
        cell = CELLS[name]()
    else:
        cell = CELLS[name](_NoModel())
        for text in presented(world):
            cell.encode(text)
        return None, cell
    result = run_world(cell, world, questions)
    return {(r["phase"], r["qid"]): r["raw"] for r in result["rows"]}, cell


def check_encoder(enc, world) -> bool:
    if not (isinstance(enc, dict) and isinstance(enc.get("encoder_name"), str)
            and isinstance(enc.get("records"), list)):
        return False
    if [r.get("text") for r in enc["records"]] != presented(world):
        return False
    for r in enc["records"]:
        if r.get("truth") != regex_encode(r["text"]):
            return False
        if not isinstance(r.get("raw"), dict) or set(r["raw"]) != set(SLOT_QUESTIONS):
            return False
        content, bad = postprocess(r["raw"])
        if content != r.get("lm") or bad != r.get("invalid"):
            return False
    return True


def validate(data, expected, request_sha, pins_sha):
    if not isinstance(data, dict):
        return ["not_an_object"]
    p = []
    if data.get("schema") != SCHEMA:
        p.append("schema")
    for key in ("model", "series", "index"):
        if data.get(key) != expected[key]:
            p.append(f"identity:{key}")
    if data.get("status") != "OK":
        return p + ["status"]
    prov = data.get("provenance") or {}
    if prov.get("request_sha256") != request_sha or prov.get("pins_sha256") != pins_sha:
        p.append("provenance")
    attempt, pair = make_world(expected["series"], expected["index"], order_both=True)
    if data.get("attempt") != attempt or set(data.get("conditions", {})) != {"high", "low"}:
        return p + ["conditions"]
    for overlap, (world, questions) in pair.items():
        c = data["conditions"][overlap]
        if (c.get("world_sha256"), c.get("questions_sha256")) != (canonical_sha256(world), canonical_sha256(questions)):
            p.append(f"world_hash:{overlap}")
            continue
        cells = c.get("cells", {})
        if set(cells) != set(CELL_NAMES):
            p.append(f"cells:{overlap}")
            continue
        for name in CELL_NAMES:
            check_cell(name, cells[name], world, questions, p, f"{overlap}:{name}")
        enc = c.get("encoder")
        if not check_encoder(enc, world):
            p.append(f"encoder:{overlap}")
            enc = None
        for name in SELECTING:
            if cells[name].get("status") != "OK" or (name == "full+ops/lm-encoder" and enc is None):
                continue
            try:
                raws, cell = replay(name, world, questions, enc)
            except Exception as exc:
                p.append(f"replay_error:{overlap}:{name}:{type(exc).__name__}")
                continue
            rows = cells[name]["rows"]
            if raws is not None and raws != {(r["phase"], r["qid"]): r["raw"] for r in rows}:
                p.append(f"replay:{overlap}:{name}")
            if name == "full+ops" and c.get("store_seal") != cell.store.seal():
                p.append(f"seal:{overlap}")
            fresh = [{k: v for k, v in r.items() if k != "diag"} for r in rows]
            diagnose(cell, fresh, world, questions)
            if [f["diag"] for f in fresh] != [r.get("diag") for r in rows]:
                p.append(f"diag_replay:{overlap}:{name}")
        ref = CELLS["full+ops"]()
        for text in presented(world):
            ref.encode(text)
        mis_rows = slim(score_world(questions["gold"], questions["candidates"], {
            q["qid"]: answer_query(misbind(ref.store.records, world["seed"]), *parse_question(q["text"])).answer()
            for q in questions["public"]["final"]}, "final"))
        mis = c.get("misbound") or {}
        if not (same(mis.get("rows"), mis_rows) and same(mis.get("summary"), summarise(mis_rows))):
            p.append(f"misbound:{overlap}")
        r = c.get("restart") or {}
        if not (all(isinstance(r.get(k), bool) for k in ("same_as_in_process", "truncated_store_refused",
                                                          "changed_store_refused"))
                and isinstance(r.get("empty_store_positive_accuracy"), float)):
            p.append(f"restart:{overlap}")
    return p


def mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else float("nan")


def positive_score(rows) -> float:
    """Positive final items (E2, E3a, E3b, E4, E7), the two A/B orientations of an E3a pair
    weighing 1/2 each (as in the pilot's model selection)."""
    pos = [r for r in rows if r["phase"] == "final" and r["criterion"] in ("E2", "E3a", "E3b", "E4", "E7")]
    w = [0.5 if "pair" in r else 1.0 for r in pos]
    return sum(x for x, r in zip(w, pos) if r["correct"]) / sum(w)


def per_world(cells, name, fn):
    """fn over the rows of both conditions of a world, then the mean over worlds."""
    return mean(fn([r for c in d["conditions"].values() for r in c["cells"][name]["rows"]])
                for d in cells.values())


def lure_shares(rows):
    lures = [r for r in rows if r["phase"] == "final" and r["criterion"] == "E5"]
    n = len(lures)
    return {"rejected": sum(r["category"] == "none_answer" or r["correct"] for r in lures) / n,
            "false_recall": sum(r["false_recall"] for r in lures) / n,
            "unknown": sum(r["category"] == "uncertain" for r in lures) / n}


def adoption(cells, complete: bool) -> tuple[str, str]:
    """(decision, text). The adoption rule is evaluated only on the complete, fully
    validated set of planned world reports; otherwise it is not decidable."""
    if not complete:
        return "UNDECIDABLE", ("LM encoder qualification for the tested round 3.2 templates (docs/ROUND_3_2.md): NOT DECIDABLE - the evaluation is incomplete "
                               f"({len(cells)} valid world reports); partial tables above are diagnostic only.")
    every = [c for d in cells.values() for c in d["conditions"].values()]
    acc = slot_accuracy([(r["lm"], r["truth"]) for c in every for r in c["encoder"]["records"]])
    ref_pos = per_world(cells, "full+ops", positive_score)
    lm_pos = per_world(cells, "full+ops/lm-encoder", positive_score)
    fr = mean(lure_shares([r for c in d["conditions"].values() for r in c["cells"]["full+ops/lm-encoder"]["rows"]])["false_recall"]
              for d in cells.values())
    adopt = acc["all_slots"] >= 0.95 and lm_pos >= ref_pos - 0.02 and fr <= 0.05
    return ("ADOPT" if adopt else "KEEP"), (
        f"LM encoder qualification for the tested round 3.2 templates (docs/ROUND_3_2.md): all_slots {acc['all_slots']:.3f} >= 0.95; positives "
        f"full+ops/lm-encoder {lm_pos:.3f} vs full+ops {ref_pos:.3f} (at most 0.02 lower); lure false "
        f"recall {fr:.3f} <= 0.05 -> "
        + ("ADOPT the LM encoder for the round 3.2 template episode formats (other formats, e.g. the round 3.3 "
           "environment with \"You\" and object-free events, need their own check)" if adopt
           else "keep the template encoder; limit stated") + ".")


def table(cells, complete: bool = True) -> str:
    L = ["# Round 3.2 summary (exploratory, template benchmark)", ""]
    if not complete:
        L += ["**INCOMPLETE evaluation: only the valid world reports are tabulated, as diagnostics; "
              "no decision is drawn from them.**", ""]
    L += [
         "Means over worlds (both overlap conditions pooled within a world). Development worlds "
         "(dev-m3) and the pilot worlds already used (pilot-m2) are shown separately. "
         "E5 = correct rejection of binding lures; FR = in-world false recall; unknown = "
         "abstention. Coverage = share of final items whose selection was certified "
         "sufficient for the question; accuracy covered = accuracy on those items, pooled over all "
         "covered final items of the series; gold support = "
         "share of positive items whose gold target episodes were all selected (evaluator "
         "information, not an upper bound of accuracy).", ""]
    for series in sorted({s for s, _ in cells}):
        part = {k: v for k, v in cells.items() if k[0] == series}
        conds = [c for d in part.values() for c in d["conditions"].values()]
        L += [f"## {series} ({len(part)} worlds)", "",
              "| cell | positives | " + " | ".join(CRIT) + " | E3a pairs | E5 FR | E5 unknown | coverage | accuracy covered | gold support | calls | prompt tokens | seconds |",
              "|" + "---|" * (len(CRIT) + 11)]
        for name in CELL_NAMES:
            cs = [c["cells"][name] for c in conds]
            row = [name, f"{per_world(part, name, positive_score):.2f}"]
            row += [f"{mean(x['final'][k]['accuracy'] for x in cs):.2f}" for k in CRIT]
            pairs = [x["final"]["E3a"].get("pairs") for x in cs]
            row.append(f"{mean(q['both_correct'] for q in pairs):.2f}" if all(pairs) else "-")
            row.append(f"{mean(x['final']['E5']['false_recall'] for x in cs):.2f}")
            row.append(f"{per_world(part, name, lambda rows: lure_shares(rows)['unknown']):.2f}")
            final = [r for x in cs for r in x["rows"] if r["phase"] == "final"]
            if final and "diag" in final[0]:
                cov = [r for r in final if r["diag"]["covered"]]
                row.append(f"{len(cov) / len(final):.2f}")
                row.append(f"{mean(r['correct'] for r in cov):.2f}" if cov else "-")
                sup = [r["diag"]["gold_support_selected"] for r in final if r["diag"]["gold_support_selected"] is not None]
                row.append(f"{mean(sup):.2f}" if sup else "-")
            else:
                row += ["-", "-", "-"]
            row += [str(sum(x["cost"]["calls"] for x in cs)), str(sum(x["cost"]["prompt_tokens"] for x in cs)),
                    f"{sum(x['seconds'] for x in cs):.0f}"]
            L.append("| " + " | ".join(row) + " |")
        L += ["", "Operator statuses (final test):", "", "| cell | " + " | ".join(STATUSES) + " |",
              "|" + "---|" * (len(STATUSES) + 1)]
        for name in ("lex3+ops", "struct3+ops", "full+ops", "random3+ops", "full+ops/lm-encoder"):
            st = [r["diag"]["result"]["status"] for c in conds for r in c["cells"][name]["rows"] if r["phase"] == "final"]
            L.append(f"| {name} | " + " | ".join(f"{st.count(s) / len(st):.2f}" for s in STATUSES) + " |")
        L.append("")
    every = [c for d in cells.values() for c in d["conditions"].values()]
    pairs = [(r["lm"], r["truth"]) for c in every for r in c["encoder"]["records"]]
    acc = slot_accuracy(pairs) if pairs else {}
    invalid = sum(bool(r["invalid"]) for c in every for r in c["encoder"]["records"])
    # declared normalisation: a second-person reply repeating the first person -> "no second person"
    normalised = sum(_clean(r["raw"]["partner"], "person") not in (None, INVALID)
                     and _clean(r["raw"]["partner"], "person") == _clean(r["raw"]["actor"], "person")
                     for c in every for r in c["encoder"]["records"])
    L += ["## LM encoder (slot filling) vs template truth (valid worlds)", "",
          "| " + " | ".join(acc) + " | records with invalid slots | partner normalised to none |",
          "|" + "---|" * (len(acc) + 2),
          "| " + " | ".join(f"{v:.3f}" for v in acc.values()) + f" | {invalid}/{len(pairs)} | {normalised}/{len(pairs)} |", "",
          adoption(cells, complete)[1],
          "", "## Controls (valid worlds)", "",
          f"- misbound store + operators: E2 {mean(c['misbound']['summary']['E2']['accuracy'] for c in every):.2f}, "
          f"E5 FR {mean(c['misbound']['summary']['E5']['false_recall'] for c in every):.2f}",
          f"- restart (store file of full+ops): same answers {sum(c['restart']['same_as_in_process'] for c in every)}/{len(every)}, "
          f"accuracy after restart {mean(c['restart']['accuracy_after_restart'] for c in every):.3f}, "
          f"empty store on positive items {mean(c['restart']['empty_store_positive_accuracy'] for c in every):.3f}, "
          f"truncated refused {sum(c['restart']['truncated_store_refused'] for c in every)}/{len(every)}, "
          f"changed refused {sum(c['restart']['changed_store_refused'] for c in every)}/{len(every)}"]
    return "\n".join(L) + "\n"


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(request_path, dest, pins_path, commit=None):
    req = json.loads(Path(request_path).read_text())
    request_sha, pins_sha = sha256_file(request_path), sha256_file(pins_path)
    dest, cells, lines = Path(dest), {}, []
    for series, indices in req["worlds"].items():
        for i in indices:
            name = f"r32_{series}_{i}.json"
            try:
                data = json.loads((dest / name).read_text())
                problems = validate(data, {"model": req["model"], "series": series, "index": i},
                                    request_sha, pins_sha)
            except Exception as exc:
                data, problems = None, [f"unreadable:{type(exc).__name__}"]
            lines.append(f"{'OK' if not problems else 'FAILED'} {name} {' '.join(problems)}".rstrip())
            if not problems:
                cells[(series, i)] = data
    commits = {d["provenance"]["code_commit"] for d in cells.values()}
    ok = len(cells) == sum(len(v) for v in req["worlds"].values()) and len(commits) <= 1
    if len(commits) > 1:
        lines.append("FAILED provenance:mixed_commits")
    if commit is not None and commits - {commit}:
        ok = False
        lines.append("FAILED provenance:commit")
    decision = "UNDECIDABLE"
    try:
        (dest / "SUMMARY.md").write_text(table(cells, ok))
        decision = adoption(cells, ok)[0]
    except Exception as exc:
        ok = False
        lines.append(f"FAILED SUMMARY.md {type(exc).__name__}")
        (dest / "SUMMARY.md").write_text(f"summary failed: {type(exc).__name__}: {exc}\n")
    if not ok:
        decision = "UNDECIDABLE"
    (dest / "CHECK.txt").write_text("\n".join(lines) + "\n")
    (dest / "VERDICT").write_text("COMPLETE\n" if ok else "INCOMPLETE\n")
    (dest / "ENCODER_DECISION").write_text(decision + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:5]))
