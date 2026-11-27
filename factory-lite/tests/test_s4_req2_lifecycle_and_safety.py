"""
Stage 4 Requirements 2 & 6: Session Lifecycle, Teardown Boundary, and Safety Prohibitions.

Validates complete root session deletion (DELETE /api/rehearsal/sessions/{id}),
sah.cleanup.v1 receipt contract, observed test-owned fake vendor cleanup boundary
call counts (first DELETE causes exactly 1 teardown, repeated DELETE causes 0 additional teardowns),
injected cleanup failure resource retention, mid-session consent withdrawal,
sanitization of injected sensitive markers across responses, logs, and evidence,
and strict meeting bot (P-06) and voice cloning (P-04) rejections.
"""

import http.server
import json
import os
import threading
import time
import unittest

from s4_constants import (
    RULE_P04,
    RULE_P06,
    SCHEMA_VERSION_CLEANUP,
)
from s4_helpers import AppProcess, delete_json, get_json, post_json


class FakeVendorBoundaryHandler(http.server.BaseHTTPRequestHandler):
    def do_DELETE(self):
        if getattr(self.server, "inject_failure", False):
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "upstream_cleanup_failure"}).encode())
            return

        req_record = {
            "method": "DELETE",
            "path": self.path,
            "headers": dict(self.headers),
            "timestamp": time.time(),
        }
        self.server.request_log.append(req_record)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "destroyed", "path": self.path}).encode())

    def do_POST(self):
        req_record = {
            "method": "POST",
            "path": self.path,
            "headers": dict(self.headers),
            "timestamp": time.time(),
        }
        self.server.request_log.append(req_record)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

    def log_message(self, format, *args):
        pass


class TestOwnedCleanupBoundary:
    def __init__(self):
        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), FakeVendorBoundaryHandler)
        self.httpd.request_log = []
        self.httpd.inject_failure = False
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return self.httpd.server_address[1]

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def get_requests(self) -> list:
        return list(self.httpd.request_log)

    def set_inject_failure(self, fail: bool):
        self.httpd.inject_failure = fail

    def clear(self):
        self.httpd.request_log.clear()
        self.httpd.inject_failure = False

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.httpd.shutdown()
        self.httpd.server_close()


