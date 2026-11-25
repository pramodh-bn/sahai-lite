"""Stage 2: "retry restores pivot snapshot and preserves first attempt."

Contract convention: POST /api/rehearsal/sessions/{id}/retry is only valid
from state "feedback". It starts a new attempt (attempt N+1), resets state
to "practice" restored at the pivot (fresh transcript, hidden_need_revealed
reset to false -- the discovery has to happen again), while the prior
attempt's transcript/evidence_score remain unchanged and retrievable via
GET /api/rehearsal/sessions/{id}/attempts.
"""
import unittest

from s2_helpers import AppProcess, post_json, get_json


class TestRetryRestoresPivotAndPreservesFirstAttempt(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def _completed_first_attempt_session(self):
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]
        post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "take_my_seat"})
        post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "practice"})
        post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": "What is your budget?"})
        status, feedback = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        assert status == 200, feedback
        return sid, feedback

    def test_retry_rejected_outside_feedback_state(self):
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]  # still "demo"
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/retry")
        self.assertEqual(status, 409, f"body={body}")

    def test_retry_starts_a_new_attempt_at_the_practice_pivot(self):
        sid, _ = self._completed_first_attempt_session()
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/retry")
        self.assertEqual(status, 200, f"body={body}")
        self.assertEqual(body.get("state"), "practice")
        self.assertEqual(body.get("attempt"), 2)
        self.assertTrue(body.get("pivot_restored"))

        status, snapshot = get_json(f"/api/rehearsal/sessions/{sid}")
        self.assertEqual(status, 200)
        self.assertEqual(snapshot.get("attempt"), 2)
        self.assertEqual(
            snapshot.get("transcript"), [],
            "retry did not restore a fresh transcript at the pivot",
        )
        self.assertFalse(
            snapshot.get("hidden_need_revealed"),
            "retry did not reset hidden_need_revealed -- discovery must happen again each attempt",
        )

    def test_first_attempt_is_preserved_unchanged_after_retry(self):
        sid, first_feedback = self._completed_first_attempt_session()
        post_json(f"/api/rehearsal/sessions/{sid}/retry")

        # Advance/mutate attempt 2 a bit, to make sure it can't bleed back into attempt 1.
        post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": "Let's start over, differently this time."})

        status, body = get_json(f"/api/rehearsal/sessions/{sid}/attempts")
        self.assertEqual(status, 200, f"body={body}")
        attempts = body.get("attempts")
        self.assertIsInstance(attempts, list)
        self.assertGreaterEqual(len(attempts), 2, "first attempt was not preserved after retry")

        attempt_1 = next((a for a in attempts if a.get("attempt") == 1), None)
        self.assertIsNotNone(attempt_1, "attempt 1 missing from /attempts after retry")
        self.assertEqual(attempt_1.get("evidence_score"), first_feedback.get("evidence_score"))
        # attempt 1's transcript must contain the original utterance, and must
        # not have been overwritten by attempt 2's practice turn.
        attempt_1_texts = [t.get("utterance") for t in attempt_1.get("transcript", [])]
        self.assertIn("What is your budget?", attempt_1_texts)
        self.assertNotIn("Let's start over, differently this time.", attempt_1_texts)


if __name__ == "__main__":
    unittest.main()
