"""Model arms of milestone 2 (protocol section 4): A0, A1 and the diagnostic O1.

Every answer is built from scratch: one fresh chat (system instruction + user message)
per question, no history, no cache across questions. The model is any object with
`generate(messages) -> str` and `weights_digest() -> str` (see models.py); tests use a
fake model, so the prompt logic is checked without PyTorch.

The three arms see exactly the same instruction and question wording; they differ only
in the story notes:
- A0 (no memory): no notes;
- A1 (all episodes in the prompt): every episode presented so far, in presentation order;
- O1 (oracle evidence, diagnostic only): the evaluator's target episodes of the question
  (none for lures). O1 is not a memory system; it measures whether the model can use the
  right evidence at all, and its evidence is passed by the runner, never stored.
"""
from __future__ import annotations

import hashlib
import json

INSTRUCTION = ("You read story notes and answer a question about them. Answer with only "
               "the name, the place, the object, the day number, or the letter A or B. "
               "If the notes do not contain the event the question asks about, answer: none.")
NO_NOTES = "(no notes)"


def build_messages(question: str, notes: list[str]) -> list[dict]:
    body = "\n".join(notes) if notes else NO_NOTES
    return [{"role": "system", "content": INSTRUCTION},
            {"role": "user", "content": f"Story notes:\n{body}\n\nQuestion: {question}"}]


class _ModelArm:
    DIGEST_COVERS = ("model",)

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

    def encode(self, text: str) -> None:
        pass

    def answer(self, text: str) -> str:
        return self.model.generate(build_messages(text, []))


class AllInPrompt(_ModelArm):
    ARM = "A1"

    def encode(self, text: str) -> None:
        self.notes.append(text)

    def answer(self, text: str) -> str:
        return self.model.generate(build_messages(text, list(self.notes)))


class OracleEvidence(_ModelArm):
    ARM = "O1"

    def encode(self, text: str) -> None:
        pass

    def answer(self, text: str) -> str:  # pragma: no cover - O1 always gets evidence
        raise RuntimeError("O1 answers only with evidence")

    def answer_with(self, text: str, evidence: list[str]) -> str:
        return self.model.generate(build_messages(text, list(evidence)))


ARMS = {"A0": NoMemory, "A1": AllInPrompt, "O1": OracleEvidence}
