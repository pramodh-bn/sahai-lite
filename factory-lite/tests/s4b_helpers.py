"""Stage 4B (consent, vendor lifecycle, deletion) black-box test helpers.

Not a test module itself (does not match ``test_*.py``). Every helper talks to
the real application over HTTP at the localhost base URL documented in
``app/RUN.md`` (guarded by ``assert_local_health_url``) and to a loopback fake
vendor on an ephemeral port. The application never imports this module.

The wire contract is documented in
``factory-lite/docs/stage-4b-acceptance-contract.md``.
"""
import hashlib
import http.server
import json
import os
import re
import shlex
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

from s2_helpers import (
    app_base_url,
    git_head_sha,
    startup_command,
    wait_for_health,
)
from test_req2_health_version import assert_local_health_url

REPO_ROOT = Path(__file__).resolve().parents[2]

SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
CONSENT_POLICY_VERSION = "consent.v1"
SCOPES = (
    "rehearsal",
    "avatar",
    "mic",
    "transcript_save",
    "research",
    "subject_consent",
)
PII_MARKER = "PII-MARKER-4B-77Q"
FAKE_API_KEY = "fake-napster-key-stage4b"
FAKE_AGENT_ID = "agent-alex-dana-4b"


def session_hash(session_id):
    return "sha256:" + hashlib.sha256(session_id.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# HTTP plumbing
# ---------------------------------------------------------------------------

def _request(method, path, payload=None, timeout=20.0):
    url = path if path.startswith("http") else app_base_url() + path
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
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    text = raw.decode("utf-8", errors="replace")
    try:
        body = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError:
        body = None
    return status, body, text


def post(path, payload=None, timeout=20.0):
    status, body, _ = _request("POST", path, payload if payload is not None else {}, timeout)
    return status, body if body is not None else {}


def get(path, timeout=20.0):
    status, body, _ = _request("GET", path, None, timeout)
    return status, body if body is not None else {}


def delete(path, timeout=20.0):
    status, body, _ = _request("DELETE", path, None, timeout)
    return status, body if body is not None else {}


# ---------------------------------------------------------------------------
# Application process with log capture
# ---------------------------------------------------------------------------

class S4BApp:
    """Starts the documented startup command with extra env and captured logs."""

    def __init__(self, env=None, capture_logs=True):
        self.env = dict(env or {})
        self.capture_logs = capture_logs
        self.proc = None
        self.log_dir = None
        self._out = None
        self._err = None

    def start(self):
        cmd = shlex.split(startup_command())
        expected_sha = git_head_sha()
        env = dict(os.environ)
        env.update(self.env)
        self.log_dir = Path(tempfile.mkdtemp(prefix="sah-s4b-logs-"))
        self._out_path = self.log_dir / "app.stdout.log"
        self._err_path = self.log_dir / "app.stderr.log"
        if self.capture_logs:
            self._out = open(self._out_path, "wb")
            self._err = open(self._err_path, "wb")
            self.proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env,
                                         stdout=self._out, stderr=self._err)
        else:
            self.proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env)
        try:
            wait_for_health(expected_sha)
        except Exception:
            self.stop()
            raise
        return self

    def stop(self):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
            self.proc = None
        for handle in (self._out, self._err):
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass
        self._out = None
        self._err = None

    def log_text(self):
        chunks = []
        for path in (getattr(self, "_out_path", None), getattr(self, "_err_path", None)):
            if path is not None and Path(path).is_file():
                chunks.append(Path(path).read_text(encoding="utf-8", errors="replace"))
        return "\n".join(chunks)

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# ---------------------------------------------------------------------------
# Fake vendor (test fixture; the app reaches it only through NAPSTER_BASE_URL)
# ---------------------------------------------------------------------------

class _FakeVendorHandler(http.server.BaseHTTPRequestHandler):
    def _record(self, method):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            parsed = {}
        record = {
            "method": method,
            "path": self.path,
            "headers": dict(self.headers),
            "body": parsed,
        }
        with self.server.lock:
            self.server.requests.append(record)
        return parsed

    def _json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        self._record("POST")
        parts = self.path.strip("/").split("/")
        if len(parts) < 3 or parts[0] != "public" or parts[1] != "agents" or parts[-1] != "connections":
            self._json(404, {"error": "not_found"})
            return
        with self.server.lock:
            self.server.created_count += 1
            number = self.server.created_count
            connection_id = "conn_s4b_%d" % number
            token = "napster_conn_token_s4b_%d" % number
            self.server.created.append(connection_id)
        self._json(200, {"token": token, "connection": {"id": connection_id}})

    def do_DELETE(self):
        self._record("DELETE")
        with self.server.lock:
            if self.server.fail_delete_count > 0:
                self.server.fail_delete_count -= 1
                fail = True
            else:
                fail = False
            if not fail:
                self.server.deleted.append(self.path)
        if fail:
            self._json(500, {"error": "vendor_delete_failed"})
            return
        self._json(200, {"status": "destroyed"})

    def log_message(self, fmt, *args):
        pass


