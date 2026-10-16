"""Model arms of milestone 2 (protocol section 4): A0, A1 and the diagnostic O1.

Every answer is built from scratch: one fresh chat (system instruction + user message)
per question, no history, no cache across questions. The model is any object with
`generate(messages) -> str` and `weights_digest() -> str` (see models.py); tests use a
fake model, so the prompt logic is checked without PyTorch.

The three arms see exactly the same instruction (which names the public answer type of
the question) and question wording; they differ only in the story notes:
- A0 (no memory): no notes;
- A1 (all episodes in the prompt): every episode presented so far, in presentation order;
- O1 (oracle evidence, diagnostic only): the evaluator's target episodes of the question;
  for lures, confusable early episodes that each contain one pair of the lure's details
  (no empty context; but always three notes, so the note count can signal a lure). O1 is not a memory
  system; it measures whether the model can use given evidence, its evidence is passed by
  the runner and never stored, and its E6 values say nothing about retention.
A0 is, strictly, a missing-evidence control with requested abstention.
"""
from __future__ import annotations

import hashlib
import json

# The answer type is public (it is part of every question record), so naming the
# expected form is fair; examples use names that never occur in any world.
FORMAT = {
    "person": ("a person's full name", "Tom Hill"),
    "place": ("a place name", "Elm Court"),
    "object": ("an object name", "red door"),
    "day": ("a day number", "Day 3"),
    "choice": ("the letter A or the letter B", "A"),
}
NO_NOTES = "(no notes)"


def instruction(answer_type: str) -> str:
    form, example = FORMAT[answer_type]
    text = (f"You read story notes and answer one question about them. Answer with only "
            f"{form} (for example: {example}), nothing else.")
    if answer_type != "choice":
        text += (" If the notes do not contain the event the question asks about, answer "
                 "with the single word: none.")
    return text


def build_messages(question: str, notes: list[str], answer_type: str) -> list[dict]:
    body = "\n".join(notes) if notes else NO_NOTES
    return [{"role": "system", "content": instruction(answer_type)},
            {"role": "user", "content": f"Story notes:\n{body}\n\nQuestion: {question}"}]


class _ModelArm:
    DIGEST_COVERS = ("model",)
    # E1b declaration per encoded episode (class attributes, not memory state)
    E1B = {"internal_replays": 0, "optimizer_steps": 0, "store_writes": 0}

    def __init__(self, model):
        self.model = model
        self.notes: list[str] = []

    def state_digest(self) -> str:
        return hashlib.sha256((self.model.weights_digest() + json.dumps(self.notes)).encode()).hexdigest()

    def deep_digest(self) -> str:
        """Recomputes the weights hash from the tensors (slow; checked once per phase)."""
        return self.model.weights_digest(recompute=True)


class NoMemory(_ModelArm):
    ARM = "A0"
    EXPOSURE = "none"  # E1b: no episode is ever placed in a prompt

    def encode(self, text: str) -> None:
        pass

    def answer(self, text: str, answer_type: str) -> str:
        return self.model.generate(build_messages(text, [], answer_type))


class AllInPrompt(_ModelArm):
    ARM = "A1"
    EXPOSURE = "all_presented"  # E1b: every presented episode is in every later prompt
    E1B = {"internal_replays": 0, "optimizer_steps": 0, "store_writes": 1}  # one note each

    def encode(self, text: str) -> None:
        self.notes.append(text)

    def answer(self, text: str, answer_type: str) -> str:
        return self.model.generate(build_messages(text, list(self.notes), answer_type))


class OracleEvidence(_ModelArm):
    ARM = "O1"
    EXPOSURE = "evidence"  # E1b: exactly the evidence passed with each question

    def encode(self, text: str) -> None:
        pass

    def answer(self, text: str, answer_type: str) -> str:  # pragma: no cover
        raise RuntimeError("O1 answers only with evidence")

    def answer_with(self, text: str, evidence: list[str], answer_type: str) -> str:
        return self.model.generate(build_messages(text, list(evidence), answer_type))


ARMS = {"A0": NoMemory, "A1": AllInPrompt, "O1": OracleEvidence}
