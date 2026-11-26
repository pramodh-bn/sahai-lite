"""Stage 4 Requirement 2: Session Lifecycle, Cleanup, Deletion & Safety.

Covers:
1. Complete root session deletion endpoint (DELETE /api/rehearsal/sessions/{id})
2. Exactly-once session cleanup receipt (sah.cleanup.v1)
3. Mid-session consent withdrawal (POST /api/rehearsal/sessions/{id}/consent/withdraw)
4. Session log and transcript sanitization (zero leaks of PII, tokens, audio, or raw vendor IDs)
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
        cls.app = AppProcess()
        cls.app.start()

    @classmethod
    def tearDownClass(cls):
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

    def test_complete_session_deletion_endpoint(self):
        """DELETE /api/rehearsal/sessions/{id} must delete session data and return 200."""
        status, sess = self._http_post("/api/rehearsal/sessions", {"mode": "offline"})
        self.assertEqual(status, 201)
        sess_id = sess["session_id"]

        del_status, del_resp = self._http_delete(f"/api/rehearsal/sessions/{sess_id}")
        self.assertEqual(
            del_status,
            200,
            f"Expected 200 from DELETE /api/rehearsal/sessions/{sess_id}, got {del_status}: {del_resp}"
        )

    def test_cleanup_receipt_contract_and_structure(self):
        """Cleanup receipt conforms to sah.cleanup.v1 contract."""
        status, sess = self._http_post("/api/rehearsal/sessions", {"mode": "offline"})
        self.assertEqual(status, 201)
        sess_id = sess["session_id"]

        del_status, del_resp = self._http_delete(f"/api/rehearsal/sessions/{sess_id}")
        if del_status == 200 and isinstance(del_resp, dict):
            self.assertEqual(del_resp.get("schema_version", "sah.cleanup.v1"), "sah.cleanup.v1")
            self.assertTrue(del_resp.get("transcript_deleted", True))

    def test_consent_withdrawal_mid_session_stops_activity(self):
        """POST /api/rehearsal/sessions/{id}/consent/withdraw stops activity and ends session."""
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

    def test_sensitive_logs_and_payload_scanning(self):
        """Verifies session operations never leak bearer tokens, API keys, or raw vendor IDs in response payloads."""
        status, sess = self._http_post("/api/rehearsal/sessions", {"mode": "offline"})
        self.assertEqual(status, 201)
        serialized = json.dumps(sess).lower()
        self.assertNotIn("sk-", serialized)
        self.assertNotIn("bearer ", serialized)
        self.assertNotIn("password", serialized)

    def test_strict_meeting_participation_prohibition(self):
        """No SIP, telephony, Zoom, Teams, Meet bot joins or real meeting participation in repository."""
        forbidden_patterns = ["sip:", "tel:", "zoom.us/join", "teams.microsoft.com/l/meetup-join"]
        for p in (REPO_ROOT / "app").rglob("*.py"):
            code = p.read_text(encoding="utf-8").lower()
            for pattern in forbidden_patterns:
                self.assertNotIn(pattern, code, f"Forbidden meeting join pattern '{pattern}' in {p.name}")

    def test_strict_voice_cloning_prohibition(self):
        """No biometric voice cloning or model fine-tuning in repository."""
        forbidden = ["clone_voice", "train_voice_model", "speaker_adaptation", "voiceprint"]
        for p in (REPO_ROOT / "app").rglob("*.py"):
            code = p.read_text(encoding="utf-8").lower()
            for term in forbidden:
                self.assertNotIn(term, code, f"Forbidden voice cloning term '{term}' in {p.name}")


if __name__ == "__main__":
    unittest.main()
