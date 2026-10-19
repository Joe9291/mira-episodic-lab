"""Round 3.5: five systematically chosen cases for the human check (Astra's idea after the
v2 review). Deterministic: in each category the pair/text with the lowest index.

  python3 bench/m3/cases35.py RUN_DIR [--split ho]

1. a historical pair (3.4 object kind): both worlds, their critical notes and the three
   history goals; 2. a role change (3.3 giver kind: someone else gives to you); 3. the
   narrator as actor in an inverted holdout wording ("<place> was where you went ...");
   4. the first wrong slot or wrong decision, if any; 5. the first declared unknown
   (abstention) and the decisions of the worlds that contain it, if any.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from episodic_lab import analysis35 as A  # noqa: E402
from episodic_lab.cands35 import SLOTS, truth_value  # noqa: E402
from episodic_lab.encoder35 import decide_record  # noqa: E402
from episodic_lab.env35 import split_pairs  # noqa: E402


def record(enc, taus, text, truth):
    content, unk, det = decide_record(enc[text], taus)
    got = {s: ("?" if s in unk else content[s]) for s in SLOTS}
    bad = [s for s in SLOTS if s not in unk and det[s]["value"] != truth_value(s, truth)]
    return {"text": text, "record": got, "truth": {s: truth[s] for s in SLOTS}, "unknown": unk, "wrong": bad}


def main(run_dir: str, split: str = "ho") -> int:
    run = Path(run_dir)
    req = json.loads((run / "request.json").read_text())
    A.DECODING.update({"receiver_differs_from_actor": False, "structural_slots": False, "joint_roles": False},
                      **req.get("decoding", {}))
    taus = req["frozen"]["taus"]
    enc = {}
    for f in sorted(run.glob(f"r35_encode_*_{split}_*.json")):
        enc.update(json.loads(f.read_text())["encodings"])
    pairs = split_pairs(split)
    rows = {(r["kind"], r["seed"], r["world"], r["goal"]): r for r in A.tasks(split, enc, taus)["intact"]}
    out = {}

    def decisions(p, w):
        return {g: {"truth": r["truth"], "lm": r["lm_action"], "policy": r["lm_policy"]}
                for (k, s, wn, g), r in rows.items() if k == p["kind"] and s == p["seed"] and wn == w}

    p = next(q for q in pairs if q["kind"] == "object")
    out["1_historical_pair"] = {"seed": p["seed"], "object": p["object"], "worlds": {
        w: {"critical": record(enc, taus, p["worlds"][w]["experiences"][p["critical"]]["text"],
                               p["worlds"][w]["truth_content"][p["critical"]]),
            "decisions": decisions(p, w)} for w in p["worlds"]}}
    p = next(q for q in pairs if q["kind"] == "giver")
    w = p["worlds"]["A"]
    i = next(i for i, c in enumerate(w["truth_content"]) if c["action"] == "gave" and c["object"] == p["object"])
    out["2_role_change"] = {"seed": p["seed"], "object": p["object"],
                            "gave_note": record(enc, taus, w["experiences"][i]["text"], w["truth_content"][i]),
                            "critical": record(enc, taus, w["experiences"][p["critical"]]["text"],
                                               w["truth_content"][p["critical"]]),
                            "decisions": decisions(p, "A")}
    found = None
    for q in pairs:
        for wn, w in q["worlds"].items():
            for e, c in zip(w["experiences"], w["truth_content"]):
                if e["frame"].startswith("went:holdout:0") or (split != "ho" and e["frame"].startswith("went:")):
                    found = found or record(enc, taus, e["text"], c)
    out["3_narrator_as_actor"] = found
    texts = {}
    for q in pairs:
        for wn, w in q["worlds"].items():
            for e, c in zip(w["experiences"], w["truth_content"]):
                texts.setdefault(e["text"], (c, q, wn))
    wrong = next((record(enc, taus, t, c) for t, (c, q, wn) in texts.items() if record(enc, taus, t, c)["wrong"]), None)
    wrong_dec = next(({"kind": k[0], "seed": k[1], "world": k[2], "goal": k[3], **{x: r[x] for x in ("truth", "lm_action", "lm_policy")}}
                      for k, r in rows.items() if r["lm_action"] != r["truth"]), None)
    out["4_error"] = {"wrong_slot": wrong, "wrong_decision": wrong_dec,
                      "wrong_records": sum(bool(record(enc, taus, t, c)["wrong"]) for t, (c, q, wn) in texts.items()),
                      "wrong_decisions": sum(r["lm_action"] != r["truth"] for r in rows.values())}
    unk = next(((t, c, q, wn) for t, (c, q, wn) in texts.items() if record(enc, taus, t, c)["unknown"]), None)
    out["5_abstention"] = None if unk is None else {
        "record": record(enc, taus, unk[0], unk[1]), "seed": unk[2]["seed"], "world": unk[3],
        "decisions": decisions(unk[2], unk[3]),
        "unknown_records": sum(bool(record(enc, taus, t, c)["unknown"]) for t, (c, q, wn) in texts.items()),
        "non_memory_decisions": sum(r["lm_policy"] != "memory" for r in rows.values())}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    raise SystemExit(main(args[0], args[args.index("--split") + 1] if "--split" in args else "ho"))
