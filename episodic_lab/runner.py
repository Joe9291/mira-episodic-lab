"""Run one system on one world under the protocol's encoding and test schedule.

Schedule: present the early episodes once each in presentation order, test with the
phase1 questions, present the follow-up episodes once each, test with the final
questions. The system sees only episode texts and question texts (E1a); the evaluator
alone holds the gold answers.
"""
from __future__ import annotations

from typing import Protocol

from .questions import build_questions
from .score import score_world, summarise
from .world import episodes_of, generate_world


class System(Protocol):
    def encode(self, text: str) -> None: ...
    def answer(self, text: str) -> str: ...


def run_world(system: System, seed: str, overlap: str = "high", **world_args) -> dict:
    world = generate_world(seed, overlap=overlap, **world_args)
    qs = build_questions(world)
    episodes = episodes_of(world)
    presented = 0
    answers = {}
    for block, phase in (("early", "phase1"), ("followup", "final")):
        for e in episodes:
            if e.block == block:
                system.encode(e.text)
                presented += 1
        answers[phase] = {q["qid"]: system.answer(q["text"]) for q in qs["public"][phase]}
    rows = (score_world(qs["gold"], qs["candidates"], answers["phase1"], "phase1")
            + score_world(qs["gold"], qs["candidates"], answers["final"], "final"))
    return {"seed": seed, "overlap": overlap, "episodes_presented": presented,
            "episodes_in_world": len(episodes), "rows": rows,
            "phase1": summarise([r for r in rows if r["phase"] == "phase1"]),
            "final": summarise([r for r in rows if r["phase"] == "final"])}
