"""Stage 2 (factory-lite/spec/stage-2.md): "Deterministic transitions stand-in
demonstration -> Take My Seat -> practice -> feedback -> retry."

Contract convention (see CONTRACT.md "Stage 2 rehearsal API"): sessions are
created via POST /api/rehearsal/sessions and start in state "demo". The
only valid `advance` transitions are demo->take_my_seat and
take_my_seat->practice; practice->feedback happens only via the dedicated
/feedback endpoint and feedback->practice only via /retry (covered in
test_s2_req4). Any other `advance` target, or acting on a nonexistent
session, must be rejected deterministically (HTTP 409 / 404), not silently
accepted.

This is a true black-box check against the real running service (the
documented Req 1 startup command); it never imports application code.
"""
import unittest

from s2_helpers import AppProcess, git_head_sha, post_json, get_json


class TestDeterministicTransitions(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def test_new_session_starts_in_demo_state_for_alex_dana_scenario(self):
        status, body = post_json("/api/rehearsal/sessions")
        self.assertEqual(status, 201, f"body={body}")
        self.assertEqual(body.get("state"), "demo")
        self.assertEqual(body.get("scenario"), "alex_dana")
        self.assertTrue(body.get("session_id"), "session_id missing/empty")

    def test_valid_transition_sequence_is_deterministic(self):
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]

        status, body = post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "take_my_seat"})
        self.assertEqual(status, 200, f"body={body}")
        self.assertEqual(body.get("state"), "take_my_seat")

        status, body = post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "practice"})
        self.assertEqual(status, 200, f"body={body}")
        self.assertEqual(body.get("state"), "practice")

        # Reading state back must agree with what advance returned.
        status, snapshot = get_json(f"/api/rehearsal/sessions/{sid}")
        self.assertEqual(status, 200)
        self.assertEqual(snapshot.get("state"), "practice")

    def test_invalid_transition_from_demo_directly_to_practice_is_rejected(self):
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "practice"})
        self.assertEqual(status, 409, f"body={body}")
        self.assertEqual(body.get("error"), "invalid_transition")

    def test_invalid_transition_to_unknown_state_is_rejected(self):
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "not_a_real_state"})
        self.assertEqual(status, 409, f"body={body}")

    def test_advance_on_unknown_session_is_not_found(self):
        status, body = post_json("/api/rehearsal/sessions/does-not-exist/advance", {"to": "take_my_seat"})
        self.assertEqual(status, 404, f"body={body}")

    def test_repeating_the_same_valid_advance_twice_is_rejected_the_second_time(self):
        """Transitions are one-shot and deterministic: once in take_my_seat,
        advancing to take_my_seat again is not a no-op success."""
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "take_my_seat"})
        self.assertEqual(status, 200, f"body={body}")
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "take_my_seat"})
        self.assertEqual(status, 409, f"body={body}")


if __name__ == "__main__":
    unittest.main()
