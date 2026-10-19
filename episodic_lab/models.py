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
    def __init__(self, slug: str, pins_path: str, max_new_tokens: int = 16, threads: int | None = None,
                 thinking: bool = False):
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
        if thinking and not slug.startswith("qwen3"):
            raise ValueError("thinking mode exists only for Qwen3")
        self.thinking = thinking
        self.template_kwargs = {"enable_thinking": thinking} if slug.startswith("qwen3") else {}
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

    def score_candidates(self, messages: list[dict], candidates: list[str]) -> list[float]:
        """Log-probability of each candidate as the COMPLETE answer (its tokens followed by
        the end-of-turn token), after the same chat prompt as `generate`. One forward
        pass per candidate; no state kept."""
        torch = self._torch
        ids = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                                 return_tensors="pt", **self.template_kwargs)
        out = []
        for cand in candidates:
            cid = self.tokenizer(cand, add_special_tokens=False)["input_ids"] + [self.tokenizer.eos_token_id]
            full = torch.cat([ids, torch.tensor([cid], dtype=ids.dtype)], dim=1)
            with torch.no_grad():
                logits = self.model(full, attention_mask=torch.ones_like(full)).logits[0]
            logp = torch.log_softmax(logits[ids.shape[1] - 1:-1].float(), dim=-1)
            out.append(float(sum(logp[i, t] for i, t in enumerate(cid))))
        self.stats["scored"] = self.stats.get("scored", 0) + len(candidates)
        return out

    def score_candidates_cached(self, messages: list[dict], candidates: list[str]) -> list[float]:
        """The same scores as `score_candidates`, with the prompt's key/value cache computed
        once and cropped back to the prompt after every candidate (round 3.5). Agreement
        with the uncached scores is checked on a development slice."""
        torch = self._torch
        ids = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                                 return_tensors="pt", **self.template_kwargs)
        plen = ids.shape[1]
        with torch.no_grad():
            first = self.model(ids, attention_mask=torch.ones_like(ids), use_cache=True)
        cache = first.past_key_values
        last = torch.log_softmax(first.logits[0, -1].float(), dim=-1)
        out = []
        for cand in candidates:
            cid = self.tokenizer(cand, add_special_tokens=False)["input_ids"] + [self.tokenizer.eos_token_id]
            total = float(last[cid[0]])
            if len(cid) > 1:
                step = torch.tensor([cid[:-1]], dtype=ids.dtype)
                with torch.no_grad():
                    o = self.model(step, past_key_values=cache, use_cache=True,
                                   attention_mask=torch.ones((1, plen + len(cid) - 1), dtype=ids.dtype))
                logp = torch.log_softmax(o.logits[0].float(), dim=-1)
                total += float(sum(logp[i, t] for i, t in enumerate(cid[1:])))
                cache.crop(plen)
            out.append(total)
        self.stats["scored"] = self.stats.get("scored", 0) + len(candidates)
        self.stats["prompts"] = self.stats.get("prompts", 0) + 1
        return out

    def score_candidates_prefixed(self, messages: list[dict], candidates: list[str]) -> list[float]:
        """Like `score_candidates_cached`, and in addition the key/value cache of everything
        before the last chat turn (system prompt and worked examples, identical for every
        note of a slot) is computed once and reused across calls; used only when that
        prefix is an exact token prefix of the full prompt, otherwise falls back."""
        torch = self._torch
        ids = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                                 return_tensors="pt", **self.template_kwargs)
        # the reusable head: the longest common token prefix of the full prompt and the same
        # conversation with an empty last turn (round 3.6: rendering messages[:-1] alone is not a
        # prefix for chat templates that format the final assistant turn differently, e.g.
        # Qwen3's think tags, which made every call fall back to the uncached path)
        probe = self.tokenizer.apply_chat_template(messages[:-1] + [dict(messages[-1], content="")],
                                                   add_generation_prompt=True, return_tensors="pt",
                                                   **self.template_kwargs)
        n = min(ids.shape[1], probe.shape[1])
        hl = int((ids[0, :n] != probe[0, :n]).nonzero()[0, 0]) if not torch.equal(ids[0, :n], probe[0, :n]) else n
        if len(messages) < 2 or hl < 1 or hl >= ids.shape[1]:
            return self.score_candidates_cached(messages, candidates)
        head = ids[:, :hl]
        key = tuple(head[0].tolist())
        store = self.__dict__.setdefault("_prefix_caches", {})   # one per slot prompt
        if key not in store:
            with torch.no_grad():
                store[key] = self.model(head, attention_mask=torch.ones_like(head), use_cache=True).past_key_values
        cache = store[key]
        cache.crop(hl)
        plen = ids.shape[1]
        rest = ids[:, hl:]
        with torch.no_grad():
            first = self.model(rest, past_key_values=cache, use_cache=True,
                               attention_mask=torch.ones((1, plen), dtype=ids.dtype))
        last = torch.log_softmax(first.logits[0, -1].float(), dim=-1)
        out = []
        for cand in candidates:
            cid = self.tokenizer(cand, add_special_tokens=False)["input_ids"] + [self.tokenizer.eos_token_id]
            total = float(last[cid[0]])
            if len(cid) > 1:
                step = torch.tensor([cid[:-1]], dtype=ids.dtype)
                with torch.no_grad():
                    o = self.model(step, past_key_values=cache, use_cache=True,
                                   attention_mask=torch.ones((1, plen + len(cid) - 1), dtype=ids.dtype))
                logp = torch.log_softmax(o.logits[0].float(), dim=-1)
                total += float(sum(logp[i, t] for i, t in enumerate(cid[1:])))
                cache.crop(plen)
            out.append(total)
        cache.crop(hl)
        self.stats["scored"] = self.stats.get("scored", 0) + len(candidates)
        self.stats["prompts"] = self.stats.get("prompts", 0) + 1
        return out

    def generate_reasoning(self, messages: list[dict], seed: int) -> dict:
        """Qwen3 thinking mode with the sampling settings recommended for it (temperature
        0.6, top-p 0.95, top-k 20), seeded per call so every answer is reproducible. The
        answer is the text after the last </think> token; without it the reply was cut
        off by the token limit and the answer is empty."""
        torch = self._torch
        ids = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True,
                                                 return_tensors="pt", **self.template_kwargs)
        torch.manual_seed(seed)
        with torch.no_grad():
            out = self.model.generate(ids, attention_mask=torch.ones_like(ids),
                                      max_new_tokens=self.max_new_tokens, do_sample=True,
                                      temperature=0.6, top_p=0.95, top_k=20,
                                      pad_token_id=self.tokenizer.eos_token_id)
        new = out[0, ids.shape[1]:].tolist()
        end = self.tokenizer.convert_tokens_to_ids("</think>")
        finished = end in new
        answer_ids = new[len(new) - new[::-1].index(end):] if finished else []
        self.stats["calls"] += 1
        self.stats["prompt_tokens"] += int(ids.shape[1])
        self.stats["new_tokens"] += len(new)
        return {"answer": self.tokenizer.decode(answer_ids, skip_special_tokens=True).strip(),
                "new_tokens": len(new), "finished": finished}

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
