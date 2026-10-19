"""Round 3.5b mutation proof for decoder d3 (Astra's review of d3, point 4).

Protocol:
- no project bytecode at the start (every __pycache__ under the repository removed, checked);
- every test run is a FRESH process with -B, PYTHONDONTWRITEBYTECODE=1 and its own new,
  empty PYTHONPYCACHEPREFIX directory, so no compiled file of an earlier run can be read;
- the freeze-binding test is EXCLUDED (any code change breaks the hash binding, which is not
  a substantive kill); a mutant counts as killed only if at least one substantive test FAILS
  with an AssertionError (unittest "FAIL"); an ERROR (import, exception) alone does not count;
- the unmutated baseline must pass under the same protocol, before and after;
- after each mutant the file is restored and its SHA-256 compared with the original; at the
  end the production files must match the proposed freeze (bench/m3/freeze35.py check) and
  no __pycache__ may exist in the repository.

  python3 bench/m3/mutation35b.py config/round35b_reserve_proposal.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED = "test_freeze_binding_covers_the_import_closure"
MUTANTS = [
    ("encoder35", "d2: provisional action instead of the decided one",
     'act["value"] if act["status"] != "unknown" else None', 'max(view(encoding["action"], mode), key=lambda x: x[2])[1]'),
    ("encoder35", "d2: non-maximal pair score", "if a not in ja or s > ja[a]:", "if True:"),
    ("encoder35", "d2: actor != receiver dropped", "return (a != r and not", "return (not"),
    ("encoder35", "d2: wrong origin label", 'origin = "text" if len', 'origin = "schema" if len'),
    ("encoder35", "F2 without an accepted action",
     'and not (gave_receiver_self and accepted_action == "gave" and r != SELF_VALUE))',
     'and not (gave_receiver_self and r != SELF_VALUE))'),
    ("encoder35", "F2 off", 'and not (gave_receiver_self and accepted_action == "gave" and r != SELF_VALUE))', ')'),
    ("encoder35", "F1 drops none", "if x[1] == NONE or len(str(x[1]).split()) == 2]", "if len(str(x[1]).split()) == 2]"),
    ("encoder35", "F1 admits >= 2 tokens", "len(str(x[1]).split()) == 2]", "len(str(x[1]).split()) >= 2]"),
    ("encoder35", "F1 off", 'if slot == "object" and DECODING.get("object_two_tokens"):', "if False:"),
    ("analysis35", "B2 without the single-value precision",
     "len(singles) >= MIN_ACCEPTED and sprec >= PRECISION", "len(singles) >= MIN_ACCEPTED"),
    ("analysis35", "calibration ignores the earlier slots' thresholds",
     'det[s] = decide_slot(enc, s, det, out[s]["tau"], mode)', "det[s] = decide_slot(enc, s, det, 0.0, mode)"),
]


def pycaches() -> list[str]:
    return sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("__pycache__"))


def test_ids() -> list[str]:
    code = ("import sys, unittest; sys.path[:0] = ['.']; s = unittest.defaultTestLoader.loadTestsFromName('tests.test_round35'); "
            "f = lambda t: [x for y in t for x in f(y)] if isinstance(t, unittest.TestSuite) else [t.id()]; print('\\n'.join(f(s)))")
    return [t for t in run([sys.executable, "-B", "-c", code]).stdout.split() if EXCLUDED not in t]


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as prefix:   # fresh, empty bytecode location per process
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPYCACHEPREFIX=prefix, GITHUB_SHA="")
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        leaked = list(Path(prefix).rglob("*.pyc"))
    if leaked:
        raise RuntimeError(f"bytecode written: {leaked[:3]}")
    return r


def unit(ids: list[str]) -> dict:
    r = run([sys.executable, "-B", "-m", "unittest", "-v"] + ids)
    fails = re.findall(r"^FAIL: (\S+) \(([^)]+)\)", r.stderr, re.M)
    errors = re.findall(r"^ERROR: (\S+) \(([^)]+)\)", r.stderr, re.M)
    asserts = re.findall(r"^(AssertionError: .*)$", r.stderr, re.M)
    ran = re.search(r"^Ran (\d+) tests", r.stderr, re.M)
    return {"rc": r.returncode, "ran": int(ran.group(1)) if ran else 0, "fail": [f[0] for f in fails],
            "error": [e[0] for e in errors], "assertions": [a[:160] for a in asserts]}


def main(freeze_path: str) -> int:
    for p in pycaches():
        for f in (ROOT / p).iterdir():
            f.unlink()
        (ROOT / p).rmdir()
    out = {"start_pycache": pycaches()}
    ids = test_ids()
    out["tests"] = len(ids)
    out["baseline_before"] = unit(ids)
    results = []
    for mod, name, old, new in MUTANTS:
        path = ROOT / "episodic_lab" / f"{mod}.py"
        src = path.read_bytes()
        h0 = hashlib.sha256(src).hexdigest()
        text = src.decode()
        assert text.count(old) == 1, (name, text.count(old))
        path.write_text(text.replace(old, new))
        try:
            res = unit(ids)
        finally:
            path.write_bytes(src)
        restored = hashlib.sha256(path.read_bytes()).hexdigest() == h0
        killed = bool(res["fail"]) and restored
        results.append({"mutant": name, "file": f"episodic_lab/{mod}.py", "killed": killed, "restored": restored,
                        "failing_tests": res["fail"], "errors": res["error"], "assertion": res["assertions"][:2]})
    out["mutants"] = results
    out["baseline_after"] = unit(ids)
    sys.path[:0] = [str(ROOT / "bench" / "m3")]
    import freeze35
    out["freeze_check"] = freeze35.check(json.loads(Path(freeze_path).read_text())["frozen"])
    out["end_pycache"] = pycaches()
    ok = (not out["start_pycache"] and not out["end_pycache"] and out["baseline_before"]["rc"] == 0
          and out["baseline_after"]["rc"] == 0 and all(m["killed"] for m in results) and out["freeze_check"] == [])
    out["RESULT"] = "PASS" if ok else "FAIL"
    print(json.dumps(out, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
