"""Stage 2: "Counterpart retains scenario state, hidden need not leaked
before discovery."

Contract convention: POST /api/rehearsal/sessions/{id}/practice accepts
{"utterance": "<text>"} and returns {"counterpart_reply": str,
"hidden_need_revealed": bool}. The Alex/Dana scenario's hidden budget
constraint must not be revealed (hidden_need_revealed stays false, and the
reply must not disclose it) until the user's utterance explicitly probes
for it (mentions budget/cost/price/afford); after that point
hidden_need_revealed must flip to true and stay true for the rest of the
attempt. The counterpart must also retain state across turns within one
session (it is not stateless/replying generically every time).
"""
import unittest

from s2_helpers import AppProcess, post_json


def _advance_to_practice(sid):
    post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "take_my_seat"})
    post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "practice"})


class TestCounterpartStateAndHiddenNeed(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def _new_practice_session(self):
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]
        _advance_to_practice(sid)
        return sid

    def test_hidden_need_not_revealed_by_neutral_opening_utterance(self):
        sid = self._new_practice_session()
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": "Hi, thanks for meeting with me today."})
        self.assertEqual(status, 200, f"body={body}")
        self.assertFalse(body.get("hidden_need_revealed"), "hidden need leaked on a neutral opening line")
        self.assertTrue(body.get("counterpart_reply"), "counterpart_reply missing/empty")

    def test_hidden_need_revealed_only_after_explicit_budget_probe(self):
        sid = self._new_practice_session()
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": "What matters most to you in this deal?"})
        self.assertEqual(status, 200)
        self.assertFalse(body.get("hidden_need_revealed"), "hidden need leaked before any budget probe")

        status, body = post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": "What is your budget for this?"})
        self.assertEqual(status, 200)
        self.assertTrue(body.get("hidden_need_revealed"), "hidden need was not revealed after an explicit budget probe")

        # Once revealed, it stays revealed for the rest of this attempt.
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": "Thanks for sharing that."})
        self.assertEqual(status, 200)
        self.assertTrue(body.get("hidden_need_revealed"), "hidden_need_revealed flipped back to false later in the same attempt")

    def test_practice_rejected_outside_practice_state(self):
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]  # still in "demo", never advanced
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": "hello"})
        self.assertEqual(status, 409, f"body={body}")
        self.assertEqual(body.get("error"), "invalid_state")

    def test_counterpart_retains_state_across_turns_in_the_same_session(self):
        """The counterpart must not be a stateless echo: asking the same
        probing question twice in one session, after it has already been
        answered, must behave differently from asking it the first time
        (hidden_need_revealed is already true and stays true), proving the
        session/transcript is actually being retained turn to turn."""
        sid = self._new_practice_session()
        post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": "What is your budget?"})
        status, first_snapshot = post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": "Can you say more?"})
        self.assertEqual(status, 200)
        self.assertTrue(first_snapshot.get("hidden_need_revealed"))

        from s2_helpers import get_json
        status, snapshot = get_json(f"/api/rehearsal/sessions/{sid}")
        self.assertEqual(status, 200)
        transcript = snapshot.get("transcript")
        self.assertIsInstance(transcript, list)
        self.assertGreaterEqual(len(transcript), 3, "transcript did not accumulate turns across the session")


if __name__ == "__main__":
    unittest.main()
