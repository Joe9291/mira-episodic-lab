"""Run one system on one world pair under the protocol's encoding and test schedule.

Schedule: present the early episodes once each in presentation order, test with the
phase1 questions, present the follow-up episodes once each, test with the final
questions. The system sees only episode texts and question texts (E1a); the evaluator
alone holds the gold answers.

Frozen memory during tests: every answer is given from a fresh context, and the system's
memory state digest must be identical before and after each answer, so questions can
never become memory input (protocol section 3). A system that changes its state while
answering is rejected.
"""
from __future__ import annotations

from typing import Protocol

from .score import score_world, summarise
from .world import episodes_of


class System(Protocol):
    def encode(self, text: str) -> None: ...
    def answer(self, text: str) -> str: ...
    def state_digest(self) -> str: ...


class StateChangedWhileAnswering(RuntimeError):
    pass


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
            before = system.state_digest()
            answers[phase][q["qid"]] = system.answer(q["text"])
            if system.state_digest() != before:
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
