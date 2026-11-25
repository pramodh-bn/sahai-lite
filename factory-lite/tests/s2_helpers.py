"""Shared black-box helpers for the Stage 2 (factory-lite/spec/stage-2.md)
rehearsal-engine test contract. Not a test module itself (does not match
`test_*.py`), so it is never collected by `unittest discover` directly --
only imported by the `test_s2_*.py` files.

Stage 2 reuses the Stage 1 service (same documented Req 1 startup command,
same app/RUN.md "## Health" URL) and adds a JSON HTTP API under
`/api/rehearsal/` on that same base URL. See CONTRACT.md for the full
endpoint contract this fixes for Builder to implement against.

Every helper here talks only to the localhost URL documented in
app/RUN.md (enforced via `assert_local_health_url`, reused from Stage 1) --
no external network calls.
"""
import json
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from test_req2_health_version import assert_local_health_url, extract_section_block

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DOC = REPO_ROOT / "app" / "RUN.md"
HARNESS = REPO_ROOT / "factory-lite" / "tests" / "harness" / "health_check.py"
STARTUP_TIMEOUT_S = 20
POLL_INTERVAL_S = 0.5


class ContractError(AssertionError):
    pass


def read_run_doc_or_raise():
    if not RUN_DOC.is_file():
        raise ContractError(f"missing {RUN_DOC}; Stage 2 reuses the Stage 1 startup contract")
    return RUN_DOC.read_text(encoding="utf-8")


def startup_command():
    text = read_run_doc_or_raise()
    run_block = extract_section_block(text, "Run")
    if run_block is None:
        raise ContractError(f"no '## Run' command block in {RUN_DOC}")
    lines = [ln for ln in run_block.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if len(lines) != 1:
        raise ContractError(f"expected exactly one startup command in {RUN_DOC}, found {len(lines)}")
    return lines[0]


def health_url():
    text = read_run_doc_or_raise()
    health_block = extract_section_block(text, "Health")
    if health_block is None:
        raise ContractError(f"no '## Health' URL block in {RUN_DOC}")
    url = health_block.splitlines()[0].strip()
    assert_local_health_url(url)
    return url


def app_base_url():
    """The Stage 1 health URL with the trailing /health stripped -- the
    base all Stage 2 /api/rehearsal/... routes hang off of."""
    url = health_url()
    if not url.endswith("/health"):
        raise ContractError(f"health URL {url!r} does not end with /health; cannot derive API base")
    return url[: -len("/health")]


def wait_for_health(expected_sha, timeout_s=STARTUP_TIMEOUT_S):
    url = health_url()
    deadline = time.time() + timeout_s
    last_code, last_out, last_err = None, "", ""
    while time.time() < deadline:
        result = subprocess.run(
            [sys.executable, str(HARNESS), url, "--expected-sha", expected_sha, "--timeout", "2"],
            capture_output=True,
            text=True,
        )
        last_code, last_out, last_err = result.returncode, result.stdout, result.stderr
        if last_code == 0:
            return
        time.sleep(POLL_INTERVAL_S)
    raise ContractError(
        f"service at {url} never became healthy with SHA {expected_sha}: stdout={last_out} stderr={last_err}"
    )


def git_head_sha():
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


class AppProcess:
    """Starts the documented Req 1 startup command and tears it down.
    Use as a context manager in setUp/tearDown (unittest has no native
    context-manager fixtures, so call __enter__/__exit__ explicitly)."""

    def __init__(self):
        self.proc = None

    def start(self):
        cmd = startup_command()
        expected_sha = git_head_sha()
        self.proc = subprocess.Popen(shlex.split(cmd), cwd=REPO_ROOT)
        wait_for_health(expected_sha)
        return self

    def stop(self):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None


def _request(method, url, payload=None, timeout=5.0):
    assert_local_health_url(url)
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
    body_text = body.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError as exc:
        raise ContractError(f"{method} {url} returned non-JSON body: {body_text!r} ({exc})")
    return status, parsed


def post_json(path, payload=None):
    """POST to app_base_url() + path. `path` must start with '/'."""
    return _request("POST", app_base_url() + path, payload if payload is not None else {})


def get_json(path):
    return _request("GET", app_base_url() + path)
