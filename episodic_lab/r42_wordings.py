"""Round 4.2 note wordings (docs/ROUND_4_2.md section 2): every structured report of the
round 4.0 generator is rendered as a short note. Per note type and attribute ten frames:
index 0 = template, 1-3 development, 4-6 holdout, 7-9 reserve. Development, calibration
and audit use frames 0-3, the holdout 4-6, the reserve 7-9.

Every frame has an exact inverse parser (inverse()), used ONLY for the checks before
freezing (meaning preservation) - never on the extraction path.
"""
from __future__ import annotations

import hashlib
import re

SPLIT_FRAMES = {"dev": (0, 1, 2, 3), "cal": (0, 1, 2, 3), "audit": (0, 1, 2, 3),
                "holdout": (4, 5, 6), "reserve": (7, 8, 9)}
FRAME_SPLIT = {0: "template", 1: "dev", 2: "dev", 3: "dev", 4: "holdout", 5: "holdout",
               6: "holdout", 7: "reserve", 8: "reserve", 9: "reserve"}

# ---------------------------------------------------------------- content clauses
STATEMENT = {
    "location": [
        "{O} has been at {P}{SINCE}.",
        "Update: {O} has been kept at {P}{SINCE}.",
        "I can tell you that {O} has been at {P}{SINCE}.",
        "{P} is where {O} has been{SINCE}.",
        "Note for the record: {O} has been sitting at {P}{SINCE}.",
        "{O} has been located at {P}{SINCE}.",
        "Where is {O}? At {P}{SINCE}.",
        "{O} has been lying at {P}{SINCE}.",
        "{O} has stayed at {P}{SINCE}.",
        "For your information, {O} has been at {P}{SINCE}.",
    ],
    "holder": [
        "{H} has had {O}{SINCE}.",
        "Update: {O} has been with {H}{SINCE}.",
        "I can tell you that {H} has had {O}{SINCE}.",
        "{H} is the one who has had {O}{SINCE}.",
        "Note for the record: {O} has been in the hands of {H}{SINCE}.",
        "{O} has been kept by {H}{SINCE}.",
        "Who has {O}? {H}{SINCE}.",
        "{O} has been staying with {H}{SINCE}.",
        "{O} has stayed with {H}{SINCE}.",
        "For your information, {H} has had {O}{SINCE}.",
    ],
}
REPEAT_FRAMES = [
    "{SN} reported on {R} that {CA}.",
    "Passing on what {SN} said on {R}: {CA}.",
    "According to {SN} on {R}, {CA}.",
    "As {SN} told me on {R}, {CA}.",
    "I am only repeating {SP} report of {R}: {CA}.",
    "{SN} mentioned on {R} that {CA}; I pass it on.",
    "Heard from {SN} on {R}: {CB}.",
    "Relaying {SP} note from {R}: {CA}.",
    "Second-hand, from {SN} on {R}: {CA}.",
    "{SN} said on {R} that {CC}.",
]
REPEAT_CLAUSE = {
    "location": {"CA": "{O} has been at {P} since {D}", "CB": "{O} at {P} since {D}",
                 "CC": "since {D}, {O} has been at {P}"},
    "holder": {"CA": "{H} has had {O} since {D}", "CB": "{O} with {H} since {D}",
               "CC": "since {D}, {H} has had {O}"},
}
CORRECT_FRAMES = [
    "Correction to {SP} report of {R}: {CL}.",
    "{SPC} report of {R} was wrong: {CL}.",
    "Correcting {SP} note from {R}: {CL}.",
    "Please fix {SP} report of {R} - {CL}.",
    "About {SP} report of {R}: that was a mistake, {CL}.",
    "{SPC} entry of {R} needs a correction: {CL}.",
    "Not quite right in {SP} report of {R}; {CL}.",
    "Amendment to {SP} report of {R}: {CL}.",
    "I have to correct {SP} report of {R}: {CL}.",
    "Regarding {SP} report of {R}, the truth is that {CL}.",
]
CORRECT_CLAUSE = {
    ("location", "value"): "{O} was actually at {P}",
    ("location", "date"): "the move of {O} actually happened on {D}",
    ("location", "both"): "{O} was actually at {P} from {D}",
    ("holder", "value"): "{O} was actually with {H}",
    ("holder", "date"): "the handover of {O} actually happened on {D}",
    ("holder", "both"): "{O} was actually with {H} from {D}",
}
RETRACT_FRAMES = [
    "Please disregard {SP} report of {R} about {CL}.",
    "Withdraw {SP} report of {R} about {CL}.",
    "Withdrawn: {SP} report of {R} about {CL}.",
    "Forget {SP} report of {R} about {CL}.",
    "Cancel {SP} report of {R} about {CL}.",
    "Retracted: {SP} report of {R} about {CL}.",
    "Strike from the record {SP} report of {R} about {CL}.",
    "Ignore {SP} report of {R} about {CL}.",
    "Please drop {SP} report of {R} about {CL}.",
    "Retract {SP} report of {R} about {CL}, please.",
]
RETRACT_CLAUSE = {"location": "where {O} is", "holder": "who has {O}"}
MEETING_FRAMES = [
    "{WHO} met {N} at {Q} {DD}.",
    "{DDC}, {WHOL} met {N} at {Q}.",
    "{WHO} ran into {N} at {Q} {DD}.",
    "{WHOP} meeting {DD} with {N} at {Q}.",
    "{WHO} had a meeting with {N} at {Q} {DD}.",
    "It was {DD} that {WHOL} met {N} at {Q}.",
    "{N} and {WHOL} met at {Q} {DD}.",
    "{WHO} saw {N} at {Q} {DD} and talked for a while.",
    "At {Q}, {WHOL} met {N} {DD}.",
    "{DDC} {WHOL} met with {N} at {Q}.",
]


