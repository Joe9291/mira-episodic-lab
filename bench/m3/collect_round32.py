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

from episodic_lab.cells import CELLS, slot_accuracy  # noqa: E402
from episodic_lab.memory import STATUSES, answer_query, misbind, parse_question  # noqa: E402
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
    if name in SELECTING:
        for r in rows:
            d = r.get("diag")
            if not (isinstance(d, dict) and isinstance(d.get("selected"), list)
                    and isinstance(d.get("complete"), bool)
                    and d.get("gold_support_selected") in (True, False, None)
                    and (d.get("result") is None or d["result"].get("status") in STATUSES)):
                problems.append(f"diag:{where}")
                break


def replay(name, data_cell, world, questions, encoder_records=None):
    """Re-run a deterministic cell (or the LM-encoder cell from its recorded records)."""
    if name == "full+ops/lm-encoder":
        recs = iter(encoder_records)

        def enc(text):
            r = next(recs)
            if r["text"] != text:
                raise ValueError("encoder records out of order")
            return {k: r["lm"][k] for k in CONTENT}
        cell = CELLS["full+ops"](encoder=enc, encoder_name="replay")
    else:
        cell = CELLS[name]()
    result = run_world(cell, world, questions)
    return {(r["phase"], r["qid"]): r["raw"] for r in result["rows"]}, cell


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
        enc = (c.get("encoder") or {}).get("records")
        if not isinstance(enc, list) or [r.get("text") for r in enc] != [e["text"] for e in world["episodes"]]:
            p.append(f"encoder:{overlap}")
            enc = None
        for name in DETERMINISTIC + (("full+ops/lm-encoder",) if enc else ()):
            if cells[name].get("status") != "OK":
                continue
            try:
                raws, cell = replay(name, cells[name], world, questions, enc)
            except Exception as exc:
                p.append(f"replay_error:{overlap}:{name}:{type(exc).__name__}")
                continue
            if raws != {(r["phase"], r["qid"]): r["raw"] for r in cells[name]["rows"]}:
                p.append(f"replay:{overlap}:{name}")
            if name == "full+ops" and c.get("store_seal") != cell.store.seal():
                p.append(f"seal:{overlap}")
        for name in ("lex3+reader", "struct3+reader"):
            if cells[name].get("status") != "OK":
                continue
            ref = CELLS["lex3+ops" if name.startswith("lex") else "struct3+ops"]()
            for e in world["episodes"]:
                ref.encode(e["text"])
            n_early = sum(e["block"] == "early" for e in world["episodes"])
            text = {q["qid"]: q["text"] for q in questions["public"]["final"]}
            for r in cells[name]["rows"]:
                recs = ref.store._records if r["phase"] == "final" else ref.store._records[:n_early]
                if ref.explain(text[r["qid"]], recs)["selected"] != r.get("diag", {}).get("selected"):
                    p.append(f"selection_replay:{overlap}:{name}")
                    break
        ref = CELLS["full+ops"]()
        for e in world["episodes"]:
            ref.encode(e["text"])
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


def table(cells) -> str:
    conds = [c for d in cells.values() for c in d["conditions"].values()]
    L = ["# Round 3.2 summary (exploratory, template benchmark)", "",
         f"{len(cells)} worlds x 2 overlap conditions; final test; means over worlds and conditions.",
         "E5 = correct rejection of binding lures; FR = in-world false recall. Gold support = share "
         "of positive final items whose gold target episodes were all selected (evaluator "
         "information, not an upper bound of accuracy).", "",
         "| cell | " + " | ".join(CRIT) + " | E3a pairs | E5 FR | gold support | calls | new tokens |",
         "|" + "---|" * (len(CRIT) + 6)]
    for name in CELL_NAMES:
        cs = [c["cells"][name] for c in conds]
        row = [name] + [f"{mean(x['final'][k]['accuracy'] for x in cs):.2f}" for k in CRIT]
        pairs = [x["final"]["E3a"].get("pairs") for x in cs]
        row.append(f"{mean(q['both_correct'] for q in pairs):.2f}" if all(pairs) else "-")
        row.append(f"{mean(x['final']['E5']['false_recall'] for x in cs):.2f}")
        sup = [r["diag"]["gold_support_selected"] for x in cs for r in x["rows"]
               if r["phase"] == "final" and "diag" in r and r["diag"]["gold_support_selected"] is not None]
        row.append(f"{mean(sup):.2f}" if sup else "-")
        row.append(str(sum(x["cost"]["calls"] for x in cs)))
        row.append(str(sum(x["cost"]["new_tokens"] for x in cs)))
        L.append("| " + " | ".join(row) + " |")
    L += ["", "## Operator statuses (final test)", "", "| cell | " + " | ".join(STATUSES) + " |",
          "|" + "---|" * (len(STATUSES) + 1)]
    for name in ("lex3+ops", "struct3+ops", "full+ops", "random3+ops", "full+ops/lm-encoder"):
        st = [r["diag"]["result"]["status"] for c in conds for r in c["cells"][name]["rows"] if r["phase"] == "final"]
        L.append(f"| {name} | " + " | ".join(f"{st.count(s) / len(st):.2f}" for s in STATUSES) + " |")
    pairs = [(r["lm"], r["truth"]) for c in conds for r in c["encoder"]["records"]]
    acc = slot_accuracy(pairs)
    invalid = sum(bool(r["invalid"]) for c in conds for r in c["encoder"]["records"])
    L += ["", "## LM encoder (slot filling) vs template truth", "",
          "| " + " | ".join(acc) + " | records with invalid slots |", "|" + "---|" * (len(acc) + 1),
          "| " + " | ".join(f"{v:.3f}" for v in acc.values()) + f" | {invalid}/{len(pairs)} |", "",
          "## Controls", "",
          f"- misbound store + operators: E2 {mean(c['misbound']['summary']['E2']['accuracy'] for c in conds):.2f}, "
          f"E5 FR {mean(c['misbound']['summary']['E5']['false_recall'] for c in conds):.2f}",
          f"- restart (store file of full+ops): same answers {sum(c['restart']['same_as_in_process'] for c in conds)}/{len(conds)}, "
          f"accuracy after restart {mean(c['restart']['accuracy_after_restart'] for c in conds):.3f}, "
          f"empty store on positive items {mean(c['restart']['empty_store_positive_accuracy'] for c in conds):.3f}, "
          f"truncated refused {sum(c['restart']['truncated_store_refused'] for c in conds)}/{len(conds)}, "
          f"changed refused {sum(c['restart']['changed_store_refused'] for c in conds)}/{len(conds)}"]
    return "\n".join(L) + "\n"


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(request_path, dest, pins_path):
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
    try:
        (dest / "SUMMARY.md").write_text(table(cells))
    except Exception as exc:
        ok = False
        lines.append(f"FAILED SUMMARY.md {type(exc).__name__}")
        (dest / "SUMMARY.md").write_text(f"summary failed: {type(exc).__name__}: {exc}\n")
    (dest / "CHECK.txt").write_text("\n".join(lines) + "\n")
    (dest / "VERDICT").write_text("COMPLETE\n" if ok else "INCOMPLETE\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
