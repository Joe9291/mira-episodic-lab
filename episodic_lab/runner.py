"""Run one system on one world pair under the protocol's encoding and test schedule.

Schedule: present the early episodes once each in presentation order, test with the
phase1 questions, present the follow-up episodes once each, test with the final
questions. The system sees only episode texts and question texts (E1a); the evaluator
alone holds the gold answers.

Frozen memory during tests: every answer must come from a fresh context (the adapter
builds each prompt from scratch). The runner checks this as far as it can see: before
and after every answer it compares the system's own digest of its memory (for large
state such as weights, attributes listed in DIGEST_COVERS) AND a fingerprint of every
other attribute of the system object. A system that changes either while answering is
rejected. State kept outside the system object (module globals, files) is not covered;
model adapters must not keep any (protocol section 3, code audit).
"""
from __future__ import annotations

import hashlib
import pickle
from typing import Protocol

from .score import score_world, summarise
from .world import episodes_of


class System(Protocol):
    def encode(self, text: str) -> None: ...
    def answer(self, text: str) -> str: ...
    def state_digest(self) -> str: ...


class StateChangedWhileAnswering(RuntimeError):
    pass


def fingerprint(system) -> str:
    """Digest of the system's own memory digest plus every attribute it does not cover."""
    covered = set(getattr(system, "DIGEST_COVERS", ()))
    rest = {k: v for k, v in sorted(vars(system).items()) if k not in covered}
    return hashlib.sha256(system.state_digest().encode() + pickle.dumps(rest, protocol=4)).hexdigest()


def run_world(system: System, world: dict, questions: dict) -> dict:
    episodes = episodes_of(world)
    presented = 0
    answers = {}
    for block, phase in (("early", "phase1"), ("followup", "final")):
        for e in episodes:
            if e.block == block:
                system.encode(e.text)
                presented += 1
        answers[phase] = {}
        for q in questions["public"][phase]:
            before = fingerprint(system)
            answers[phase][q["qid"]] = system.answer(q["text"])
            if fingerprint(system) != before:
                raise StateChangedWhileAnswering(q["qid"])
    gold, cands = questions["gold"], questions["candidates"]
    rows = (score_world(gold, cands, answers["phase1"], "phase1")
            + score_world(gold, cands, answers["final"], "final"))
    return {"seed": world["seed"], "overlap": world["overlap"], "episodes_presented": presented,
            "episodes_in_world": len(episodes), "rows": rows,
            "phase1": summarise([r for r in rows if r["phase"] == "phase1"]),
            "final": summarise([r for r in rows if r["phase"] == "final"])}


def retention(result: dict) -> dict:
    """E6 inputs: accuracy on the early-target items at phase1 and at final."""
    early = [r for r in result["rows"] if r["criterion"] in ("E2", "E4")]
    out = {}
    for phase in ("phase1", "final"):
        sub = [r for r in early if r["phase"] == phase]
        out[phase] = sum(r["correct"] for r in sub) / len(sub) if sub else float("nan")
    return out