class FakeVendor:
    """Loopback HTTP vendor with an observable create/delete ledger."""

    def __init__(self):
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _FakeVendorHandler)
        self.httpd.lock = threading.Lock()
        self.httpd.requests = []
        self.httpd.created = []
        self.httpd.deleted = []
        self.httpd.created_count = 0
        self.httpd.fail_delete_count = 0
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def base_url(self):
        return "http://127.0.0.1:%d" % self.httpd.server_address[1]

    def env(self):
        return {
            "NAPSTER_BASE_URL": self.base_url,
            "NAPSTER_API_KEY": FAKE_API_KEY,
            "NAPSTER_AGENT_ID": FAKE_AGENT_ID,
        }

    def fail_next_deletes(self, count):
        with self.httpd.lock:
            self.httpd.fail_delete_count = count

    def ledger(self):
        with self.httpd.lock:
            return {
                "created": list(self.httpd.created),
                "deleted": list(self.httpd.deleted),
                "created_count": self.httpd.created_count,
            }

    def requests(self):
        with self.httpd.lock:
            return list(self.httpd.requests)

    def reset(self):
        with self.httpd.lock:
            self.httpd.requests = []
            self.httpd.created = []
            self.httpd.deleted = []
            self.httpd.created_count = 0
            self.httpd.fail_delete_count = 0

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.httpd.shutdown()
        self.httpd.server_close()


# ---------------------------------------------------------------------------
# Session and consent helpers
# ---------------------------------------------------------------------------

def create_session(extra=None):
    return post("/api/rehearsal/sessions", dict(extra or {}))


def require_session():
    status, body = create_session()
    if status != 201 or not body.get("session_id"):
        raise AssertionError(f"session creation failed: status={status} body={body}")
    return body["session_id"]


def advance(session_id, target):
    return post(f"/api/rehearsal/sessions/{session_id}/advance", {"to": target})


def make_practice_session():
    sid = require_session()
    for target in ("take_my_seat", "practice"):
        status, body = advance(sid, target)
        if status != 200:
            raise AssertionError(f"advance to {target} failed: status={status} body={body}")
    return sid


def consent_get(session_id):
    return get(f"/api/rehearsal/sessions/{session_id}/consent")


def consent_set(session_id, scope, granted, schema="sah.consent.v1"):
    return post(
        f"/api/rehearsal/sessions/{session_id}/consent",
        {"schema": schema, "scope": scope, "granted": granted},
    )


def grant(session_id, scope):
    status, body = consent_set(session_id, scope, True)
    if status != 200:
        raise AssertionError(f"granting {scope!r} failed: status={status} body={body}")
    return body


def grant_many(session_id, scopes):
    for scope in scopes:
        grant(session_id, scope)


def withdraw(session_id, scope):
    return consent_set(session_id, scope, False)


def practice(session_id, utterance):
    return post(f"/api/rehearsal/sessions/{session_id}/practice", {"utterance": utterance})


def mic_start(session_id):
    return post(f"/api/rehearsal/sessions/{session_id}/mic/start", {})


def transcript_save(session_id):
    return post(f"/api/rehearsal/sessions/{session_id}/transcript/save", {})


def transcript_saved(session_id):
    return get(f"/api/rehearsal/sessions/{session_id}/transcript/saved")


def research_export(session_id):
    return post(f"/api/rehearsal/sessions/{session_id}/research/export", {})


def napster_create(session_id, simulate_error=None):
    payload = {}
    if simulate_error is not None:
        payload["simulate_error"] = simulate_error
    return post(f"/api/rehearsal/sessions/{session_id}/napster-session", payload)


def napster_delete(session_id):
    return delete(f"/api/rehearsal/sessions/{session_id}/napster-session")


def delete_session(session_id):
    return delete(f"/api/rehearsal/sessions/{session_id}")


def snapshot(session_id):
    return get(f"/api/rehearsal/sessions/{session_id}")


def assert_status(testcase, status_body, expected, context):
    status, body = status_body
    testcase.assertEqual(status, expected, f"{context}: status={status} body={body}")
    return body


def assert_consent_required(testcase, status_body, scope, context):
    status, body = status_body
    testcase.assertEqual(status, 403, f"{context}: expected 403, got status={status} body={body}")
    testcase.assertEqual(body.get("error"), "consent_required",
                         f"{context}: wrong error body={body}")
    testcase.assertEqual(body.get("scope"), scope,
                         f"{context}: wrong blocking scope body={body}")