def _h(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


def day_phrase(day: int, report_day: int, key: str, allow_relative=True) -> str:
    """'today' / 'yesterday' (chosen by hash) or 'day N'."""
    if allow_relative and day == report_day and _h(key, "rel") % 2 == 0:
        return "today"
    if allow_relative and day == report_day - 1 and _h(key, "rel") % 2 == 0:
        return "yesterday"
    return f"day {day}"


def _poss(target_source: str, author: str) -> str:
    if target_source == author:
        return "my"
    if target_source == "self":
        return "your"
    return f"{target_source}'s"


def _name(source: str, author: str) -> str:
    if source == "self":
        return "you" if author != "self" else "I"
    return source


def note_type(report: dict, by_id: dict) -> tuple:
    """(type, subtype) of a structured report - used by the generator only."""
    if report["subject"].startswith("event:"):
        return ("meeting", None)
    if report["kind"] == "correct":
        sub = "both" if report["value"] is not None and report["valid_from"] is not None else \
            ("value" if report["value"] is not None else "date")
        return ("correction", sub)
    if report["kind"] == "retract":
        return ("retraction", None)
    if report["origin"] != "o-" + report["report_id"]:
        return ("repeat", None)
    return ("statement", None)


def header(report: dict) -> str:
    who = "your own note" if report["source"] == "self" else f"note from {report['source']}"
    return f"Day {report['report_day']}, {who}."


def render(report: dict, by_id: dict, frame: int, key: str) -> str:
    """Note text of a report with frame index `frame` (0-9); `by_id` resolves references."""
    t, sub = note_type(report, by_id)
    author, rd = report["source"], report["report_day"]
    attr = report["attribute"]
    f = {}
    if t == "meeting":
        m = re.fullmatch(r"event:met (.+) at (.+)", report["subject"])
        dd = day_phrase(report["value"], rd, key)
        dd = "on " + dd if dd.startswith("day") else dd
        f.update(N=m.group(1), Q=m.group(2), DD=dd, DDC=dd[0].upper() + dd[1:],
                 WHO="I" if author == "self" else "You", WHOL="I" if author == "self" else "you",
                 WHOP="My" if author == "self" else "Your")
        return MEETING_FRAMES[frame].format(**f)
    f["O"] = report["subject"] if report["subject"] else ""
    if t == "statement":
        vf = report["valid_from"]
        omit = vf == rd and _h(key, "omit") % 2 == 0
        since = "" if omit else " since " + day_phrase(vf, rd, key)
        f.update(P=report["value"], H=report["value"], SINCE=since)
        s = STATEMENT[attr][frame].format(**f)
        return s[0].upper() + s[1:]
    if t == "repeat":
        orig = by_id[report["origin"][2:]]
        # explicit day only: a relative day inside a repeated statement would be ambiguous
        # (relative to the repeating author's day or to the original speaker's day?)
        f.update(P=report["value"], H=report["value"], D=f"day {report['valid_from']}")
        cl = {k: v.format(**f) for k, v in REPEAT_CLAUSE[attr].items()}
        sn = _name(orig["source"], author)
        s = REPEAT_FRAMES[frame].format(SN=sn, SP=_poss(orig["source"], author), R=f"day {orig['report_day']}", **cl)
        return s[0].upper() + s[1:]
    target = by_id[report["target_report_id"]]
    sp = _poss(target["source"], author)
    if t == "correction":
        d = f"day {report['valid_from']}" if report["valid_from"] is not None else None
        f.update(P=report["value"], H=report["value"], D=d)
        cl = CORRECT_CLAUSE[(attr, sub)].format(**f)
        return CORRECT_FRAMES[frame].format(SP=sp, SPC=sp[0].upper() + sp[1:], R=f"day {target['report_day']}", CL=cl)
    cl = RETRACT_CLAUSE[attr].format(**f)
    return RETRACT_FRAMES[frame].format(SP=sp, SPC=sp[0].upper() + sp[1:], R=f"day {target['report_day']}", CL=cl)


def choose_frame(split: str, pair_seed: str, position: int) -> int:
    frames = SPLIT_FRAMES[split]
    return frames[_h(pair_seed, position, "frame") % len(frames)]


# ---------------------------------------------------------------- inverse parser (checks only)
_PAT = {
    "O": r"(?P<O>[Tt]he [a-z]+ [a-z]+)", "P": r"(?P<P>[A-Z][a-z]+ [A-Z][a-z]+)",
    "H": r"(?P<H>[A-Z][a-z]+ [A-Z][a-z]+)", "N": r"(?P<N>[A-Z][a-z]+ [A-Z][a-z]+)",
    "Q": r"(?P<Q>[A-Z][a-z]+ [A-Z][a-z]+)", "D": r"(?P<D>day \d+|yesterday|today)",
    "R": r"day (?P<R>\d+)", "SN": r"(?P<SN>[Yy]ou|I|[A-Z][a-z]+)",
    "SP": r"(?P<SP>my|your|[A-Z][a-z]+'s)", "SPC": r"(?P<SP>My|Your|[A-Z][a-z]+'s)",
    "DD": r"(?P<DD>on day \d+|yesterday|today)", "DDC": r"(?P<DD>On day \d+|Yesterday|Today)",
    "WHO": r"(?P<WHO>I|You)", "WHOL": r"(?P<WHO>I|you)", "WHOP": r"(?P<WHO>My|Your)",
}


def _regex(template: str, extra: dict) -> re.Pattern:
    out, pos, used = "", 0, set()
    for m in re.finditer(r"\{([A-Z]+)\}", template):
        out += re.escape(template[pos:m.start()])
        name = m.group(1)
        if name in extra:
            out += extra[name]
        else:
            if name in used:
                raise ValueError(f"placeholder {name} twice in one frame")
            out += _PAT[name]
            used.add(name)
        pos = m.end()
    return re.compile(out + re.escape(template[pos:]))


def _day(text: str, rd: int) -> int:
    t = text.lower().replace("on ", "")
    if t == "today":
        return rd
    if t == "yesterday":
        return rd - 1
    return int(t.split()[1])


def inverse(text: str, ntype: str, attr: str | None, frame: int, sub: str | None, author: str, rd: int) -> dict:
    """Exact inverse of render() for one frame; returns the meaning fields or raises."""
    if ntype == "meeting":
        m = _regex(MEETING_FRAMES[frame], {}).fullmatch(text)
        if not m:
            raise ValueError("no parse")
        return {"person": m["N"], "place": m["Q"], "day": _day(m["DD"], rd)}
    if ntype == "statement":
        t = STATEMENT[attr][frame]
        for since in ("", " since " + _PAT["D"]):
            m = _regex(t, {"SINCE": since}).fullmatch(text)
            if m:
                v = m.groupdict()
                return {"subject": v["O"][0].lower() + v["O"][1:], "value": v.get("P") or v.get("H"),
                        "valid_from": _day(v["D"], rd) if v.get("D") else "not stated"}
        raise ValueError("no parse")
    if ntype == "repeat":
        cl = {k: _regex(c, {}).pattern for k, c in REPEAT_CLAUSE[attr].items()}
        t = REPEAT_FRAMES[frame]
        m = _regex(t, cl).fullmatch(text)
        if not m:
            raise ValueError("no parse")
        v = m.groupdict()
        sn = v["SN"] if v.get("SN") else v["SP"]
        return {"subject": v["O"][0].lower() + v["O"][1:], "value": v.get("P") or v.get("H"),
                "valid_from": _day(v["D"], rd), "ref_source": _src(sn, author), "ref_day": int(v["R"])}
    if ntype == "correction":
        cl = _regex(CORRECT_CLAUSE[(attr, sub)], {}).pattern
        m = _regex(CORRECT_FRAMES[frame], {"CL": cl}).fullmatch(text)
        if not m:
            raise ValueError("no parse")
        v = m.groupdict()
        return {"subject": v["O"][0].lower() + v["O"][1:], "value": v.get("P") or v.get("H") or "keep",
                "valid_from": _day(v["D"], rd) if v.get("D") else "keep",
                "ref_source": _src(v["SP"], author), "ref_day": int(v["R"])}
    cl = _regex(RETRACT_CLAUSE[attr], {}).pattern
    m = _regex(RETRACT_FRAMES[frame], {"CL": cl}).fullmatch(text)
    if not m:
        raise ValueError("no parse")
    v = m.groupdict()
    return {"subject": v["O"][0].lower() + v["O"][1:], "ref_source": _src(v["SP"], author), "ref_day": int(v["R"])}


def _src(word: str, author: str) -> str:
    w = word.lower()
    if w in ("my", "i"):
        return author
    if w in ("your", "you"):
        return "self"
    return word[:-2] if word.endswith("'s") else word
