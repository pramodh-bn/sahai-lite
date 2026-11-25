"""Req 6 (stage-1.md): "independent harness exits nonzero for broken service
and zero for healthy implementation."

This proves the harness itself (factory-lite/tests/harness/health_check.py)
is sound, using fixtures entirely under this test's control -- no dependency
on whether the real Stage 1 app exists yet. The real app is exercised
separately by test_req2 and test_req7, which are expected to fail until
Builder implements Stage 1 against this contract.
"""
import http.server
import json
import socket
import subprocess
import sys
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS = REPO_ROOT / "factory-lite" / "tests" / "harness" / "health_check.py"
FIXED_SHA = "deadbeefcafef00dfeedfacefeedfacefeedface"


def free_unused_port():
    """Return a port number that is not bound to anything."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _HealthyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"status": "ok", "version": FIXED_SHA}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class _BrokenHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(500)
        self.end_headers()

    def log_message(self, *args):
        pass


class _FixtureServer:
    def __init__(self, handler_cls):
        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def port(self):
        return self.httpd.server_address[1]

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.httpd.shutdown()
        self.httpd.server_close()


def run_harness(url, expected_sha=None, timeout="2"):
    cmd = [sys.executable, str(HARNESS), url, "--timeout", timeout]
    if expected_sha:
        cmd += ["--expected-sha", expected_sha]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


class TestIndependentHarnessContract(unittest.TestCase):
    def test_harness_script_exists(self):
        self.assertTrue(HARNESS.is_file(), f"independent harness missing at {HARNESS}")

    def test_harness_exits_zero_for_conforming_healthy_service(self):
        with _FixtureServer(_HealthyHandler) as server:
            code, out, err = run_harness(f"http://127.0.0.1:{server.port}/health", FIXED_SHA)
        self.assertEqual(code, 0, f"stdout={out!r} stderr={err!r}")

    def test_harness_exits_nonzero_for_broken_service(self):
        with _FixtureServer(_BrokenHandler) as server:
            code, out, err = run_harness(f"http://127.0.0.1:{server.port}/health", FIXED_SHA)
        self.assertNotEqual(code, 0, f"stdout={out!r} stderr={err!r}")

    def test_harness_exits_nonzero_for_unavailable_service(self):
        port = free_unused_port()  # nothing is listening here
        code, out, err = run_harness(f"http://127.0.0.1:{port}/health", FIXED_SHA)
        self.assertNotEqual(code, 0, f"stdout={out!r} stderr={err!r}")

    def test_harness_exits_nonzero_on_sha_mismatch(self):
        with _FixtureServer(_HealthyHandler) as server:
            code, out, err = run_harness(f"http://127.0.0.1:{server.port}/health", "0" * 40)
        self.assertNotEqual(code, 0, f"stdout={out!r} stderr={err!r}")


if __name__ == "__main__":
    unittest.main()
