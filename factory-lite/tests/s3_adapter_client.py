"""Black-box subprocess launcher for the frozen app/napster_adapter.py CLI
(factory-lite/tests/CONTRACT.md "Stage 3 adapter CLI"). Not a test module
itself (doesn't match test_*.py).

Every call here only ever points NAPSTER_BASE_URL at a local fixture
server (factory-lite/tests/s3_fake_vendor.py) -- never a real vendor
host -- for the offline req3/req4 tests. test_s3_live_napster.py is the
only place NAPSTER_BASE_URL may point at the real vendor, and only when
the live gate is open.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = REPO_ROOT / "app" / "napster_adapter.py"


def run_adapter(capability, base_url, state_dir, evidence_dir, api_key="dummy-test-key", timeout=30):
    """Run the adapter CLI once. Returns (returncode, stdout_json_or_None,
    stdout_text, stderr_text). Never raises on a missing/erroring adapter
    -- that is exactly what the offline tests must observe as red."""
    env = {
        "NAPSTER_BASE_URL": base_url,
        "NAPSTER_API_KEY": api_key,
        "ADAPTER_STATE_DIR": str(state_dir),
        "ADAPTER_EVIDENCE_DIR": str(evidence_dir),
    }
    proc = subprocess.run(
        [sys.executable, str(ADAPTER_PATH), capability],
        capture_output=True,
        text=True,
        env=_merged_env(env),
        timeout=timeout,
    )
    parsed = None
    first_line = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
    if first_line:
        try:
            parsed = json.loads(first_line)
        except json.JSONDecodeError:
            parsed = None
    return proc.returncode, parsed, proc.stdout, proc.stderr


def _merged_env(overrides):
    import os

    merged = dict(os.environ)
    merged.update(overrides)
    return merged