class TestStage4SessionLifecycleAndSafety(unittest.TestCase):
    fake_boundary = None
    app_process = None

    @classmethod
    def setUpClass(cls):
        cls.fake_boundary = TestOwnedCleanupBoundary()
        cls.fake_boundary.__enter__()
        os.environ["NAPSTER_BASE_URL"] = cls.fake_boundary.base_url
        os.environ["NAPSTER_API_KEY"] = "test-fake-key"
        cls.app_process = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app_process is not None:
            cls.app_process.stop()
        if cls.fake_boundary is not None:
            cls.fake_boundary.__exit__(None, None, None)
        os.environ.pop("NAPSTER_BASE_URL", None)
        os.environ.pop("NAPSTER_API_KEY", None)

    def setUp(self):
        self.fake_boundary.clear()

    def _create_session(self) -> str:
        status, data = post_json(
            "/api/rehearsal/sessions",
            {"scenario": "alex_dana", "mode": "offline"},
        )
        self.assertEqual(status, 201, f"Failed to create session: {data}")
        return data["session_id"]

    def test_complete_session_deletion_endpoint_and_inaccessibility(self):
        """
        DELETE /api/rehearsal/sessions/{id} deletes the session, invokes the upstream boundary,
        and ensures subsequent access returns 404 Not Found.
        """
        session_id = self._create_session()

        initial_count = len([r for r in self.fake_boundary.get_requests() if r["method"] == "DELETE"])
        del_status, del_data = delete_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(
            del_status,
            200,
            f"Expected 200 from DELETE /api/rehearsal/sessions/{session_id}, got {del_status}: {del_data}",
        )

        self.assertIn("schema_version", del_data)
        self.assertEqual(del_data["schema_version"], SCHEMA_VERSION_CLEANUP)
        self.assertIn("session_deleted", del_data)
        self.assertEqual(del_data["session_deleted"], True)
        self.assertIn("session_id", del_data)
        self.assertEqual(del_data["session_id"], session_id)
        self.assertIn("transcript_deleted", del_data)
        self.assertEqual(del_data["transcript_deleted"], True)
        self.assertIn("media_released", del_data)
        self.assertEqual(del_data["media_released"], True)
        self.assertIn("upstream_teardown_performed", del_data)
        self.assertEqual(del_data["upstream_teardown_performed"], True)
        self.assertIn("failures", del_data)
        self.assertIsInstance(del_data["failures"], list)

        # Boundary call count verification
        observed_teardowns = len([r for r in self.fake_boundary.get_requests() if r["method"] == "DELETE"])
        self.assertEqual(
            observed_teardowns - initial_count,
            1,
            "Initial session cleanup must cause exactly 1 upstream teardown call",
        )

        # Following deletion, subsequent GET must return 404
        get_status, get_data = get_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(
            get_status,
            404,
            f"Expected 404 for deleted session, got {get_status}: {get_data}",
        )

    def test_cleanup_receipt_contract_and_idempotent_repeated_cleanup(self):
        """
        DELETE /api/rehearsal/sessions/{id} returns sah.cleanup.v1 receipt.
        First DELETE causes 1 teardown; repeated deletion causes 0 additional teardowns.
        """
        session_id = self._create_session()

        # First cleanup
        del_status1, data1 = delete_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(del_status1, 200, f"Initial cleanup failed: {data1}")
        self.assertIn("schema_version", data1)
        self.assertEqual(data1["schema_version"], SCHEMA_VERSION_CLEANUP)
        self.assertIn("session_deleted", data1)
        self.assertEqual(data1["session_deleted"], True)
        self.assertIn("upstream_teardown_performed", data1)
        self.assertEqual(data1["upstream_teardown_performed"], True)

        first_count = len([r for r in self.fake_boundary.get_requests() if r["method"] == "DELETE"])
        self.assertEqual(first_count, 1, "First DELETE must perform exactly one teardown call")

        # Repeated cleanup: must be safe, idempotent, and add 0 upstream teardowns
        del_status2, data2 = delete_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(
            del_status2,
            200,
            f"Repeated cleanup must return 200, got {del_status2}: {data2}",
        )
        self.assertIn("schema_version", data2)
        self.assertEqual(data2["schema_version"], SCHEMA_VERSION_CLEANUP)
        self.assertIn("session_deleted", data2)
        self.assertEqual(data2["session_deleted"], True)
        self.assertIn("upstream_teardown_performed", data2)
        self.assertEqual(
            data2["upstream_teardown_performed"],
            False,
            "Repeated cleanup must not execute duplicate upstream teardown",
        )

        second_count = len([r for r in self.fake_boundary.get_requests() if r["method"] == "DELETE"])
        self.assertEqual(
            second_count - first_count,
            0,
            "Repeated cleanup must add 0 additional teardown calls",
        )

    def test_injected_cleanup_failure_retains_session_handle(self):
        """
        When upstream cleanup boundary fails (500), deletion must report failure
        and explicitly retain the session handle/resource rather than destroying it silently.
        """
        session_id = self._create_session()
        self.fake_boundary.set_inject_failure(True)

        del_status, del_data = delete_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(del_status, 502, f"Expected 502 on cleanup failure, got {del_status}")
        self.assertIn("upstream_teardown_performed", del_data)
        self.assertEqual(del_data["upstream_teardown_performed"], False)

        # Handle/resource must remain accessible and retained
        get_status, get_data = get_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(
            get_status,
            200,
            "Session handle must be retained when upstream teardown fails",
        )

    def test_mid_session_consent_withdrawal_stops_activity(self):
        """
        POST /api/rehearsal/sessions/{id}/consent/withdraw immediately withdraws consent,
        disabling further turns and marking session terminated.
        """
        session_id = self._create_session()

        post_json(
            f"/api/rehearsal/sessions/{session_id}/advance",
            {"to": "take_my_seat"},
        )

        w_status, w_data = post_json(
            f"/api/rehearsal/sessions/{session_id}/consent/withdraw",
            {"scope": "all", "reason": "user_withdrew"},
        )
        self.assertEqual(w_status, 200)
        self.assertIn("consent_active", w_data)
        self.assertEqual(w_data["consent_active"], False)
        self.assertIn("state", w_data)
        self.assertEqual(w_data["state"], "withdrawn")

        # Further turns or advances must be rejected with 409
        adv_status, adv_data = post_json(
            f"/api/rehearsal/sessions/{session_id}/advance",
            {"to": "practice"},
        )
        self.assertEqual(adv_status, 409)

    def test_injected_marker_sanitization_across_responses_and_evidence(self):
        """
        Injects distinct sensitive markers (token, credential, raw vendor ID,
        prohibited utterance, biometric vector, audio marker) into requests.
        Asserts complete absence across response payloads and evidence logs.
        """
        session_id = self._create_session()

        marker_token = "TEST_TOKEN_SECRET_98765"
        marker_cred = "sk-live-testcredential-12345"
        marker_vendor_id = "raw_vendor_id_xyz_999"
        marker_prohibited = "PROHIBITED_UTTERANCE_INJECTED_FOO"
        marker_biometric = "BIOMETRIC_MARKER_RAW_FEATURE_VECTOR_888"
        marker_media = "AUDIO_RAW_MARKER_DATA_111"

        injection_payload = {
            "token": marker_token,
            "credential": marker_cred,
            "vendor_id": marker_vendor_id,
            "prohibited": marker_prohibited,
            "biometric": marker_biometric,
            "media": marker_media,
        }

        # Submit injection via turn / advance
        post_json(f"/api/rehearsal/sessions/{session_id}/advance", injection_payload)

        # Inspect session GET payload
        _, sess_data = get_json(f"/api/rehearsal/sessions/{session_id}")
        sess_str = json.dumps(sess_data)

        self.assertNotIn(marker_token, sess_str)
        self.assertNotIn(marker_cred, sess_str)
        self.assertNotIn(marker_vendor_id, sess_str)
        self.assertNotIn(marker_prohibited, sess_str)
        self.assertNotIn(marker_biometric, sess_str)
        self.assertNotIn(marker_media, sess_str)

        # Inspect evidence payload
        _, ev_data = get_json(f"/api/rehearsal/sessions/{session_id}/evidence")
        ev_str = json.dumps(ev_data)

        self.assertNotIn(marker_token, ev_str)
        self.assertNotIn(marker_cred, ev_str)
        self.assertNotIn(marker_vendor_id, ev_str)
        self.assertNotIn(marker_prohibited, ev_str)
        self.assertNotIn(marker_biometric, ev_str)
        self.assertNotIn(marker_media, ev_str)

    def test_strict_meeting_bot_and_voice_cloning_prohibition(self):
        """
        Enforces strict rejection of external meeting bot integrations (Zoom, Meet)
        and custom voice cloning attempts with exact 400 and exact rule codes.
        """
        session_id = self._create_session()

        meet_payload = {
            "action": "join_meeting",
            "meeting_url": "https://meet.google.com/abc-defg-hij",
        }
        m_status, m_data = post_json(
            f"/api/rehearsal/sessions/{session_id}/advance",
            meet_payload,
        )
        self.assertEqual(m_status, 400, f"Meeting integration must return exact 400, got {m_status}: {m_data}")
        self.assertEqual(m_data["rule_id"], RULE_P06)

        clone_payload = {
            "to": "take_my_seat",
            "voice": {"cloned_voice_id": "victim-voice-sample-01"},
        }
        c_status, c_data = post_json(
            f"/api/rehearsal/sessions/{session_id}/advance",
            clone_payload,
        )
        self.assertEqual(c_status, 400, f"Voice cloning must return exact 400, got {c_status}: {c_data}")
        self.assertEqual(c_data["rule_id"], RULE_P04)


if __name__ == "__main__":
    unittest.main()
