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
model adapters must not keep any (protocol section 3, code audit). Systems with large
state (model weights) also offer `deep_digest()`, recomputed from the data itself at the
start and after every test phase.

Diagnostic oracle arms (O1) offer `answer_with(question, evidence)`; the runner passes
evaluator knowledge that the arm never stores: for positive items the texts of the
question's target episodes, for E5 lures confusable early episodes (for every pair of
the lure's cue details, the first early episode in presentation order that contains that
pair; deduplicated, in presentation order). A lure is therefore never answered from an
empty context; rejecting it needs the binding of the details.

E1b (processing per episode): every encoded episode is read once by `encode`. How often
an episode is placed in an answering prompt follows from the arm's declared EXPOSURE
("none", "all_presented", "evidence") and is counted here by the runner for every
question, so the count is part of the result and not of the arm's state.

`on_phase(phase, answers)` (optional) is called after each test phase with the raw
answers so far, so a caller can keep partial results if a later phase fails.
"""
from __future__ import annotations

import hashlib
import pickle
from typing import Protocol

from .questions import matching
from .score import score_world, summarise
from .world import episodes_of


class System(Protocol):
    def encode(self, text: str) -> None: ...
    def answer(self, text: str, answer_type: str) -> str: ...
    def state_digest(self) -> str: ...


class StateChangedWhileAnswering(RuntimeError):
    pass


def fingerprint(system) -> str:
    """Digest of the system's own memory digest plus every attribute it does not cover."""
    covered = set(getattr(system, "DIGEST_COVERS", ()))
    rest = {k: v for k, v in sorted(vars(system).items()) if k not in covered}
    return hashlib.sha256(system.state_digest().encode() + pickle.dumps(rest, protocol=4)).hexdigest()


def oracle_evidence(item: dict, episodes: list) -> list[str]:
    """Episode ids passed to O1: targets for positive items, confusable ones for lures."""
    order = {e.episode_id: e.position for e in episodes}
    if item["criterion"] != "E5":
        return sorted(item["targets"], key=order.get)
    early = sorted((e for e in episodes if e.block == "early"), key=lambda e: e.position)
    keys = sorted(item["cue"])
    chosen = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            hits = matching(early, **{a: item["cue"][a], b: item["cue"][b]})
            if not hits:
                raise ValueError(f"lure pair {a},{b} has no early episode")
            if hits[0].episode_id not in chosen:
                chosen.append(hits[0].episode_id)
    return sorted(chosen, key=order.get)


EXPOSURES = ("none", "all_presented", "evidence")


def run_world(system: System, world: dict, questions: dict, on_phase=None) -> dict:
    episodes = episodes_of(world)
    texts = {e.episode_id: e.text for e in episodes}
    oracle = hasattr(system, "answer_with")
    exposure = getattr(system, "EXPOSURE", None)
    if exposure is not None and exposure not in EXPOSURES:
        raise ValueError(f"unknown EXPOSURE {exposure!r}")
    if oracle and exposure != "evidence":
        raise ValueError("oracle arms must declare EXPOSURE = 'evidence'")
    deep = getattr(system, "deep_digest", None)
    deep_start = deep() if deep else None
    presented = []
    in_prompt = {e.episode_id: 0 for e in episodes}
    encoded = {e.episode_id: 0 for e in episodes}
    asked = []
    answers = {}
    for block, phase in (("early", "phase1"), ("followup", "final")):
        for e in episodes:
            if e.block == block:
                system.encode(e.text)
                presented.append(e.episode_id)
                encoded[e.episode_id] += 1
        answers[phase] = {}
        for q in questions["public"][phase]:
            before = fingerprint(system)
            if oracle:
                evidence = oracle_evidence(questions["gold"][q["qid"]], episodes)
                reply = system.answer_with(q["text"], [texts[t] for t in evidence],
                                           q["answer_type"])
                shown = evidence
            else:
                reply = system.answer(q["text"], q["answer_type"])
                shown = presented if exposure == "all_presented" else []
            for t in shown:
                in_prompt[t] += 1
            answers[phase][q["qid"]] = reply
            asked.append([phase, q["qid"]])
            if fingerprint(system) != before:
                raise StateChangedWhileAnswering(q["qid"])
        if deep and deep() != deep_start:
            raise StateChangedWhileAnswering(f"weights changed during {phase}")
        if on_phase:
            on_phase(phase, dict(answers[phase]))
    gold, cands = questions["gold"], questions["candidates"]
    rows = (score_world(gold, cands, answers["phase1"], "phase1")
            + score_world(gold, cands, answers["final"], "final"))
    return {"seed": world["seed"], "overlap": world["overlap"],
            "episodes_presented": len(presented), "oracle": oracle,
            "episodes_in_world": len(episodes), "rows": rows, "asked": asked,
            "processing": {"exposure": exposure, "encode_reads": encoded,
                           "declared_per_episode": getattr(system, "E1B", None),
                           "prompt_inclusions": in_prompt if exposure else None},
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
