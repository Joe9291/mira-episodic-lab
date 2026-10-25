"""Round 4.3: the plan step of .github/workflows/round43.yml executed exactly as written for the
three configurations (Astra's idea in the implementation review v3: a regression test so that
a wrong path replacement in the workflow shows up at once)."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

WF = Path(__file__).resolve().parents[1] / ".github/workflows/round43.yml"


def plan_script() -> str:
    text = WF.read_text()
    start = text.index("python3 - <<'PY'")
    end = text.index("\n          PY", start)
    body = text[start:end].split("\n", 1)[1]
    lines = [ln[10:] if ln.startswith(" " * 10) else ln for ln in body.split("\n")]
    return "python3 - <<'PY'\n" + "\n".join(lines) + "\nPY\n"


class PlanStep(unittest.TestCase):
    def run_plan(self, phase, split):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "config").mkdir()
            (Path(d) / "config/round43.json").write_text(json.dumps({"enabled": True, "phase": phase, "split": split}))
            out = Path(d) / "gh_out"
            out.write_text("")
            env = dict(os.environ, GITHUB_OUTPUT=str(out), RUNNER_TEMP=str(Path(d) / "does-not-exist"))
            r = subprocess.run(["bash", "-e", "-c", plan_script()], cwd=d, env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return dict(line.split("=", 1) for line in out.read_text().splitlines())

    def test_three_configurations(self):
        for phase, split, cells in (("run", "holdout", 14), ("audit", "holdout", 1), ("run", "dev", 14)):
            o = self.run_plan(phase, split)
            m = json.loads(o["matrix"])["include"]
            self.assertEqual((o["enabled"], o["phase"], o["split"], len(m)), ("true", phase, split, cells))
            if phase == "run":
                self.assertEqual([c["families"] for c in m if c["conformance"]], ["P1"])


if __name__ == "__main__":
    unittest.main()
