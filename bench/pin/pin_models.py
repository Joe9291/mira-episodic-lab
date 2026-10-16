"""Milestone 2 pinning step (protocol section 5).

Downloads each requested model at its exact revision (only the file types a model needs)
and records licence, revision, and size and SHA-256 of every file. The output is the pin
file the pilot verifies against; it contains hashes only, no model data.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import traceback
from pathlib import Path

PATTERNS = ["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pin(repo: str, revision: str) -> dict:
    from huggingface_hub import model_info, snapshot_download
    info = model_info(repo, revision=revision)
    if info.sha != revision:
        raise RuntimeError(f"revision mismatch: asked {revision}, got {info.sha}")
    licence = getattr(getattr(info, "card_data", None), "license", None)
    path = Path(snapshot_download(repo, revision=revision, allow_patterns=PATTERNS))
    files = {}
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = file.relative_to(path).as_posix()
        files[rel] = {"size": file.stat().st_size, "sha256": sha256_file(file)}
    if not any(name.endswith(".safetensors") for name in files):
        raise RuntimeError("no safetensors weights")
    return {"repo": repo, "revision": revision, "license": licence, "files": files}


def main(request_path: str, out_path: str) -> int:
    request = json.loads(Path(request_path).read_text())
    result = {"schema": "episodic_lab.model_pins.v1", "models": {}, "errors": {}}
    for slug, spec in request["models"].items():
        try:
            result["models"][slug] = pin(spec["repo"], spec["revision"])
        except Exception:
            result["errors"][slug] = traceback.format_exc()[-2000:]
    Path(out_path).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: len(v["files"]) for k, v in result["models"].items()}), result["errors"].keys())
    return 0 if not result["errors"] and len(result["models"]) == len(request["models"]) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
