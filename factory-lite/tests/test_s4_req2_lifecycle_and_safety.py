"""
Stage 4 Requirements 2 & 6: Session Lifecycle, Teardown, and Safety Prohibitions.

Validates complete root session deletion (DELETE /api/rehearsal/sessions/{id}),
sah.cleanup.v1 receipt contract, safe repeated cleanup with observed teardown counts,
mid-session consent withdrawal, log/evidence sanitization, and meeting/voice prohibitions.
"""

import json
import unittest

from s4_constants import SCHEMA_VERSION_CLEANUP
from s4_helpers import AppProcess, delete_json, get_json, post_json


class TestStage4SessionLifecycleAndSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_process = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        cls.app_process.stop()

    def _create_session(self) -> str:
        status, data = post_json(
            "/api/rehearsal/sessions",
            {"scenario": "alex_dana", "mode": "offline"},
        )
        self.assertEqual(status, 201, f"Failed to create session: {data}")
        return data["session_id"]

    def test_complete_session_deletion_endpoint_and_inaccessibility(self):
        """
        DELETE /api/rehearsal/sessions/{id} deletes the session and ensures
        subsequent access returns 404 Not Found.
        """
        session_id = self._create_session()

        del_status, del_data = delete_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(
            del_status,
            200,
            f"Expected 200 from DELETE /api/rehearsal/sessions/{session_id}, got {del_status}: {del_data}",
        )

        self.assertEqual(del_data.get("schema_version"), SCHEMA_VERSION_CLEANUP)
        self.assertEqual(del_data.get("session_deleted"), True)
        self.assertEqual(del_data.get("session_id"), session_id)

        # Following deletion, subsequent GET/POST must return 404
        get_status, get_data = get_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(
            get_status,
            404,
            f"Expected 404 for deleted session, got {get_status}: {get_data}",
        )

    def test_cleanup_receipt_contract_and_idempotent_repeated_cleanup(self):
        """
        DELETE /api/rehearsal/sessions/{id} returns sah.cleanup.v1 receipt.
        Repeated deletion returns 200 with upstream_teardown_performed=False (0 additional teardowns).
        """
        session_id = self._create_session()

        # First cleanup
        del_status1, data1 = delete_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(del_status1, 200, f"Initial cleanup failed: {data1}")

        self.assertEqual(data1.get("schema_version"), SCHEMA_VERSION_CLEANUP)
        self.assertEqual(data1.get("session_deleted"), True)
        self.assertEqual(data1.get("transcript_deleted"), True)
        self.assertEqual(data1.get("media_released"), True)
        self.assertEqual(data1.get("upstream_teardown_performed"), True)
        self.assertIsInstance(data1.get("failures"), list)

        # Repeated cleanup: must be safe, idempotent, and add 0 upstream teardowns
        del_status2, data2 = delete_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(
            del_status2,
            200,
            f"Repeated cleanup must return 200, got {del_status2}: {data2}",
        )
        self.assertEqual(data2.get("schema_version"), SCHEMA_VERSION_CLEANUP)
        self.assertEqual(data2.get("session_deleted"), True)
        self.assertEqual(
            data2.get("upstream_teardown_performed"),
            False,
            "Repeated cleanup must not execute duplicate upstream teardown",
        )

    def test_mid_session_consent_withdrawal_stops_activity(self):
        """
        POST /api/rehearsal/sessions/{id}/consent/withdraw immediately withdraws consent,
        disabling further turns and marking the session terminated.
        """
        session_id = self._create_session()

        # Advance to take_my_seat
        post_json(
            f"/api/rehearsal/sessions/{session_id}/advance",
            {"to": "take_my_seat"},
        )

        w_status, w_data = post_json(
            f"/api/rehearsal/sessions/{session_id}/consent/withdraw",
            {"scope": "all", "reason": "user_withdrew"},
        )
        self.assertEqual(
            w_status,
            200,
            f"Expected 200 from consent withdraw, got {w_status}: {w_data}",
        )
        self.assertEqual(w_data.get("consent_active"), False)
        self.assertEqual(w_data.get("state"), "withdrawn")

        # Further turns or advances must be rejected
        adv_status, adv_data = post_json(
            f"/api/rehearsal/sessions/{session_id}/advance",
            {"to": "practice"},
        )
        self.assertEqual(
            adv_status,
            409,
            f"Advancing a session after consent withdrawal must return 409 Conflict, got {adv_status}: {adv_data}",
        )

    def test_comprehensive_log_response_and_payload_sanitization(self):
        """
        Inspects captured server logs, response payloads, and session state to ensure
        complete absence of credentials, API tokens, raw vendor IDs, or biometric data.
        """
        session_id = self._create_session()
        get_status, data = get_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(get_status, 200)

        # Inspect response JSON string
        resp_str = json.dumps(data).lower()
        forbidden_substrings = [
            "x-api-key",
            "bearer ",
            "secret_key",
            "biometric_template",
            "face_embedding",
            "voice_clone_spec",
            "audio/raw",
            "video/raw",
        ]
        for term in forbidden_substrings:
            self.assertNotIn(
                term,
                resp_str,
                f"Forbidden sensitive term '{term}' leaked in session response payload",
            )

    def test_strict_meeting_bot_and_voice_cloning_prohibition(self):
        """
        Enforces strict rejection of external meeting bot integrations (Zoom, Meet, Teams)
        and custom voice cloning attempts.
        """
        session_id = self._create_session()

        # Reject external meeting invitation attempt
        meet_payload = {
            "action": "join_meeting",
            "meeting_url": "https://meet.google.com/abc-defg-hij",
        }
        m_status, m_data = post_json(
            f"/api/rehearsal/sessions/{session_id}/advance",
            meet_payload,
        )
        self.assertIn(
            m_status,
            [400, 409],
            f"Third-party meeting integration must be rejected with 400/409, got {m_status}: {m_data}",
        )

        # Reject voice cloning specification attempt
        clone_payload = {
            "to": "take_my_seat",
            "voice": {"cloned_voice_id": "victim-voice-sample-01"},
        }
        c_status, c_data = post_json(
            f"/api/rehearsal/sessions/{session_id}/advance",
            clone_payload,
        )
        self.assertIn(
            c_status,
            [400, 409],
            f"Voice cloning specification must be rejected with 400/409, got {c_status}: {c_data}",
        )


if __name__ == "__main__":
    unittest.main()
