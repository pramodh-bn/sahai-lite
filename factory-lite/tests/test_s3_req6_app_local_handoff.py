"""Requirement 6: App-local handoff contract and prohibition of external telephony/SIP/cloning.

Contract conventions:
- Sah handoff is app-local:
    completed embodied demonstration -> Take My Seat -> practice ready.
- Strictly forbidden:
    * SIP transfer / telephony dialing (sip:, tel:)
    * Meeting join / relay / control (Zoom, Teams, Meet, Chime bots)
    * Real-person voice cloning / voiceprint imitation
"""
import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s2_helpers import AppProcess, app_base_url


class TestAppLocalHandoffAndRestrictions(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def setUp(self):
        req = urllib.request.Request(
            f"{app_base_url()}/api/rehearsal/sessions",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.session_id = data["session_id"]

    def _post(self, path, body):
        req = urllib.request.Request(
            f"{app_base_url()}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read().decode("utf-8"))
            except Exception:
                return exc.code, {}

    def test_sah_handoff_is_app_local_through_deterministic_states(self):
        with urllib.request.urlopen(f"{app_base_url()}/api/rehearsal/sessions/{self.session_id}", timeout=5) as resp:
            snap = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(snap["state"], "demo")

        status1, data1 = self._post(f"/api/rehearsal/sessions/{self.session_id}/advance", {"to": "take_my_seat"})
        self.assertEqual(status1, 200)
        self.assertEqual(data1["state"], "take_my_seat")

        status2, data2 = self._post(f"/api/rehearsal/sessions/{self.session_id}/advance", {"to": "practice"})
        self.assertEqual(status2, 200)
        self.assertEqual(data2["state"], "practice")

    def test_forbid_sip_telephony_transfer(self):
        payloads = [
            {"to": "practice", "sip_uri": "sip:user@gateway.internal"},
            {"to": "practice", "phone_number": "+15550199"},
            {"transfer_protocol": "sip"},
        ]
        for p in payloads:
            with self.subTest(payload=p):
                status, _ = self._post(f"/api/rehearsal/sessions/{self.session_id}/advance", p)
                self.assertIn(status, (400, 404, 409), f"SIP/telephony construct must be rejected: {p}")

    def test_forbid_meeting_bot_join_and_control(self):
        meeting_payloads = [
            {"meeting_url": "https://zoom.us/j/123456789"},
            {"meeting_url": "https://teams.microsoft.com/l/meetup-join/123"},
            {"meeting_platform": "chime"},
        ]
        for p in meeting_payloads:
            with self.subTest(payload=p):
                status, _ = self._post(f"/api/rehearsal/sessions/{self.session_id}/advance", p)
                self.assertIn(status, (400, 404, 409), f"Meeting join/relay construct must be rejected: {p}")

    def test_forbid_real_person_voice_cloning(self):
        clone_payloads = [
            {"utterance": "Hello", "clone_target_speaker": "Alex Real Person"},
            {"voiceprint_id": "vp_987654321"},
            {"voice_cloning_enabled": True},
        ]
        for p in clone_payloads:
            with self.subTest(payload=p):
                status, _ = self._post(f"/api/rehearsal/sessions/{self.session_id}/practice", p)
                self.assertIn(status, (400, 404, 409), f"Voice cloning construct must be rejected: {p}")


if __name__ == "__main__":
    unittest.main()
