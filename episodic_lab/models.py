"""Pinned model loading and greedy generation (protocol section 5). Needs PyTorch.

Loading refuses any byte that differs from config/model_pins.json: the downloaded file
set must equal the pinned set and every file must have its pinned size and SHA-256.
Generation is greedy, one fresh chat per call (chat template of the model; Qwen3 with
thinking switched off), no cache kept between calls.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

PATTERNS = ["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja"]


class PinError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_snapshot(path: Path, spec: dict) -> None:
    found = {p.relative_to(path).as_posix(): p for p in path.rglob("*") if p.is_file()}
    if set(found) != set(spec["files"]):
        raise PinError(f"file set differs: {sorted(set(found) ^ set(spec['files']))}")
    for rel, meta in spec["files"].items():
        if found[rel].stat().st_size != meta["size"] or _sha256_file(found[rel]) != meta["sha256"]:
            raise PinError(f"pinned bytes differ: {rel}")


class PinnedModel:
    def __init__(self, slug: str, pins_path: str, max_new_tokens: int = 16, threads: int | None = None):
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForCausalLM, AutoTokenizer

        spec = json.loads(Path(pins_path).read_text())["models"][slug]
        path = Path(snapshot_download(spec["repo"], revision=spec["revision"], allow_patterns=PATTERNS))
        verify_snapshot(path, spec)
        torch.set_num_threads(threads or os.cpu_count() or 1)
        torch.manual_seed(0)
        self._torch = torch
        self.slug, self.repo, self.revision = slug, spec["repo"], spec["revision"]
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float32,
                                                          local_files_only=True)
        self.model.eval()
        self.model.requires_grad_(False)
        self.max_new_tokens = max_new_tokens
        self.template_kwargs = {"enable_thinking": False} if slug.startswith("qwen3") else {}
        # telemetry, not memory: totals plus one entry per call (prompt length, answer
        # length, and whether the answer was cut off by the token limit)
        self.stats = {"calls": 0, "prompt_tokens": 0, "new_tokens": 0, "truncated": 0}
        self.call_log: list[dict] = []
        self._digest = self._weights_hash()

    def _weights_hash(self) -> str:
        h = hashlib.sha256()
        for name, tensor in sorted(self.model.state_dict().items()):
            h.update(name.encode())
            h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
        return h.hexdigest()

    def weights_digest(self, recompute: bool = False) -> str:
        return self._weights_hash() if recompute else self._digest

    def count_tokens(self, text: str) -> int:
        """Tokens of a text on its own (E1b: tokens processed per episode)."""
        return len(self.tokenizer(text, add_special_tokens=False)["input_ids"])

    def generate(self, messages: list[dict]) -> str:
        torch = self._torch
        ids = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                                 return_tensors="pt", **self.template_kwargs)
        with torch.no_grad():
            out = self.model.generate(ids, attention_mask=torch.ones_like(ids),
                                      max_new_tokens=self.max_new_tokens, do_sample=False,
                                      pad_token_id=self.tokenizer.eos_token_id)
        new = out[0, ids.shape[1]:]
        self.stats["calls"] += 1
        self.stats["prompt_tokens"] += int(ids.shape[1])
        self.stats["new_tokens"] += int(new.shape[0])
        cut = int(new.shape[0]) >= self.max_new_tokens and int(new[-1]) != self.tokenizer.eos_token_id
        self.stats["truncated"] += int(cut)
        self.call_log.append({"prompt_tokens": int(ids.shape[1]), "new_tokens": int(new.shape[0]),
                              "truncated": bool(cut)})
        return self.tokenizer.decode(new, skip_special_tokens=True).strip()
