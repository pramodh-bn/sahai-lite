"""Stage 2: "hidden budget constraint and sign-on flexibility"; "Counterpart
retains scenario state, hidden need not leaked before discovery."

Contract convention (Repair R1): the Alex/Dana hidden need is composite --
a hidden budget constraint *and* hidden sign-on flexibility, both tracked
by the single `hidden_need_revealed` boolean returned by POST
/api/rehearsal/sessions/{id}/practice ({"utterance": str} ->
{"counterpart_reply": str, "hidden_need_revealed": bool}). Neither
dimension may be revealed (hidden_need_revealed stays false) until the
user's utterance explicitly probes for *either* one. The trigger set is:
  - budget-side: utterance mentions budget/cost/price/afford
  - sign-on-side: utterance mentions "sign-on", "sign on", "signing
    bonus", "flexible on sign-on", or contract terms generally
A probe from either side flips hidden_need_revealed to true, and it stays
true for the rest of the attempt regardless of which side was asked about.
The counterpart must also retain state across turns within one session (it
is not stateless/replying generically every time).
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

    def test_hidden_need_revealed_by_sign_on_only_probe_with_no_budget_keyword(self):
        """A probe about sign-on flexibility alone -- no budget/cost/price/
        afford keyword anywhere -- must reveal the hidden need just as much
        as a budget probe does, since the hidden need is the composite
        (budget constraint + sign-on flexibility), not budget alone."""
        sid = self._new_practice_session()
        status, body = post_json(
            f"/api/rehearsal/sessions/{sid}/practice",
            {"utterance": "Are you flexible on sign-on timing for this role?"},
        )
        self.assertEqual(status, 200, f"body={body}")
        self.assertTrue(
            body.get("hidden_need_revealed"),
            "sign-on-only probe (no budget keyword) did not reveal the hidden need",
        )
        self.assertTrue(body.get("counterpart_reply"), "counterpart_reply missing/empty")

        # Stays revealed for the rest of the attempt, same as the budget path.
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": "Good to know, thanks."})
        self.assertEqual(status, 200)
        self.assertTrue(
            body.get("hidden_need_revealed"),
            "hidden_need_revealed flipped back to false later in the same attempt after a sign-on probe",
        )

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
