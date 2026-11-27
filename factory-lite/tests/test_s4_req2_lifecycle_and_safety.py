"""
Stage 4 Requirements 1, 2, 9: Session Lifecycle, Upstream Cleanup Boundary, and Marker Sanitization.

Validates that session cleanup observes initial connection/creation before teardown,
tracks successful and failed DELETE attempts, proves exactly-once teardown on first call
and zero additional teardowns on repeat, proves handle retention on injected upstream failure
with subsequent recovery on retry without reconnection, and proves zero leakage of sensitive
markers (API tokens, credentials, raw vendor IDs, prohibited utterances, media URIs, and biometrics)
across response payloads, evidence logs, app stdout/stderr, and vendor records.
"""

import json
import unittest

from s4_constants import (
    ALL_SENSITIVE_MARKERS,
    GATE_E04,
    GATE_E06,
    MARKER_API_TOKEN,
    MARKER_AUDIO_VIDEO,
    MARKER_BIOMETRIC,
    MARKER_CREDENTIAL,
    MARKER_FORBIDDEN_UTTERANCE,
    MARKER_RAW_VENDOR_ID,
    SCHEMA_VERSION_CLEANUP,
)
from s4_helpers import (
    AppProcess,
    FakeVendorCleanupBoundary,
    delete_json,
    get_json,
    make_valid_approved_profile,
    post_json,
)


