"""Req 2 (stage-1.md): "health and version report actual build SHA."

Contract convention (see factory-lite/tests/CONTRACT.md):
  - app/RUN.md documents, under a "## Health" heading, a single fenced block
    whose first line is the full health-check URL, e.g.
    http://127.0.0.1:8000/health.
  - The process started via the Req 1 startup command must answer that URL
    with HTTP 200 and JSON {"status": "ok", "version": "<git HEAD sha>"},
    where <git HEAD sha> is the exact commit of the checkout under test.

This is a true black-box check: it starts the documented command as a
subprocess and polls the documented URL with the independent harness
(factory-lite/tests/harness/health_check.py); it never imports application
code.
"""
import re
import shlex
import subprocess
import sys
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DOC = REPO_ROOT / "app" / "RUN.md"
HARNESS = REPO_ROOT / "factory-lite" / "tests" / "harness" / "health_check.py"
STARTUP_TIMEOUT_S = 20
POLL_INTERVAL_S = 0.5


def extract_section_block(text, heading):
    m = re.search(rf"##\s*{heading}\b.*?```(?:\w+)?\n(.*?)```", text, re.S | re.I)
    return m.group(1).strip() if m else None


def git_head_sha():
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


class TestHealthReportsActualBuildSha(unittest.TestCase):
    proc = None

    def tearDown(self):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None

    def test_health_endpoint_reports_actual_build_sha(self):
        self.assertTrue(RUN_DOC.is_file(), f"missing {RUN_DOC}; cannot locate startup command")
        text = RUN_DOC.read_text(encoding="utf-8")

        run_block = extract_section_block(text, "Run")
        self.assertIsNotNone(run_block, f"no '## Run' command block in {RUN_DOC}")
        startup_cmd = [ln for ln in run_block.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        self.assertEqual(len(startup_cmd), 1, "Req 1 startup command must be singular")

        health_block = extract_section_block(text, "Health")
        self.assertIsNotNone(health_block, f"no '## Health' URL block in {RUN_DOC}")
        health_url = health_block.splitlines()[0].strip()
        self.assertTrue(
            health_url.startswith("http://") or health_url.startswith("https://"),
            f"health URL malformed: {health_url!r}",
        )

        expected_sha = git_head_sha()

        self.proc = subprocess.Popen(shlex.split(startup_cmd[0]), cwd=REPO_ROOT)

        deadline = time.time() + STARTUP_TIMEOUT_S
        last_code, last_out, last_err = None, "", ""
        while time.time() < deadline:
            result = subprocess.run(
                [sys.executable, str(HARNESS), health_url, "--expected-sha", expected_sha, "--timeout", "2"],
                capture_output=True,
                text=True,
            )
            last_code, last_out, last_err = result.returncode, result.stdout, result.stderr
            if last_code == 0:
                break
            time.sleep(POLL_INTERVAL_S)

        self.assertEqual(
            last_code,
            0,
            f"health endpoint {health_url} never reported healthy status with SHA {expected_sha}: "
            f"stdout={last_out} stderr={last_err}",
        )


if __name__ == "__main__":
    unittest.main()
