"""Round 4.0 report schema (docs/ROUND_4_0.md section 1).

This module is the ONLY code that the memory M (r40_memory.py) and the independent
reference R (r40_reference.py) share: field names, kinds, ranks and the check of a
single report's shape. No resolver logic lives here.
"""
from __future__ import annotations

REPORT_SCHEMA = "episodic_lab.r40_report.v1"
FIELDS = ("report_id", "report_day", "source", "rank", "origin", "subject", "attribute",
          "kind", "value", "valid_from", "target_report_id")
KINDS = ("assert", "correct", "retract")
RANKS = (1, 2, 3)                       # hearsay 1, trusted person 2, own observation 3
ANCHOR_PREFIX = "event:"                # anchor events: subject "event:<content>",
ANCHOR_ATTRIBUTE = "day"                # attribute "day", value = the day, valid_from 0
OPERATORS = ("current", "valid_at", "believed_at", "why_changed", "conflicts", "history",
             "before")


class ReportError(ValueError):
    pass


def check_report(r: dict) -> None:
    """Shape of one report; raises ReportError. Semantics (targets, ranks of the world,
    origins) are checked by the generator audit, not here."""
    if not isinstance(r, dict) or tuple(sorted(r)) != tuple(sorted(FIELDS)):
        raise ReportError(f"fields must be exactly {FIELDS}")
    rid = r["report_id"]
    if not (isinstance(rid, str) and len(rid) == 6 and rid[0] == "r" and rid[1:].isdigit()):
        raise ReportError(f"bad report_id {rid!r}")
    if type(r["report_day"]) is not int or r["report_day"] < 1:
        raise ReportError(f"{rid}: bad report_day")
    if type(r["rank"]) is not int or r["rank"] not in RANKS:
        raise ReportError(f"{rid}: bad rank")
    for f in ("source", "origin", "subject", "attribute"):
        if not isinstance(r[f], str) or not r[f]:
            raise ReportError(f"{rid}: bad {f}")
    kind = r["kind"]
    if kind not in KINDS:
        raise ReportError(f"{rid}: bad kind")
    vf, val, tgt = r["valid_from"], r["value"], r["target_report_id"]
    if vf is not None and (type(vf) is not int or vf < 0):
        raise ReportError(f"{rid}: bad valid_from")
    if val is not None and not (isinstance(val, str) or type(val) is int):
        raise ReportError(f"{rid}: bad value")
    if kind == "assert":
        if val is None or vf is None or tgt is not None:
            raise ReportError(f"{rid}: assert needs value and valid_from, no target")
    elif kind == "correct":
        if tgt is None or (val is None and vf is None):
            raise ReportError(f"{rid}: correct needs a target and a value or valid_from")
    else:
        if tgt is None or val is not None or vf is not None:
            raise ReportError(f"{rid}: retract needs a target only")
    if tgt is not None and not (isinstance(tgt, str) and len(tgt) == 6 and tgt[0] == "r"):
        raise ReportError(f"{rid}: bad target_report_id")


def order_key(r: dict) -> tuple:
    """The total order of reports: (report_day, report_id)."""
    return (r["report_day"], r["report_id"])
