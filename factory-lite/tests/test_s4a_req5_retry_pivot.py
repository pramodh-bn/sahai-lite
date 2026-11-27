"""Stage 4A requirement 5: retry from a server-fetched pivot.

The pivot is server-owned and immutable for the session: ``GET
/api/rehearsal/sessions/{id}/pivot`` returns the same ``sah.pivot.v1`` object
before and after discovery. ``POST .../retry`` increments the attempt, restores
that exact pivot (discovery reset, persona/policy stable) and leaves attempt 1
byte-identical even after attempt 2 is mutated through the API.
"""
import copy
import unittest

from s4_helpers import (
    POLICY_VERSION,
    S4App,
    SHA256_RE,
    attempts,
    evidence,
    make_practice_session,
    pivot,
    post_json,
    require_ok,
    send_turn,
    session_snapshot,
    standard_personas,
)


class TestRetryFromServerFetchedPivot(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = S4App().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def _session_at_pivot(self):
        sid = make_practice_session(standard_personas())
        status, body = pivot(sid)
        require_ok(status, body, "initial pivot fetch")
        return sid, body

    def _complete_attempt_one(self, sid, probe="My budget is tight; what terms work?"):
        status, _ = send_turn(sid, "Thanks for making the time.", 1, f"{sid}-a1-t1")
        self.assertEqual(status, 200)
        status, body = send_turn(sid, probe, 2, f"{sid}-a1-t2")
        self.assertEqual(status, 200, f"body={body}")
        self.assertIs(body.get("scenario", {}).get("hidden_need_revealed"), True,
                      "qualifying probe did not reveal the hidden need")
        status, fb = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        self.assertEqual(status, 200, f"body={fb}")

    def test_retry_increments_attempt_and_restores_the_exact_pivot(self):
        sid, initial_pivot = self._session_at_pivot()
        self.assertEqual(initial_pivot.get("schema"), "sah.pivot.v1")
        self.assertEqual(initial_pivot.get("scenario_id"), "alex_dana")
        self.assertEqual(initial_pivot.get("phase"), "practice")
        self.assertIs(initial_pivot.get("discovery_reset"), True)
        self._complete_attempt_one(sid)

        status, before_retry = pivot(sid)
        require_ok(status, before_retry, "pivot fetch after discovery")
        self.assertEqual(before_retry, initial_pivot,
                         "the restorable pivot changed after discovery; it must stay immutable")

        status, retry = post_json(f"/api/rehearsal/sessions/{sid}/retry")
        self.assertEqual(status, 200, f"body={retry}")
        self.assertEqual(retry.get("state"), "practice")
        self.assertEqual(retry.get("attempt"), 2)
        self.assertIs(retry.get("pivot_restored"), True)
        self.assertEqual(retry.get("pivot"), initial_pivot,
                         "retry did not restore the server-fetched pivot deep-equal")

        status, snap = session_snapshot(sid)
        require_ok(status, snap, "snapshot after retry")
        self.assertEqual(snap.get("attempt"), 2)
        self.assertEqual(snap.get("transcript"), [], "retry did not clear the attempt transcript")
        self.assertIs(snap.get("hidden_need_revealed"), False,
                      "retry did not reset discovery")

        status, after_retry = pivot(sid)
        require_ok(status, after_retry, "pivot fetch after retry")
        self.assertEqual(after_retry, initial_pivot)

        status, body = send_turn(sid, "Starting the second attempt.", 1, f"{sid}-a2-t1")
        self.assertEqual(status, 200,
                         f"sequence did not restart at 1 for the new attempt: {body}")

    def test_persona_hashes_and_policy_are_stable_across_retry(self):
        sid, _ = self._session_at_pivot()
        self._complete_attempt_one(sid)
        status, before = session_snapshot(sid)
        require_ok(status, before, "snapshot before retry")

        status, retry = post_json(f"/api/rehearsal/sessions/{sid}/retry")
        self.assertEqual(status, 200, f"body={retry}")
        status, after = session_snapshot(sid)
        require_ok(status, after, "snapshot after retry")

        self.assertEqual(after.get("profile_hashes"), before.get("profile_hashes"),
                         "persona profile hashes changed across retry")
        self.assertEqual(after.get("policy_version"), POLICY_VERSION)
        self.assertEqual(after.get("policy_version"), before.get("policy_version"))
        cp_instruction_hash = (before.get("instruction_hashes") or {}).get("counterpart", "")
        self.assertRegex(cp_instruction_hash, SHA256_RE,
                         "session snapshot does not expose the counterpart instruction hash")

        status, turn = send_turn(sid, "Same persona, second attempt.", 1, f"{sid}-a2-stable")
        self.assertEqual(status, 200, f"body={turn}")
        status, ev = evidence(sid)
        require_ok(status, ev, "evidence after retry turn")
        attempt_two = [r for r in ev["records"] if r.get("attempt") == 2]
        self.assertTrue(attempt_two, "no attempt-2 evidence records after retry turn")
        for record in attempt_two:
            self.assertEqual(record.get("profile_hash"),
                             before["profile_hashes"]["counterpart"])
            self.assertEqual(record.get("instruction_hash"),
                             before.get("instruction_hashes", {}).get("counterpart"))
            self.assertEqual((record.get("policy") or {}).get("policy_version"),
                             POLICY_VERSION)

    def test_attempt_one_is_immutable_after_attempt_two_is_mutated(self):
        sid, _ = self._session_at_pivot()
        self._complete_attempt_one(sid)
        status, before = attempts(sid)
        require_ok(status, before, "attempts before retry")
        attempt_one_before = next(a for a in before["attempts"] if a.get("attempt") == 1)
        frozen = copy.deepcopy(attempt_one_before)

        status, retry = post_json(f"/api/rehearsal/sessions/{sid}/retry")
        self.assertEqual(status, 200, f"body={retry}")
        status, body = send_turn(sid, "A completely different second-attempt question.",
                                 1, f"{sid}-a2-mutate")
        self.assertEqual(status, 200, f"body={body}")

        status, after = attempts(sid)
        require_ok(status, after, "attempts after attempt-2 mutation")
        attempt_one_after = next(a for a in after["attempts"] if a.get("attempt") == 1)
        self.assertEqual(attempt_one_after, frozen,
                         "attempt 1 changed after mutating attempt 2 through the API")
        attempt_two = next(a for a in after["attempts"] if a.get("attempt") == 2)
        texts = [t.get("utterance") for t in attempt_two.get("transcript", [])]
        self.assertIn("A completely different second-attempt question.", texts)
        self.assertNotIn("My budget is tight; what terms work?", texts)

    def test_discovery_must_happen_again_in_the_new_attempt(self):
        sid, _ = self._session_at_pivot()
        self._complete_attempt_one(sid)
        status, retry = post_json(f"/api/rehearsal/sessions/{sid}/retry")
        self.assertEqual(status, 200, f"body={retry}")

        status, body = send_turn(sid, "How is the weather where you are?", 1, f"{sid}-a2-quiet")
        self.assertEqual(status, 200, f"body={body}")
        self.assertIs(body["scenario"]["hidden_need_revealed"], False,
                      "non-probe turn in the new attempt claims the hidden need is still revealed")

        status, body = send_turn(sid, "Let's talk about the budget.", 2, f"{sid}-a2-probe")
        self.assertEqual(status, 200, f"body={body}")
        self.assertIs(body["scenario"]["hidden_need_revealed"], True,
                      "qualifying probe in the new attempt did not reveal the hidden need")

    def test_pivot_read_is_deterministic_and_does_not_mutate_the_session(self):
        sid, first = self._session_at_pivot()
        status, second = pivot(sid)
        require_ok(status, second, "second pivot read")
        self.assertEqual(first, second)
        status, snap = session_snapshot(sid)
        require_ok(status, snap, "snapshot after pivot reads")
        self.assertEqual(snap.get("attempt"), 1)
        self.assertEqual(snap.get("state"), "practice")
        self.assertIs(snap.get("hidden_need_revealed"), False)


if __name__ == "__main__":
    unittest.main()
