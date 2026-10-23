#!/usr/bin/env python3
"""Round 4.2 collector (encode phases): checks that every planned cell delivered an OK
output with the planned identity and writes a short summary; the analysis of the
encodings (decisions, calibration, arms G / E, cause analysis) is model-free and runs
separately (bench/m3/analyse_round42.py).

usage: collect_round42.py REQUEST DIR
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    req = json.loads(Path(sys.argv[1]).read_text())
    dest = Path(sys.argv[2])
    if req["phase"] in ("timing", "probe", "prior"):
        cells = [(m, "dev", 0, 1) for m in req["models"]]
    elif req.get("cells"):
        cells = [(m, s, c, req["chunks"]) for m, s, c in req["cells"]]
    else:
        cells = [(m, s, c, req["chunks"]) for m in req["models"] for s in req["splits"] for c in range(req["chunks"])]
    lines, ok = [f"# Round 4.2 encode ({req['phase']})", ""], True
    for m, s, c, n in cells:
        f = dest / f"r42_{req['phase']}_{m}_{s}_{c}.json"
        if not f.exists():
            lines.append(f"- {m} {s} {c}/{n}: MISSING")
            ok = False
            continue
        d = json.loads(f.read_text())
        good = d.get("status") == "OK" and d.get("model") == m and d.get("split") == s and d.get("chunk") == c
        secs = sorted(d.get("seconds", {}).values())
        lines.append(f"- {m} {s} {c}/{n}: {d.get('status')} notes {d.get('notes')} "
                     f"median {secs[len(secs) // 2] if secs else '-'} s, max {secs[-1] if secs else '-'} s, "
                     f"load {d.get('load_seconds')} s, cache check {d.get('cache_check', {}).get('ok')}"
                     + ("" if good else f" ERROR {d.get('error')}"))
        ok &= good
    (dest / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    (dest / "VERDICT").write_text(("COMPLETE" if ok else "INCOMPLETE") + "\n")
    print("COMPLETE" if ok else "INCOMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
