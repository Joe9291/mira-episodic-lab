#!/usr/bin/env python3
"""Round 4.3: Joe's check sheet (docs/ROUND_4_3.md section 6) - five development cases chosen
by rule (the first match in family / pair order, world A, delay 0):
1 a cut between a report and its correction (P3); 2 a late report whose valid_from lies
before the cut (P2); 3 a conflict opened before and resolved after a cut (P8); 4 an
anchored question whose anchor lies before the cut (P9); 5 a Mode-T answer "compacted".
For each: the reports, the checkpoint at the cut, the tail, the question, the answer of
the full memory M and of Mode T.

usage: joe_cases43.py OUT.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from episodic_lab import r43_consolidate as X  # noqa: E402
from episodic_lab import r43_world as W  # noqa: E402
from episodic_lab.r40_memory import Memory  # noqa: E402


def fmt_rep(r):
    t = f" -> {r['target_report_id']}" if r["target_report_id"] else ""
    v = f" {r['value']!r}" if r["value"] is not None else ""
    vf = f" ab Tag {r['valid_from']}" if r["valid_from"] is not None else ""
    return f"- {r['report_id']} Tag {r['report_day']}: {r['source']} (Rang {r['rank']}) {r['kind']}{v}{vf}{t} [{r['subject']} / {r['attribute']}]"


def case(title, pair, inst, cut, q):
    w = inst["A"]
    reps = w["reports"]
    recs = X.chain_records(reps)
    cp = X.build_checkpoint(reps, recs, cut)
    rel = [r for r in reps if r["report_id"] in set(w["relevant_ids"])]
    tail = [r for r in reps[X.prefix_len(reps, cut):] if r["report_id"] in set(w["relevant_ids"])]
    h = X.mode_t(cp, reps, recs, X.trust_record(cp, X.seal_of(recs, len(reps))))
    m = Memory(reps)
    full = X.full_digest(m, (q["subject"], q["attribute"]), q["now"]) if q["op"] == "digest" else m.answer(q)
    asked = {tuple(pair["fact"])}
    if pair["anchor"]:
        asked.add(("event:" + pair["anchor"], "day"))
    claims = [x for x in X.checkpoint_claims(cp) if (x["subject"], x["attribute"]) in asked]
    lines = [f"## {title}", "", f"Welt {pair['pair']} A, Verzögerung 0, Schnitt nach Tag {cut} (heute: Tag {inst['now']}).", "",
             "Relevante Berichte (alle):"] + [fmt_rep(r) for r in rel]
    lines += ["", f"Verdichteter Stand C({cut}) - nur die noch geltenden Aussagen der gefragten Fakten:"]
    lines += [f"- {x['id']}: {x['value']!r} ab Tag {x['valid_from']}, {x['source']} (Rang {x['rank']}), Ursprung {x['origin']}"
              for x in claims] or ["- (keine)"]
    lines += ["", "Danach (Tail, relevante Berichte):"] + ([fmt_rep(r) for r in tail] or ["- (keine)"])
    qq = {k: v for k, v in q.items() if k not in ("qid", "subject", "attribute", "role")}
    lines += ["", f"Frage: {json.dumps(qq, ensure_ascii=False)}",
              f"- volles Gedächtnis M: `{json.dumps(full, ensure_ascii=False)}`",
              f"- verdichtet (Mode T): `{json.dumps(h.answer(q), ensure_ascii=False)}`", ""]
    return lines


def main():
    out = ["# Runde 4.3 - Joes Fallprüfung (5 Dev-Fälle nach Regel)", "",
           "Bitte je Fall prüfen: Stimmt die Antwort des verdichteten Gedächtnisses mit dem vollen Gedächtnis "
           "überein (bzw. ist \"compacted\" richtig, weil die Frage einen gelöschten Zeitpunkt braucht)? "
           "Und ergibt die Antwort aus den Berichten Sinn?", ""]
    pairs = {p["family"]: p for p in W.iter_pairs("dev") if p["index"] == 0}
    # 1 correction after the cut
    p = pairs["P3"]; inst = p["instances"][0]; w = inst["A"]
    corr = next(r for r in w["reports"] if r["kind"] == "correct" and r["report_id"] in set(w["relevant_ids"]))
    q = next(q for q in w["questions"] if q["op"] == "history")
    out += case("1. Schnitt zwischen einem Bericht und seiner Korrektur", p, inst, corr["report_day"] - 1, q)
    # 2 late report across the cut
    p = pairs["P2"]; inst = p["instances"][0]; w = inst["A"]
    late = next(r for r in w["reports"] if r["valid_from"] is not None and r["valid_from"] < r["report_day"]
                and r["report_id"] in set(w["relevant_ids"]))
    q = next(q for q in w["questions"] if q["op"] == "valid_at" and q["v"] >= late["valid_from"])
    out += case("2. Späte Nachricht, deren Gültigkeit vor dem Schnitt beginnt", p, inst, late["report_day"] - 1, q)
    # 3 conflict opened before, resolved after the cut
    p = pairs["P8"]; inst = p["instances"][0]; w = inst["A"]
    rel = [r for r in w["reports"] if r["report_id"] in set(w["relevant_ids"])]
    q = next(q for q in w["questions"] if q["op"] == "digest")
    out += case("3. Konflikt vor dem Schnitt, aufgelöst danach", p, inst, rel[-1]["report_day"] - 1, q)
    # 4 anchored question, anchor before the cut
    p = pairs["P9"]; inst = p["instances"][0]; w = inst["A"]
    anchor = next(r for r in w["reports"] if r["subject"].startswith("event:"))
    q = next(q for q in w["questions"] if q["op"] == "before")
    out += case("4. Frage 'vor dem Ereignis', Ereignis vor dem Schnitt", p, inst, anchor["report_day"], q)
    # 5 compacted
    p = pairs["P1"]; inst = p["instances"][0]; w = inst["A"]
    q = next(q for q in w["questions"] if q["op"] == "believed_at")
    out += case("5. Antwort \"compacted\": die Frage braucht einen Wissensstand vor dem Schnitt", p, inst, q["t"] + 1, q)
    Path(sys.argv[1]).write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
