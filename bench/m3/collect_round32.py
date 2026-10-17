"""Collector of round 3.2: completeness, summaries recomputed from the rows, SUMMARY.md."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from episodic_lab.score import summarise  # noqa: E402

SCHEMA = "episodic_lab.round32_cell.v1"
CELLS = ("A0", "A1", "lex+reader", "struct+reader", "lex+ops", "struct+ops", "random+ops",
         "struct+ops/lm-encoder")
CRIT = ("E2", "E3a", "E3b", "E4", "E5", "E7")


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def validate(data, model, series, index):
    if not isinstance(data, dict):
        return ["not_an_object"]
    p = []
    if data.get("schema") != SCHEMA:
        p.append("schema")
    if (data.get("model"), data.get("series"), data.get("index")) != (model, series, index):
        p.append("identity")
    if data.get("status") != "OK":
        return p + ["status"]
    conds = data.get("conditions", {})
    if set(conds) != {"high", "low"}:
        return p + ["conditions"]
    for o, c in conds.items():
        if set(c.get("cells", {})) != set(CELLS):
            p.append(f"cells:{o}")
            continue
        for name, cell in c["cells"].items():
            rows = cell.get("rows") or []
            for phase in ("phase1", "final"):
                sub = [r for r in rows if r.get("phase") == phase]
                if not sub or not same(cell.get(phase), summarise(sub)):
                    p.append(f"summary:{o}:{name}:{phase}")
        for key in ("encoder", "misbound", "restart"):
            if key not in c:
                p.append(f"{key}:{o}")
        if "misbound" in c and not same(c["misbound"]["summary"], summarise(c["misbound"]["rows"])):
            p.append(f"misbound_summary:{o}")
    return p


def mean(v):
    v = list(v)
    return sum(v) / len(v) if v else float("nan")


def table(cells):
    conds = [c for d in cells.values() for c in d["conditions"].values()]
    L = ["# Round 3.2 summary (exploratory, template benchmark)", "",
         f"{len(cells)} worlds x 2 overlap conditions; final test; means over worlds and conditions.",
         "E5 = correct rejection of binding lures; FR = in-world false recall. Recall = share of "
         "positive final items whose target episodes are all retrieved (E2/E3b/E7).", "",
         "| cell | " + " | ".join(CRIT) + " | E3a pairs | E5 FR | recall E2 | recall E3b | recall E7 | LM calls |",
         "|" + "---|" * (len(CRIT) + 7)]
    for name in CELLS:
        cs = [c["cells"][name] for c in conds]
        row = [name] + [f"{mean(x['final'][k]['accuracy'] for x in cs):.2f}" for k in CRIT]
        pairs = [x["final"]["E3a"].get("pairs") for x in cs]
        row.append(f"{mean(p['both_correct'] for p in pairs):.2f}" if all(pairs) else "-")
        row.append(f"{mean(x['final']['E5']['false_recall'] for x in cs):.2f}")
        for k in ("E2", "E3b", "E7"):
            rec = [x.get("retrieval_recall", {}).get(k) for x in cs]
            row.append(f"{mean(rec):.2f}" if all(r is not None for r in rec) else "-")
        row.append(str(sum(x["lm_calls"] for x in cs)))
        L.append("| " + " | ".join(row) + " |")
    L += ["", "## LM encoder (slot filling) vs template truth", ""]
    slots = conds[0]["encoder"]["slot_accuracy"].keys()
    L.append("| " + " | ".join(slots) + " |")
    L.append("|" + "---|" * len(slots))
    L.append("| " + " | ".join(f"{mean(c['encoder']['slot_accuracy'][s] for c in conds):.3f}" for s in slots) + " |")
    L += ["", "## Controls", "",
          f"- misbound store + operators: E2 {mean(c['misbound']['summary']['E2']['accuracy'] for c in conds):.2f}, "
          f"E5 FR {mean(c['misbound']['summary']['E5']['false_recall'] for c in conds):.2f}",
          f"- restart: same answers as in-process in {sum(c['restart']['same_as_in_process'] for c in conds)}/{len(conds)}; "
          f"accuracy after restart {mean(c['restart']['accuracy_after_restart'] for c in conds):.3f}; "
          f"empty store, positive items {mean(c['restart']['empty_store_positive_accuracy'] for c in conds):.3f}; "
          f"tampered store refused {sum(c['restart']['tampered_store_refused'] for c in conds)}/{len(conds)}"]
    return "\n".join(L) + "\n"


def main(request_path, dest):
    req = json.loads(Path(request_path).read_text())
    dest, cells, lines = Path(dest), {}, []
    for series, indices in req["worlds"].items():
        for i in indices:
            name = f"r32_{series}_{i}.json"
            try:
                data = json.loads((dest / name).read_text())
                problems = validate(data, req["model"], series, i)
            except Exception as exc:
                data, problems = None, [f"unreadable:{type(exc).__name__}"]
            lines.append(f"{'OK' if not problems else 'FAILED'} {name} {' '.join(problems)}".rstrip())
            if not problems:
                cells[(series, i)] = data
    ok = len(cells) == sum(len(v) for v in req["worlds"].values())
    try:
        (dest / "SUMMARY.md").write_text(table(cells))
    except Exception as exc:
        ok = False
        lines.append(f"FAILED SUMMARY.md {type(exc).__name__}")
    (dest / "CHECK.txt").write_text("\n".join(lines) + "\n")
    (dest / "VERDICT").write_text("COMPLETE\n" if ok else "INCOMPLETE\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