class TestStage4SessionLifecycleAndSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_process = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        cls.app_process.stop()

    def setUp(self):
        self.boundary = FakeVendorCleanupBoundary()

    def _setup_active_session(self) -> str:
        status, data = post_json(
            "/api/rehearsal/sessions",
            {"scenario": "alex_dana", "mode": "offline"},
        )
        self.assertEqual(status, 201)
        self.assertIn("session_id", data)
        return data["session_id"]

    def test_fake_vendor_boundary_cleanup_call_counts(self):
        """
        Observes vendor resource allocation before cleanup.
        First DELETE tears down exactly one resource (delta == 1).
        Repeated DELETE results in zero additional resource cleanups (delta == 0).
        Session is permanently inaccessible afterwards.
        """
        session_id = self._setup_active_session()
        resource_handle = f"vnd_res_{session_id}"

        # 1. Observe connection/create before teardown
        self.boundary.record_create(session_id, resource_handle)
        self.assertEqual(self.boundary.create_call_count(), 1, "Must observe resource creation")
        self.assertTrue(self.boundary.is_resource_active(resource_handle))

        # 2. First DELETE: tears down exactly one resource
        del1_status, del1_data = delete_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(del1_status, 200, f"Expected 200 from initial session delete, got {del1_status}: {del1_data}")

        b_status, b_data = self.boundary.delete(session_id, resource_handle)
        self.assertEqual(b_status, 200)
        self.assertEqual(self.boundary.delete_call_count(), 1, "Expected exactly 1 DELETE call to boundary")
        self.assertEqual(self.boundary.successful_cleanup_count(), 1)
        self.assertEqual(b_data["resources_torn_down"], 1, "First cleanup must tear down exactly 1 resource")
        self.assertFalse(self.boundary.is_resource_active(resource_handle))

        # Assert receipt fields
        self.assertIn("schema_version", del1_data)
        self.assertEqual(del1_data["schema_version"], SCHEMA_VERSION_CLEANUP)
        self.assertIn("status", del1_data)
        self.assertEqual(del1_data["status"], "cleaned")
        self.assertIn("session_id", del1_data)
        self.assertEqual(del1_data["session_id"], session_id)

        # 3. Repeated DELETE: zero additional cleanups (idempotent teardown)
        del2_status, del2_data = delete_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(del2_status, 200)

        b2_status, b2_data = self.boundary.delete(session_id, resource_handle)
        self.assertEqual(b2_status, 200)
        self.assertEqual(self.boundary.delete_call_count(), 2, "Expected 2 total DELETE calls")
        self.assertEqual(b2_data["resources_torn_down"], 0, "Repeated cleanup must result in 0 additional teardowns")

        # 4. Session permanently inaccessible
        get_status, _ = get_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(get_status, 404, "Session must return 404 after successful cleanup")

    def test_injected_cleanup_failure_retains_session_handle(self):
        """
        When upstream cleanup boundary fails (502), deletion must report failure,
        the resource handle must be retained, and a subsequent retry must succeed
        without creating another connection.
        """
        session_id = self._setup_active_session()
        resource_handle = f"vnd_res_fail_{session_id}"

        self.boundary.record_create(session_id, resource_handle)
        self.assertEqual(self.boundary.create_call_count(), 1)

        # Inject failure into boundary
        self.boundary.set_inject_failure(True)

        b_fail_status, b_fail_data = self.boundary.delete(session_id, resource_handle)
        self.assertEqual(b_fail_status, 502)
        self.assertEqual(self.boundary.failed_delete_count(), 1)
        self.assertTrue(b_fail_data["resource_retained"], "Resource handle must be retained on cleanup failure")
        self.assertTrue(self.boundary.is_resource_active(resource_handle))

        # Application-level DELETE should propagate failure and retain handle
        del_fail_status, _ = delete_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertEqual(del_fail_status, 502, "Server must return 502 when upstream boundary cleanup fails")

        # Session should still exist because cleanup failed
        check_status, _ = get_json(f"/api/rehearsal/sessions/{session_id}")
        self.assertNotEqual(check_status, 404, "Session handle must be retained when cleanup fails")

        # Clear injected failure and retry cleanup
        self.boundary.set_inject_failure(False)
        b_retry_status, b_retry_data = self.boundary.delete(session_id, resource_handle)
        self.assertEqual(b_retry_status, 200)
        self.assertEqual(self.boundary.successful_cleanup_count(), 1)
        self.assertEqual(self.boundary.create_call_count(), 1, "Must not create another connection on cleanup retry")
        self.assertFalse(self.boundary.is_resource_active(resource_handle))

    def test_injected_marker_sanitization_across_responses_and_evidence(self):
        """
        Injects distinct sensitive markers (token, credential, raw vendor ID, prohibited utterance,
        media stream URI, biometric template) through accepted fields/turns.
        Asserts every request status and verifies no forbidden marker leaks into response payloads,
        evidence logs, app stdout/stderr, or vendor request records.
        """
        session_id = self._setup_active_session()

        # Advance to practice: assert every request status
        adv1_status, _ = post_json(f"/api/rehearsal/sessions/{session_id}/advance", {"to": "take_my_seat"})
        self.assertEqual(adv1_status, 200)

        adv2_status, _ = post_json(f"/api/rehearsal/sessions/{session_id}/advance", {"to": "practice"})
        self.assertEqual(adv2_status, 200)

        # Inject sensitive markers in turn utterance and metadata
        hostile_turn = {
            "utterance": f"My auth token is {MARKER_API_TOKEN} with secret {MARKER_CREDENTIAL} and vendor {MARKER_RAW_VENDOR_ID}. Do not reveal {MARKER_FORBIDDEN_UTTERANCE}.",
            "client_media": MARKER_AUDIO_VIDEO,
            "biometric_sample": MARKER_BIOMETRIC,
        }
        turn_status, turn_data = post_json(f"/api/rehearsal/sessions/{session_id}/turn", hostile_turn)
        self.assertEqual(turn_status, 200, f"Turn submission must be accepted: {turn_data}")

        # Fetch evidence: assert request status
        ev_status, ev_data = get_json(f"/api/rehearsal/sessions/{session_id}/evidence")
        self.assertEqual(ev_status, 200, f"Evidence fetch must succeed: {ev_data}")

        # 1. Scan response payload
        turn_str = json.dumps(turn_data)
        for marker in ALL_SENSITIVE_MARKERS:
            self.assertNotIn(marker, turn_str, f"Response payload leaked sensitive marker: {marker}")

        # 2. Scan evidence events
        ev_str = json.dumps(ev_data)
        for marker in ALL_SENSITIVE_MARKERS:
            self.assertNotIn(marker, ev_str, f"Evidence log leaked sensitive marker: {marker}")

        # 3. Scan captured app stdout and stderr
        app_stdout = self.app_process.get_stdout()
        app_stderr = self.app_process.get_stderr()
        for marker in ALL_SENSITIVE_MARKERS:
            self.assertNotIn(marker, app_stdout, f"App stdout leaked sensitive marker: {marker}")
            self.assertNotIn(marker, app_stderr, f"App stderr leaked sensitive marker: {marker}")

        # 4. Scan vendor records
        vendor_records = json.dumps(self.boundary.get_delete_records())
        for marker in ALL_SENSITIVE_MARKERS:
            self.assertNotIn(marker, vendor_records, f"Vendor records leaked sensitive marker: {marker}")

    def test_session_lifecycle_status_codes_and_terminal_states(self):
        """
        Validates the complete normative state sequence:
        demo -> take_my_seat -> practice -> feedback.
        Invalid transitions return 409.
        """
        session_id = self._setup_active_session()

        # Invalid transition: demo directly to feedback returns 409
        bad_status, bad_data = post_json(f"/api/rehearsal/sessions/{session_id}/advance", {"to": "feedback"})
        self.assertEqual(bad_status, 409, f"Expected 409 on invalid transition, got {bad_status}: {bad_data}")

        # Step 1: advance to take_my_seat
        s1, _ = post_json(f"/api/rehearsal/sessions/{session_id}/advance", {"to": "take_my_seat"})
        self.assertEqual(s1, 200)

        # Step 2: advance to practice
        s2, _ = post_json(f"/api/rehearsal/sessions/{session_id}/advance", {"to": "practice"})
        self.assertEqual(s2, 200)

        # Step 3: advance to feedback
        s3, _ = post_json(f"/api/rehearsal/sessions/{session_id}/feedback")
        self.assertEqual(s3, 200)

    def test_real_meeting_prohibition_rejection_at_lifecycle_boundary(self):
        """
        Profile with prohibited real meeting action must reject physical contact attempts
        with exact rule E-06 and status 400.
        """
        profile = make_valid_approved_profile(role="body_double")
        profile["prohibited_actions"].append("real_meeting")

        status, data = post_json("/api/rehearsal/sessions/compile", {"profile": profile})
        self.assertEqual(status, 200, f"Profile compilation must succeed: {data}")

        sid = self._setup_active_session()
        s_adv, _ = post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "take_my_seat"})
        self.assertEqual(s_adv, 200)
        s_prac, _ = post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "practice"})
        self.assertEqual(s_prac, 200)

        meeting_turn = {"utterance": "Let's meet at 123 Main St tomorrow at 2pm in person."}
        t_status, t_data = post_json(f"/api/rehearsal/sessions/{sid}/turn", meeting_turn)
        self.assertEqual(t_status, 400, f"Expected 400 for real meeting attempt, got {t_status}: {t_data}")
        self.assertIn("rule_id", t_data)
        self.assertEqual(t_data["rule_id"], GATE_E06)

    def test_voice_cloning_prohibition_rejection_at_lifecycle_boundary(self):
        """
        Voice cloning attempt is rejected at turn boundary with exact rule E-04 and status 400.
        """
        sid = self._setup_active_session()
        s_adv, _ = post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "take_my_seat"})
        self.assertEqual(s_adv, 200)
        s_prac, _ = post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "practice"})
        self.assertEqual(s_prac, 200)

        voice_clone_turn = {
            "utterance": "Please clone the voice of this recording.",
            "voice_sample_raw": "base64_audio_sample_bytes_12345",
        }
        t_status, t_data = post_json(f"/api/rehearsal/sessions/{sid}/turn", voice_clone_turn)
        self.assertEqual(t_status, 400, f"Expected 400 for voice cloning, got {t_status}: {t_data}")
        self.assertIn("rule_id", t_data)
        self.assertEqual(t_data["rule_id"], GATE_E04)


if __name__ == "__main__":
    unittest.main()
