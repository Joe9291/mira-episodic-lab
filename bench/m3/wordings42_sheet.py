#!/usr/bin/env python3
"""Round 4.2: the meaning-check sheet for Joe - one rendered example of every note frame
(template, development, holdout, reserve), taken from development reports; for repeats,
corrections and retractions the inserted clause rotates so that every clause occurs.

usage: wordings42_sheet.py OUT.md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from episodic_lab import r42_wordings as WD  # noqa: E402
from episodic_lab import r42_world as W  # noqa: E402

TITLES = {"statement": "Aussage", "repeat": "Wiederholte Aussage", "correction": "Korrektur",
          "retraction": "Rücknahme", "meeting": "Treffen (Ankerereignis)"}
SPLITS = {"template": "Vorlage", "dev": "Entwicklung", "holdout": "Holdout", "reserve": "Reserve"}


def who(source, author):
    if source == "self":
        return "Mira selbst" if author != "self" else "ich (Mira, eigene Notiz)"
    return source + (" (= Verfasser)" if source == author else "")


def meaning(r, by_id, t, sub):
    a = "Ort" if r["attribute"] == "location" else "Besitzer"
    if t == "meeting":
        m = re.fullmatch(r"event:met (.+) at (.+)", r["subject"])
        return f"TREFFEN: Mira hat {m[1]} am Ort {m[2]} getroffen, an Tag {r['value']}."
    if t == "statement":
        return f"AUSSAGE: {r['subject']} - {a} = {r['value']}, gültig ab Tag {r['valid_from']}."
    ref = W.reference_of(r, by_id)
    if t == "repeat":
        return (f"WIEDERHOLUNG der Meldung von {who(ref['source'], r['source'])} vom Tag {ref['report_day']}: "
                f"{r['subject']} - {a} = {r['value']}, gültig ab Tag {r['valid_from']}.")
    if t == "correction":
        what = {"value": f"neuer {a}: {r['value']} (Gültigkeitsbeginn bleibt)",
                "date": f"neuer Gültigkeitsbeginn: Tag {r['valid_from']} (Wert bleibt)",
                "both": f"neuer {a}: {r['value']}, gültig ab Tag {r['valid_from']}"}[sub]
        return f"KORREKTUR der Meldung von {who(ref['source'], r['source'])} vom Tag {ref['report_day']} über {r['subject']} ({a}): {what}."
    return f"RÜCKNAHME der Meldung von {who(ref['source'], r['source'])} vom Tag {ref['report_day']} über {r['subject']} ({a})."


def main():
    pool = {}
    for pair in W.iter_pairs("dev"):
        for inst in pair["instances"]:
            reps = inst["A"]["reports"]
            by_id = {r["report_id"]: r for r in reps}
            for pos, r in enumerate(reps):
                t, sub = WD.note_type(r, by_id)
                attr = None if t == "meeting" else r["attribute"]
                pool.setdefault((t, attr, sub), []).append((r, by_id, f"{pair['pair']}|{inst['delay']}|{pos}"))
    lines = ["# Bedeutungsprüfung Runde 4.2 (Berichte als Notizen)", "",
             "Bitte pro Nummer prüfen: Sagt die englische Notiz genau das, was darunter als Bedeutung steht? "
             "Vor jeder Notiz steht ihr Kopf (Tag und Verfasser). In den Notizen ist „you“ immer Mira, „I“ / „my“ "
             "der Verfasser der Notiz. Antwort einfach: „passt“ oder die Nummern, die nicht passen, mit kurzem Grund.", "",
             "Jede Satzvorlage kommt genau einmal vor (Vorlage, 3 Entwicklung, 3 Holdout, 3 Reserve). Bei Wiederholungen, "
             "Korrekturen und Rücknahmen wechselt der eingesetzte Teilsatz, sodass jeder Teilsatz mindestens einmal "
             "vorkommt. Eine Aussage ohne Tagesangabe gilt nach der festen Regel ab dem Tag der Notiz.", ""]
    plan = [("statement", "location", None), ("statement", "holder", None), ("repeat", None, None),
            ("correction", None, None), ("retraction", None, None), ("meeting", None, None)]
    n = 0
    for t, fixed, _ in plan:
        lines += [f"## {TITLES[t]}" + (f" - {'Ort' if fixed == 'location' else 'Besitzer'}" if fixed else ""), ""]
        for frame in range(10):
            attr = fixed if t in ("statement",) else (None if t == "meeting" else ("location", "holder")[frame % 2])
            sub = ("value", "date", "both")[frame % 3] if t == "correction" else None
            cands = pool[(t, attr, sub)]
            r, by_id, key = cands[(frame * 7) % len(cands)]
            n += 1
            lines += [f"{n}. _{WD.header(r)}_ **{WD.render(r, by_id, frame, key)}**   _({SPLITS[WD.FRAME_SPLIT[frame]]})_  ",
                      f"   Bedeutung: {meaning(r, by_id, t, sub)}", ""]
    Path(sys.argv[1]).write_text("\n".join(lines) + "\n")
    print(n)


if __name__ == "__main__":
    main()
