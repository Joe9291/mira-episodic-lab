#!/usr/bin/env python3
"""Round 4.2 option B (Astra, reviews/2026-10-23_r42devresult_astra.txt): merge the p7
label re-encode (slots attribute, change) with the p6 encodings of all other slots.

Checks before any score is reused (every check must hold for every note, else the merge
fails and writes nothing):
- same model slug, same weight digest, same model pins file, same candidate version;
- the p6 files cover every reused slot and the p7 files exactly the re-encoded slots, for
  the same set of note keys (stable keys: run_round42_encode.note_key);
- for every reused slot the chat messages under p6 and p7 are identical, and the
  recorded candidate surfaces (with canonical values, in order) equal the candidates the
  current code builds for that note;
- for the re-encoded slots the recorded candidates equal the current candidates as well;
- both encodings were scored by the same scoring configuration (recorded scorer).
Output: one merged file per model and split, prompt version "p7", with the SHA-256 of
every input file and the p7 label priors.

usage: merge_round42.py --base P6.json ... --labels P7.json ... --out MERGED.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from episodic_lab.cands42 import SLOTS, candidates  # noqa: E402
from episodic_lab.encoder42 import LABEL_REENCODED, candidate_text, messages  # noqa: E402


def read(paths):
    files, enc, index = [], {}, {}
    for p in paths:
        raw = Path(p).read_bytes()
        d = json.loads(raw)
        if d.get("status") != "OK":
            raise SystemExit(f"{p}: status {d.get('status')}")
        files.append({"path": str(p), "sha256": hashlib.sha256(raw).hexdigest(), "model": d["model"],
                      "split": d["split"], "chunk": d["chunk"], "chunks": d["chunks"],
                      "prompt_version": d["prompt_version"], "candidate_version": d["candidate_version"],
                      "weights_sha256": d["weights_sha256"], "pins_sha256": d["provenance"]["pins_sha256"],
                      "code_commit": d["provenance"]["code_commit"], "slots": d.get("slots"),
                      "priors": d.get("priors")})
        overlap = set(enc) & set(d["encodings"])
        if overlap:                                   # Astra (closure review): never overwrite silently
            raise SystemExit(f"merge refused: {p} repeats {len(overlap)} note keys of an earlier input file")
        enc.update(d["encodings"])
        index.update(d["index"])
    return files, enc, index


def one(values, what):
    vals = {v for v in values}
    if len(vals) != 1:
        raise SystemExit(f"merge refused: {what} differs: {sorted(map(str, vals))}")
    return vals.pop()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", nargs="+", required=True)
    ap.add_argument("--labels", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    bf, benc, bidx = read(a.base)
    lf, lenc, lidx = read(a.labels)
    slug = one([f["model"].split("+")[0] for f in bf + lf], "model")
    split = one([f["split"] for f in bf + lf], "split")
    one([f["weights_sha256"] for f in bf + lf], "weight digest")
    one([f["pins_sha256"] for f in bf + lf], "pins file")
    cand_version = one([f["candidate_version"] for f in bf + lf], "candidate version")
    if one([f["prompt_version"] for f in bf], "base prompt") != "p6" or one([f["prompt_version"] for f in lf], "label prompt") != "p7":
        raise SystemExit("merge refused: base must be p6, labels p7")
    if one([f["slots"] for f in bf], "base slots") != "all":
        raise SystemExit("merge refused: base files must cover all slots")
    if sorted(one([f["slots"] for f in lf], "label slots").split(",")) != sorted(LABEL_REENCODED):
        raise SystemExit("merge refused: label files must cover exactly " + ",".join(LABEL_REENCODED))
    if set(benc) != set(lenc):
        raise SystemExit(f"merge refused: note keys differ ({len(benc)} base, {len(lenc)} labels)")
    scorer_src = {}
    for c in sorted({f["code_commit"] for f in bf + lf}):     # the scoring code of every input run
        try:
            src = subprocess.run(["git", "-C", str(ROOT), "show", f"{c}:episodic_lab/models.py"], check=True,
                                 capture_output=True).stdout
        except subprocess.CalledProcessError:
            raise SystemExit(f"merge refused: code commit {c} not available locally (git fetch)")
        scorer_src[c] = hashlib.sha256(src).hexdigest()
    one(scorer_src.values(), "scoring code (episodic_lab/models.py)")
    reused = [s for s in SLOTS if s not in LABEL_REENCODED]
    merged = {}
    for k in sorted(benc):
        if bidx[k] != lidx[k]:
            raise SystemExit(f"merge refused: note {k} has a different header / text / context")
        n = bidx[k]
        full = candidate_text(n["header"], n["text"], "p7")
        if full != candidate_text(n["header"], n["text"], "p6"):
            raise SystemExit(f"merge refused: candidate text differs for {k}")
        e = {}
        for s in reused:
            if messages(s, n["header"], n["text"], "p6") != messages(s, n["header"], n["text"], "p7"):
                raise SystemExit(f"merge refused: messages of slot {s} differ for {k}")
            want = [[x, c] for x, c in candidates(s, full, n["ctx"])]
            got = [[x, c] for x, c, _ in benc[k][s]]
            if json.loads(json.dumps(want)) != got:
                raise SystemExit(f"merge refused: candidates of slot {s} differ for {k}")
            e[s] = benc[k][s]
        for s in LABEL_REENCODED:
            want = [[x, c] for x, c in candidates(s, full, n["ctx"])]
            if json.loads(json.dumps(want)) != [[x, c] for x, c, _ in lenc[k][s]]:
                raise SystemExit(f"merge refused: candidates of slot {s} differ for {k} (labels)")
            e[s] = lenc[k][s]
        merged[k] = e
    # the label priors are a report-only quantity (variant B); they differ between runners in
    # the 4th-5th decimal (CPU floating point), so they are recorded, not required equal: the
    # merged file carries those of the first label file and the largest difference
    pri_all = [f["priors"] for f in sorted(lf, key=lambda f: f["chunk"])]
    prior_spread = max(abs(p[s][l] - pri_all[0][s][l]) for p in pri_all for s in p for l in p[s])
    out = {"schema": "episodic_lab.round42_encode.v1", "status": "OK", "phase": "merged",
           "model": f"{slug}+p7", "split": split, "chunk": 0, "chunks": 1, "prompt_version": "p7",
           "candidate_version": cand_version, "slots": "all", "weights_sha256": bf[0]["weights_sha256"],
           "priors": pri_all[0], "prior_spread_between_runners": prior_spread, "notes": len(merged), "encodings": merged, "index": bidx,
           "merged_from": {"base_p6": [{k: f[k] for k in f if k != "priors"} for f in bf],
                           "labels_p7": lf,
                           "reused_slots": reused, "reencoded_slots": list(LABEL_REENCODED),
                           "scoring_code_sha256": scorer_src},
           "provenance": {"code_commit": "merge", "pins_sha256": bf[0]["pins_sha256"]}}
    Path(a.out).write_text(json.dumps(out, sort_keys=True) + "\n")
    print(f"merged {slug} {split}: {len(merged)} notes, reused {len(reused)} slots, re-encoded {list(LABEL_REENCODED)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
