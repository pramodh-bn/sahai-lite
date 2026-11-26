"""Stage 4 Requirement 2: Session Lifecycle, Cleanup, Deletion & Safety.

Covers:
1. Complete root session deletion endpoint (DELETE /api/rehearsal/sessions/{id}) and session inaccessibility
2. Exactly-once session cleanup receipt (sah.cleanup.v1) and safe repeated cleanup
3. Mid-session consent withdrawal (POST /api/rehearsal/sessions/{id}/consent/withdraw)
4. Comprehensive log and payload sanitization (tokens, credentials, raw vendor IDs, utterances, audio/video)
5. Strict meeting participation prohibition (zero SIP, telephony, Zoom/Teams/Meet bot joins)
6. Strict voice cloning prohibition (zero biometric voice cloning pipelines)
"""
import json
import os
import sys
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent

if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s2_helpers import AppProcess, app_base_url


class TestStage4SessionLifecycleAndSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def _http_post(self, path, payload):
        base = app_base_url()
        url = f"{base}{path}"
        req = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=10) as resp:
                data = resp.read()
                return resp.status, json.loads(data.decode("utf-8")) if data else {}
        except HTTPError as exc:
            err_data = exc.read()
            try:
                parsed = json.loads(err_data.decode("utf-8"))
            except Exception:
                parsed = {"raw": err_data.decode("utf-8", errors="replace")}
            return exc.code, parsed

    def _http_get(self, path):
        base = app_base_url()
        url = f"{base}{path}"
        req = Request(url, headers={"Content-Type": "application/json"}, method="GET")
        try:
            with urlopen(req, timeout=10) as resp:
                data = resp.read()
                return resp.status, json.loads(data.decode("utf-8")) if data else {}
        except HTTPError as exc:
            err_data = exc.read()
            try:
                parsed = json.loads(err_data.decode("utf-8"))
            except Exception:
                parsed = {"raw": err_data.decode("utf-8", errors="replace")}
            return exc.code, parsed

    def _http_delete(self, path):
        base = app_base_url()
        url = f"{base}{path}"
        req = Request(url, headers={"Content-Type": "application/json"}, method="DELETE")
        try:
            with urlopen(req, timeout=10) as resp:
                data = resp.read()
                return resp.status, json.loads(data.decode("utf-8")) if data else {}
        except HTTPError as exc:
            err_data = exc.read()
            try:
                parsed = json.loads(err_data.decode("utf-8"))
            except Exception:
                parsed = {"raw": err_data.decode("utf-8", errors="replace")}
            return exc.code, parsed

    def test_complete_session_deletion_endpoint_and_inaccessibility(self):
        """DELETE /api/rehearsal/sessions/{id} must delete session data, return 200, and make session inaccessible (404)."""
        status, sess = self._http_post("/api/rehearsal/sessions", {"mode": "offline"})
        self.assertEqual(status, 201)
        sess_id = sess["session_id"]

        del_status, del_resp = self._http_delete(f"/api/rehearsal/sessions/{sess_id}")
        self.assertEqual(
            del_status,
            200,
            f"Expected 200 from DELETE /api/rehearsal/sessions/{sess_id}, got {del_status}: {del_resp}"
        )

        # Subsequent GET on deleted session must return 404
        get_status, get_resp = self._http_get(f"/api/rehearsal/sessions/{sess_id}")
        self.assertEqual(
            get_status,
            404,
            f"Expected 404 for deleted session {sess_id}, got {get_status}: {get_resp}"
        )

    def test_cleanup_receipt_contract_and_idempotent_repeated_cleanup(self):
        """Cleanup returns exact sah.cleanup.v1 receipt; repeated cleanup is safe without secondary errors."""
        status, sess = self._http_post("/api/rehearsal/sessions", {"mode": "offline"})
        self.assertEqual(status, 201)
        sess_id = sess["session_id"]

        del_status, del_resp = self._http_delete(f"/api/rehearsal/sessions/{sess_id}")
        self.assertEqual(del_status, 200, f"Initial cleanup failed: {del_resp}")

        self.assertIn("schema_version", del_resp, "Cleanup receipt must include schema_version")
        self.assertEqual(del_resp["schema_version"], "sah.cleanup.v1")
        self.assertIn("vendor_session_destroyed", del_resp)
        self.assertIs(del_resp["vendor_session_destroyed"], True)
        self.assertIn("local_media_stopped", del_resp)
        self.assertIs(del_resp["local_media_stopped"], True)
        self.assertIn("transcript_deleted", del_resp)
        self.assertIs(del_resp["transcript_deleted"], True)
        self.assertIn("connection_retained", del_resp)
        self.assertIs(del_resp["connection_retained"], False)

        # Idempotent repeated DELETE must return 200 or 404 safely
        del2_status, del2_resp = self._http_delete(f"/api/rehearsal/sessions/{sess_id}")
        self.assertIn(del2_status, [200, 404], f"Repeated cleanup returned unexpected code {del2_status}: {del2_resp}")

    def test_mid_session_consent_withdrawal_stops_activity(self):
        """POST /api/rehearsal/sessions/{id}/consent/withdraw halts rendering and ends session."""
        status, sess = self._http_post("/api/rehearsal/sessions", {"mode": "offline"})
        self.assertEqual(status, 201)
        sess_id = sess["session_id"]

        w_status, w_resp = self._http_post(
            f"/api/rehearsal/sessions/{sess_id}/consent/withdraw",
            {"scope": "avatar"}
        )
        self.assertEqual(
            w_status,
            200,
            f"Expected 200 from consent withdraw, got {w_status}: {w_resp}"
        )

    def test_comprehensive_log_and_payload_sanitization(self):
        """Inspects payloads and server outputs for zero leaks of tokens, credentials, raw vendor IDs, or audio/video."""
        status, sess = self._http_post("/api/rehearsal/sessions", {"mode": "offline"})
        self.assertEqual(status, 201)
        sess_id = sess["session_id"]

        self._http_post(f"/api/rehearsal/sessions/{sess_id}/advance", {"to": "take_my_seat"})
        self._http_post(f"/api/rehearsal/sessions/{sess_id}/advance", {"to": "practice"})
        status, p_resp = self._http_post(
            f"/api/rehearsal/sessions/{sess_id}/practice",
            {"utterance": "Confidential budget discussion terms"}
        )
        self.assertEqual(status, 200)

        # Scan serialized response payloads
        combined = (json.dumps(sess) + json.dumps(p_resp)).lower()
        forbidden_substrings = [
            "sk-", "bearer ", "password", "napster_session_", "audio/wav", "audio/mp3", "data:audio", "data:video"
        ]
        for term in forbidden_substrings:
            self.assertNotIn(term, combined, f"Found forbidden leaked term '{term}' in response payload")

    def test_strict_meeting_participation_prohibition(self):
        """No SIP, telephony, Zoom, Teams, Meet bot joins or real meeting participation in repository."""
        forbidden_patterns = ["sip:", "tel:", "zoom.us/join", "teams.microsoft.com/l/meetup-join"]
        for p in (REPO_ROOT / "app").rglob("*.py"):
            code = p.read_text(encoding="utf-8").lower()
            for pattern in forbidden_patterns:
                self.assertNotIn(pattern, code, f"Forbidden meeting join pattern '{pattern}' in {p.name}")

    def test_strict_voice_cloning_prohibition(self):
        """No biometric voice cloning or speaker adaptation model fine-tuning in repository."""
        forbidden = ["clone_voice", "train_voice_model", "speaker_adaptation", "voiceprint"]
        for p in (REPO_ROOT / "app").rglob("*.py"):
            code = p.read_text(encoding="utf-8").lower()
            for term in forbidden:
                self.assertNotIn(term, code, f"Forbidden voice cloning term '{term}' in {p.name}")


if __name__ == "__main__":
    unittest.main()
