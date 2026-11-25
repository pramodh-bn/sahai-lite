"""Stage 2: "Evidence score references actual utterances"; deterministic
scoring.

Contract convention: POST /api/rehearsal/sessions/{id}/feedback is only
valid from state "practice"; it returns {"state": "feedback",
"evidence_score": <int 0-100>, "evidence": [{"utterance": str, "note":
str}, ...]}. Each "evidence[*].utterance" must exactly match text the user
actually sent to /practice during that attempt -- not generic boilerplate.
Scoring must be deterministic: re-reading feedback for the same attempt
(without new practice input) must return the identical score every time.
"""
import unittest

from s2_helpers import AppProcess, post_json, get_json


class TestEvidenceScoring(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def _session_with_practice_turns(self, utterances):
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]
        post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "take_my_seat"})
        post_json(f"/api/rehearsal/sessions/{sid}/advance", {"to": "practice"})
        for utterance in utterances:
            post_json(f"/api/rehearsal/sessions/{sid}/practice", {"utterance": utterance})
        return sid

    def test_feedback_rejected_outside_practice_state(self):
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]  # still "demo"
        status, body = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        self.assertEqual(status, 409, f"body={body}")

    def test_evidence_references_actual_submitted_utterances(self):
        utterances = [
            "I'd like to understand your timeline for signing.",
            "What is your budget for this engagement?",
        ]
        sid = self._session_with_practice_turns(utterances)

        status, body = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        self.assertEqual(status, 200, f"body={body}")
        self.assertEqual(body.get("state"), "feedback")

        evidence = body.get("evidence")
        self.assertIsInstance(evidence, list)
        self.assertGreaterEqual(len(evidence), 1, "feedback returned no evidence items")

        evidence_utterances = {item.get("utterance") for item in evidence}
        self.assertTrue(
            evidence_utterances.issubset(set(utterances)),
            f"evidence cites utterance(s) never actually sent: {evidence_utterances - set(utterances)}",
        )
        self.assertTrue(
            evidence_utterances & set(utterances),
            "no evidence item references any utterance actually sent in this attempt",
        )

        score = body.get("evidence_score")
        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_scoring_is_deterministic_on_repeated_read(self):
        sid = self._session_with_practice_turns(["Let's talk about scope first."])
        status, first = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        self.assertEqual(status, 200)

        status, snapshot1 = get_json(f"/api/rehearsal/sessions/{sid}")
        self.assertEqual(status, 200)
        status, snapshot2 = get_json(f"/api/rehearsal/sessions/{sid}")
        self.assertEqual(status, 200)

        self.assertEqual(snapshot1.get("evidence_score"), first.get("evidence_score"))
        self.assertEqual(
            snapshot1.get("evidence_score"),
            snapshot2.get("evidence_score"),
            "evidence_score changed between two reads of the same, unmodified attempt",
        )


if __name__ == "__main__":
    unittest.main()
