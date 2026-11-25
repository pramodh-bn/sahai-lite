"""Stage 2: "Test invalid transitions, isolation, replay and deterministic
scoring."

Isolation: two concurrently open sessions must not share or leak state.
Replay: re-issuing the same read (or the same already-applied action)
must not silently corrupt state or double-advance it; acting against a
session that does not exist is always rejected, regardless of how many
other sessions exist.
"""
import unittest

from s2_helpers import AppProcess, post_json, get_json


class TestIsolationAndReplay(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def test_two_sessions_are_isolated_from_each_other(self):
        _, created_a = post_json("/api/rehearsal/sessions")
        _, created_b = post_json("/api/rehearsal/sessions")
        sid_a, sid_b = created_a["session_id"], created_b["session_id"]
        self.assertNotEqual(sid_a, sid_b)

        post_json(f"/api/rehearsal/sessions/{sid_a}/advance", {"to": "take_my_seat"})
        post_json(f"/api/rehearsal/sessions/{sid_a}/advance", {"to": "practice"})
        post_json(f"/api/rehearsal/sessions/{sid_a}/practice", {"utterance": "What is your budget?"})

        status, snapshot_b = get_json(f"/api/rehearsal/sessions/{sid_b}")
        self.assertEqual(status, 200)
        self.assertEqual(snapshot_b.get("state"), "demo", "session B was affected by session A's transitions")
        self.assertFalse(snapshot_b.get("hidden_need_revealed"), "session B's hidden need leaked from session A")
        self.assertEqual(snapshot_b.get("transcript"), [], "session B's transcript was polluted by session A")

    def test_replaying_a_read_is_side_effect_free(self):
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]
        post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "take_my_seat"})

        status, first_read = get_json(f"/api/rehearsal/sessions/{sid}")
        status2, second_read = get_json(f"/api/rehearsal/sessions/{sid}")
        self.assertEqual(status, 200)
        self.assertEqual(status2, 200)
        self.assertEqual(first_read, second_read, "re-reading the same session state is not idempotent")

    def test_action_on_nonexistent_session_rejected_even_with_other_sessions_open(self):
        post_json("/api/rehearsal/sessions")  # some other real session exists
        status, body = post_json("/api/rehearsal/sessions/totally-bogus-id/practice", {"utterance": "hi"})
        self.assertEqual(status, 404, f"body={body}")
        status, body = get_json("/api/rehearsal/sessions/totally-bogus-id")
        self.assertEqual(status, 404, f"body={body}")

    def test_feedback_endpoint_is_replay_safe_once_in_feedback_state(self):
        """Calling /feedback again while already in the feedback state must
        not recompute or mutate the score (replay safety), per the Req 3
        determinism requirement."""
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]
        post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "take_my_seat"})
        post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "practice"})
        post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": "Let's discuss terms."})

        status1, feedback1 = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        status2, feedback2 = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        self.assertEqual(status1, 200)
        self.assertIn(status2, (200, 409))  # either idempotent 200 or rejected re-submit; never a new/changed score
        if status2 == 200:
            self.assertEqual(feedback1.get("evidence_score"), feedback2.get("evidence_score"))


if __name__ == "__main__":
    unittest.main()
