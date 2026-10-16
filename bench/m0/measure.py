"""Milestone 0: feasibility measurement on the GitHub runner (protocol section 9).

For one model: download, load time, memory, prefill and generation speed, and the time
of LoRA update steps on one episode-sized text. Every outcome, including a failure with
its traceback, is written to the result JSON, so the run itself is the evidence.
No evaluation data is involved.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import time
import traceback

EPISODE = ("On day 7, Varo Tellin repaired the copper lantern at Mossgate Mill together "
           "with Odile Quist. ") * 4  # about 100 tokens, the size of one episode
PROMPT = EPISODE * 2 + "Question: Who repaired the copper lantern? Answer:"


def peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def measure(model_id: str, threads: int, lora_steps: int) -> dict:
    import torch
    from huggingface_hub import model_info, snapshot_download
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(threads)
    torch.manual_seed(0)
    out: dict = {"model_id": model_id, "torch_threads": threads}

    t0 = time.perf_counter()
    info = model_info(model_id)
    out["resolved_revision"] = info.sha
    path = snapshot_download(model_id, revision=info.sha,
                             allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model",
                                             "*.jinja"])
    out["download_s"] = round(time.perf_counter() - t0, 2)
    out["files_mb"] = round(sum(os.path.getsize(os.path.join(dp, f))
                                for dp, _, fs in os.walk(path) for f in fs) / 2**20, 1)

    t0 = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float32)
    model.eval()
    out["load_s"] = round(time.perf_counter() - t0, 2)
    out["parameters_m"] = round(sum(p.numel() for p in model.parameters()) / 1e6, 1)
    out["rss_after_load_mb"] = round(peak_rss_mb(), 1)

    ids = tok(PROMPT, return_tensors="pt")
    out["prompt_tokens"] = int(ids["input_ids"].shape[1])
    with torch.no_grad():
        model(**ids)  # warm-up
        t0 = time.perf_counter()
        for _ in range(3):
            model(**ids)
        prefill = (time.perf_counter() - t0) / 3
    out["prefill_tokens_per_s"] = round(out["prompt_tokens"] / prefill, 1)

    new_tokens = 32
    with torch.no_grad():
        t0 = time.perf_counter()
        gen = model.generate(**ids, max_new_tokens=new_tokens, min_new_tokens=new_tokens,
                             do_sample=False, pad_token_id=tok.eos_token_id)
        gen_s = time.perf_counter() - t0
    produced = int(gen.shape[1] - ids["input_ids"].shape[1])
    out["generate_tokens_per_s"] = round(produced / gen_s, 2)
    out["generate_sample"] = tok.decode(gen[0, ids["input_ids"].shape[1]:],
                                        skip_special_tokens=True)[:200]

    # LoRA update steps on one episode (protocol P1): attention projections only.
    names = {n.split(".")[-1] for n, _ in model.named_modules()}
    targets = [t for t in ("q_proj", "v_proj") if t in names]
    out["lora_targets"] = targets
    lora = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0,
                                            target_modules=targets, task_type="CAUSAL_LM"))
    lora.train()
    out["lora_trainable"] = sum(p.numel() for p in lora.parameters() if p.requires_grad)
    batch = tok(EPISODE, return_tensors="pt")
    out["episode_tokens"] = int(batch["input_ids"].shape[1])
    optim = torch.optim.AdamW([p for p in lora.parameters() if p.requires_grad], lr=1e-3)
    times, losses = [], []
    for _ in range(lora_steps):
        t0 = time.perf_counter()
        loss = lora(**batch, labels=batch["input_ids"]).loss
        loss.backward()
        optim.step()
        optim.zero_grad()
        times.append(time.perf_counter() - t0)
        losses.append(round(float(loss), 4))
    out["lora_step_s"] = [round(t, 3) for t in times]
    out["lora_step_s_median"] = round(sorted(times)[len(times) // 2], 3)
    out["lora_losses"] = losses
    out["peak_rss_mb"] = round(peak_rss_mb(), 1)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--threads", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--lora-steps", type=int, default=6)
    args = parser.parse_args()
    result = {"schema": "episodic_lab.m0.v1", "python": platform.python_version(),
              "cpu_count": os.cpu_count(), "machine": platform.machine()}
    t0 = time.perf_counter()
    try:
        result.update(measure(args.model, args.threads, args.lora_steps))
        result["status"] = "OK"
    except Exception:
        result["status"] = "ERROR"
        result["model_id"] = args.model
        result["traceback"] = traceback.format_exc()[-4000:]
    result["total_s"] = round(time.perf_counter() - t0, 2)
    try:
        import torch, transformers, peft
        result["versions"] = {"torch": torch.__version__,
                              "transformers": transformers.__version__,
                              "peft": peft.__version__}
    except Exception:
        pass
    with open(args.out, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
