"""Offline proof for Stage 3 repair R1.

Runs without live credentials and makes no vendor calls beyond the local fake
vendor. It proves:
1. The vendored SDK is served at the exact pinned URL with a JavaScript MIME
   type and the pinned SHA-256 digest.
2. The app tears down connections through the documented
   DELETE /public/connections/{connectionId} endpoint.
3. A failed upstream DELETE keeps the local cleanup handle so a later DELETE
   can retry deterministically.

Run with: py -3.12 app/verify_stage3_offline.py
"""
import hashlib
import os
import time
from pathlib import Path

import sys

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
TESTS_DIR = REPO_ROOT / "factory-lite" / "tests"
for path in (APP_DIR, TESTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import main as app_main  # noqa: E402
import napster  # noqa: E402
import s3_helpers  # noqa: E402

SDK_URL = "/vendor/napster-companion-api/2.0.0/bundle.js"
SDK_SHA256 = "c1b2db52267af46e172e4c5fbb0c46b67f57729bc841b26ac4e112a14ddd025f"


class FailingDeleteHandler(s3_helpers.FakeNapsterHandler):
    """Fake vendor handler that records but rejects DELETE with HTTP 500."""

    def do_DELETE(self):
        self.server.request_log.append({
            "method": "DELETE",
            "path": self.path,
            "headers": dict(self.headers),
            "timestamp": time.time(),
        })
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error": "vendor_delete_failed"}')


def proof_sdk():
    resp = app_main.app.test_client().get(SDK_URL)
    assert resp.status_code == 200, resp.status_code
    ctype = resp.headers.get("Content-Type", "")
    assert "javascript" in ctype.lower(), ctype
    digest = hashlib.sha256(resp.data).hexdigest()
    assert digest == SDK_SHA256, digest
    print("SDK_PROOF_OK status=200 content_type=%s sha256=%s bytes=%d" % (ctype, digest, len(resp.data)))


def _new_session(client):
    resp = client.post("/api/rehearsal/sessions", json={})
    assert resp.status_code == 201, (resp.status_code, resp.get_json())
    return resp.get_json()["session_id"]


def proof_delete_path_and_retention():
    vendor = s3_helpers.FakeNapsterServer()
    vendor.__enter__()
    os.environ["NAPSTER_BASE_URL"] = vendor.base_url
    os.environ["NAPSTER_API_KEY"] = "fake-proof-key"
    os.environ["NAPSTER_AGENT_ID"] = "agent-proof"
    try:
        client = app_main.app.test_client()

        sid = _new_session(client)
        resp = client.post(
            "/api/rehearsal/sessions/%s/napster-session" % sid,
            json={"channel_type": "webrtc"},
        )
        assert resp.status_code == 200, (resp.status_code, resp.get_json())
        conn_id = resp.get_json()["connection_id"]
        resp = client.delete("/api/rehearsal/sessions/%s/napster-session" % sid)
        assert resp.status_code == 200, (resp.status_code, resp.get_json())
        deletes = [req for req in vendor.get_requests() if req["method"] == "DELETE"]
        assert deletes, "no DELETE reached the fake vendor"
        assert deletes[-1]["path"] == "/public/connections/%s" % conn_id, deletes[-1]["path"]
        print("DELETE_PATH_PROOF_OK path=%s" % deletes[-1]["path"])

        vendor.clear_requests()
        sid2 = _new_session(client)
        resp = client.post(
            "/api/rehearsal/sessions/%s/napster-session" % sid2,
            json={"channel_type": "webrtc"},
        )
        assert resp.status_code == 200, (resp.status_code, resp.get_json())
        conn_id2 = resp.get_json()["connection_id"]

        vendor.httpd.RequestHandlerClass = FailingDeleteHandler
        resp = client.delete("/api/rehearsal/sessions/%s/napster-session" % sid2)
        assert resp.status_code == 502, (resp.status_code, resp.get_json())
        body = resp.get_json()
        assert body.get("connection_retained") is True, body
        entry = napster._state.get(sid2)
        assert entry and entry.get("connection"), "local cleanup handle was discarded"
        deletes = [req for req in vendor.get_requests() if req["method"] == "DELETE"]
        assert deletes and deletes[-1]["path"] == "/public/connections/%s" % conn_id2
        print("DELETE_FAILURE_RETENTION_PROOF_OK status=502 retained=True path=%s" % deletes[-1]["path"])

        vendor.httpd.RequestHandlerClass = s3_helpers.FakeNapsterHandler
        resp = client.delete("/api/rehearsal/sessions/%s/napster-session" % sid2)
        assert resp.status_code == 200, (resp.status_code, resp.get_json())
        entry = napster._state.get(sid2)
        assert not entry or not entry.get("connection"), "cleanup handle not cleared on retry"
        print("DELETE_RETRY_PROOF_OK status=200 handle_cleared=True")
    finally:
        vendor.__exit__(None, None, None)
        for name in ("NAPSTER_BASE_URL", "NAPSTER_API_KEY", "NAPSTER_AGENT_ID"):
            os.environ.pop(name, None)


if __name__ == "__main__":
    proof_sdk()
    proof_delete_path_and_retention()
    print("ALL_OFFLINE_PROOFS_OK")
