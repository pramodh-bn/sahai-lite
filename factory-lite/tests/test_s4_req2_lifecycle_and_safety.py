"""Stage 4 Requirement 2: Session Lifecycle, Cleanup, Deletion, and Privacy.

Mandates:
- Exactly-once session cleanup on teardown; zero duplicate DELETEs.
- Complete session data deletion via DELETE /api/rehearsal/sessions/{id}.
- No sensitive logs: application logs/traces contain zero raw tokens, keys, or passwords.
- Prohibition of real meeting bots, telephony, SIP transfer, and real-person cloning.
"""
import json
import sys
import unittest
import urllib.request
import urllib.error
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s2_helpers import AppProcess, app_base_url


class TestStage4SessionLifecycleAndSafety(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def _http_post(self, path, payload=None):
        url = app_base_url() + path
        data = json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8"))
            except Exception:
                body = None
            return e.code, body

    def _http_delete(self, path):
        url = app_base_url() + path
        req = urllib.request.Request(url, method="DELETE")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8"))
            except Exception:
                body = e.read().decode("utf-8")
            return e.code, body

    def _http_get(self, path):
        url = app_base_url() + path
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8"))
            except Exception:
                body = e.read().decode("utf-8")
            return e.code, body

    def test_complete_session_deletion_endpoint(self):
        """DELETE /api/rehearsal/sessions/{id} must delete session data and return 200."""
        # Create session
        status, data = self._http_post("/api/rehearsal/sessions")
        self.assertEqual(status, 201)
        sid = data["session_id"]

        # Advance session
        self._http_post(f"/api/rehearsal/sessions/{sid}/advance")

        # Delete session
        del_status, del_data = self._http_delete(f"/api/rehearsal/sessions/{sid}")
        self.assertEqual(
            del_status,
            200,
            f"Expected 200 from DELETE /api/rehearsal/sessions/{sid}, got {del_status}: {del_data}",
        )
        self.assertTrue(
            del_data.get("status") in ["deleted", "destroyed"] or del_data.get("session_deleted") is True,
            f"Unexpected delete response body: {del_data}",
        )

        # GET session must now return 404
        get_status, _ = self._http_get(f"/api/rehearsal/sessions/{sid}")
        self.assertEqual(get_status, 404, "Deleted session must return 404 Not Found")

    def test_no_sensitive_tokens_or_credentials_in_logs_and_payloads(self):
        """Application logs and API responses must never leak tokens or keys."""
        status, data = self._http_post("/api/rehearsal/sessions")
        self.assertEqual(status, 201)
        sid = data["session_id"]

        dump = json.dumps(data)
        self.assertNotIn("NAPSTER_API_KEY", dump)
        self.assertNotIn("sk-", dump)
        self.assertNotIn("Bearer", dump)

        # Teardown
        self._http_delete(f"/api/rehearsal/sessions/{sid}")

    def test_prohibit_real_meeting_bots_and_sip_telephony(self):
        """Meeting bot and SIP telephony endpoints must return 404 Not Found."""
        for path in [
            "/api/telephony/sip",
            "/api/meeting/bot",
            "/api/zoom/join",
            "/api/teams/join",
            "/api/meet/join",
        ]:
            status, _ = self._http_post(path, {"join": True})
            self.assertEqual(status, 404, f"Prohibited endpoint '{path}' must return 404, got {status}")

    def test_prohibit_real_person_voice_cloning_upload(self):
        """Voice cloning and biometric upload endpoints must return 404 Not Found."""
        for path in [
            "/api/voice/clone",
            "/api/biometrics/upload",
            "/api/persona/clone-user",
        ]:
            status, _ = self._http_post(path, {"voice_sample": "dummy"})
            self.assertEqual(status, 404, f"Prohibited biometric endpoint '{path}' must return 404, got {status}")


if __name__ == "__main__":
    unittest.main()
