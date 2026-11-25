"""Req 7 (stage-1.md): "verify clean checkout startup."

Clones the exact commit under test into a fresh temporary directory (no
reliance on this worktree's build caches or local state) and verifies the
documented Req 1 startup command brings up a Req 2 healthy endpoint there.
"""
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from test_req2_health_version import assert_local_health_url

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS = REPO_ROOT / "factory-lite" / "tests" / "harness" / "health_check.py"
STARTUP_TIMEOUT_S = 30
POLL_INTERVAL_S = 0.5


def extract_section_block(text, heading):
    m = re.search(rf"##\s*{heading}\b.*?```(?:\w+)?\n(.*?)```", text, re.S | re.I)
    return m.group(1).strip() if m else None


class TestCleanCheckoutStartup(unittest.TestCase):
    proc = None
    tmpdir = None

    def tearDown(self):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None
        if self.tmpdir is not None:
            shutil.rmtree(self.tmpdir, ignore_errors=True)
            self.tmpdir = None

    def test_clean_checkout_of_head_starts_and_becomes_healthy(self):
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()

        self.tmpdir = Path(tempfile.mkdtemp(prefix="sahai-lite-clean-checkout-"))
        clone = subprocess.run(
            ["git", "clone", "--quiet", str(REPO_ROOT), str(self.tmpdir)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(clone.returncode, 0, f"clean clone failed:\n{clone.stderr}")

        checkout = subprocess.run(
            ["git", "checkout", "--quiet", head], cwd=self.tmpdir, capture_output=True, text=True
        )
        self.assertEqual(checkout.returncode, 0, f"checkout of {head} failed:\n{checkout.stderr}")

        run_doc = self.tmpdir / "app" / "RUN.md"
        self.assertTrue(run_doc.is_file(), f"missing {run_doc} in clean checkout; cannot verify startup")
        text = run_doc.read_text(encoding="utf-8")

        run_block = extract_section_block(text, "Run")
        self.assertIsNotNone(run_block, "no '## Run' command block in clean checkout's RUN.md")
        startup_cmd = [ln for ln in run_block.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        self.assertEqual(len(startup_cmd), 1, "Req 1 startup command must be singular")

        health_block = extract_section_block(text, "Health")
        self.assertIsNotNone(health_block, "no '## Health' URL block in clean checkout's RUN.md")
        health_url = health_block.splitlines()[0].strip()
        assert_local_health_url(health_url)

        self.proc = subprocess.Popen(shlex.split(startup_cmd[0]), cwd=self.tmpdir)

        deadline = time.time() + STARTUP_TIMEOUT_S
        last_code, last_out, last_err = None, "", ""
        while time.time() < deadline:
            result = subprocess.run(
                [sys.executable, str(HARNESS), health_url, "--expected-sha", head, "--timeout", "2"],
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
            f"clean checkout of {head} never became healthy at {health_url}: "
            f"stdout={last_out} stderr={last_err}",
        )


if __name__ == "__main__":
    unittest.main()
