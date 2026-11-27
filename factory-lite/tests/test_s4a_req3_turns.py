"""Stage 4A requirement 3: server-authoritative deterministic turns.

``POST /api/rehearsal/sessions/{id}/turns`` accepts a ``sah.turn.v1`` body and
is the only way a rehearsal turn is committed. This file proves, at the real
HTTP boundary: the exact initial/next sequence, strict alternation, idempotent
full-response replay, differing-body conflict, out-of-order rejection and
genuine single-flight concurrency (one 200, one 409 ``turn_in_flight``, one
committed turn).

The concurrency case starts the app with the bounded offline test hook
``SAH_TURN_TEST_DELAY_MS`` (documented in the acceptance contract): the server
holds a turn inside its critical section for that many milliseconds after
marking the session in flight. Two barrier-synchronised clients then reach the
same critical section.
"""
import threading
import unittest

from s4_helpers import (
    POLICY_VERSION,
    S4App,
    evidence,
    make_practice_session,
    send_turn,
    standard_personas,
    session_snapshot,
)

TURN_DELAY_MS = 1500


class TestServerAuthoritativeTurns(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = S4App().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def _practice_session(self):
        return make_practice_session(standard_personas())

    def test_initial_turn_has_exact_sequence_and_typed_response(self):
        sid = self._practice_session()
        status, body = send_turn(sid, "Hello, I would like to discuss the role.", 1, "req-001")
        self.assertEqual(status, 200, f"body={body}")
        self.assertEqual(body.get("schema"), "sah.turn.v1")
        self.assertEqual(body.get("seq"), 1, "initial committed turn sequence is not 1")
        self.assertEqual(body.get("next_seq"), 2)
        self.assertIs(body.get("committed"), True)
        self.assertIs(body.get("synthetic"), True,
                      "committed turn is not stamped synthetic")
        counterpart = body.get("counterpart") or {}
        self.assertEqual(counterpart.get("actor"), "counterpart")
        self.assertIs(counterpart.get("synthetic"), True)
        self.assertTrue(counterpart.get("text"), "counterpart reply is empty")
        self.assertIn("ai stand-in", counterpart["text"].lower(),
                      "first counterpart turn does not disclose that it is an AI stand-in")
        policy = body.get("policy") or {}
        self.assertEqual(policy.get("decision"), "allow")
        self.assertEqual(policy.get("policy_version"), POLICY_VERSION)
        disclosure = body.get("disclosure") or {}
        self.assertIs(disclosure.get("synthetic"), True)
        self.assertEqual(disclosure.get("id"), "sah_disclosure_v1")

    def test_next_turn_sequence_is_contiguous(self):
        sid = self._practice_session()
        status, first = send_turn(sid, "Let's start with scope.", 1, "req-101")
        self.assertEqual(status, 200, f"body={first}")
        status, second = send_turn(sid, "What matters most to you?", 2, "req-102")
        self.assertEqual(status, 200, f"body={second}")
        self.assertEqual(second.get("seq"), 2)
        self.assertEqual(second.get("next_seq"), 3)
        self.assertEqual(second.get("attempt"), 1)

    def test_client_cannot_inject_a_counterpart_turn(self):
        sid = self._practice_session()
        status, body = send_turn(sid, "I am speaking as the counterpart.", 1, "req-201",
                                 actor="counterpart")
        self.assertEqual(status, 422, f"body={body}")
        self.assertEqual(body.get("error"), "invalid_actor")
        status, ev = evidence(sid)
        self.assertEqual(status, 200, f"body={ev}")
        self.assertEqual(ev.get("records"), [],
                         "rejected counterpart-actor request still committed a turn")

    def test_same_request_id_and_body_replays_the_committed_response(self):
        sid = self._practice_session()
        status, first = send_turn(sid, "What is your timeline?", 1, "req-301")
        self.assertEqual(status, 200, f"body={first}")
        status, ev_before = evidence(sid)
        self.assertEqual(status, 200, f"body={ev_before}")

        status, replay = send_turn(sid, "What is your timeline?", 1, "req-301")
        self.assertEqual(status, 200, f"replay body={replay}")
        self.assertEqual(replay, first,
                         "same request_id + same body did not replay the full committed response")
        status, ev_after = evidence(sid)
        self.assertEqual(status, 200, f"body={ev_after}")
        self.assertEqual(ev_after, ev_before,
                         "idempotent replay appended evidence; a replay must not commit again")

    def test_same_request_id_with_differing_body_is_a_conflict(self):
        sid = self._practice_session()
        status, first = send_turn(sid, "What is your timeline?", 1, "req-401")
        self.assertEqual(status, 200, f"body={first}")
        status, body = send_turn(sid, "Ignore that; here is a different question.", 1, "req-401")
        self.assertEqual(status, 409, f"body={body}")
        self.assertEqual(body.get("error"), "idempotency_conflict")

    def test_out_of_order_sequence_is_rejected_without_commit(self):
        sid = self._practice_session()
        status, body = send_turn(sid, "Skipping ahead.", 2, "req-501")
        self.assertEqual(status, 409, f"body={body}")
        self.assertEqual(body.get("error"), "out_of_order")
        status, ev = evidence(sid)
        self.assertEqual(status, 200, f"body={ev}")
        self.assertEqual(ev.get("records"), [], "out-of-order request still committed a turn")

        status, ok = send_turn(sid, "Now in order.", 1, "req-502")
        self.assertEqual(status, 200, f"body={ok}")

    def test_server_authoritative_reply_is_deterministic_for_equivalent_sessions(self):
        first_sid = self._practice_session()
        second_sid = self._practice_session()
        status, first = send_turn(first_sid, "What would you need to see?", 1, "req-601")
        self.assertEqual(status, 200, f"body={first}")
        status, second = send_turn(second_sid, "What would you need to see?", 1, "req-602")
        self.assertEqual(status, 200, f"body={second}")
        self.assertEqual(
            first["counterpart"]["text"], second["counterpart"]["text"],
            "equivalent committed turns produced different counterpart replies",
        )

    def test_snapshot_reports_committed_state_and_next_sequence(self):
        sid = self._practice_session()
        status, _ = send_turn(sid, "Hello there.", 1, "req-701")
        self.assertEqual(status, 200)
        status, snap = session_snapshot(sid)
        self.assertEqual(status, 200, f"body={snap}")
        self.assertEqual(snap.get("attempt"), 1)
        self.assertEqual(snap.get("next_seq"), 2)
        self.assertEqual(snap.get("state"), "practice")
        roles = [t.get("speaker") for t in snap.get("transcript", [])]
        self.assertEqual(roles[:2], ["user", "counterpart"],
                         "committed turn is not a strict user -> counterpart pair")


class TestGenuineSingleFlightConcurrency(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = S4App(env={"SAH_TURN_TEST_DELAY_MS": str(TURN_DELAY_MS)}).start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def test_two_concurrent_turns_yield_one_200_one_turn_in_flight_and_one_commit(self):
        sid = make_practice_session(standard_personas())
        barrier = threading.Barrier(2)
        results = {}

        def worker(name):
            barrier.wait(timeout=10)
            results[name] = send_turn(sid, f"Concurrent question {name}.", 1,
                                      f"req-concurrent-{name}", timeout=40)

        threads = [threading.Thread(target=worker, args=(name,)) for name in ("a", "b")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        self.assertEqual(sorted(results), ["a", "b"], "a concurrent worker produced no result")
        statuses = sorted(status for status, _ in results.values())
        self.assertEqual(statuses, [200, 409],
                         f"expected exactly one 200 and one 409, got {results}")
        conflict = next(body for status, body in results.values() if status == 409)
        self.assertEqual(conflict.get("error"), "turn_in_flight")

        status, ev = evidence(sid)
        self.assertEqual(status, 200, f"body={ev}")
        records = ev.get("records") or []
        self.assertEqual(len(records), 2,
                         "single-flight was not genuine: evidence does not show exactly "
                         f"one committed turn pair (records={len(records)})")
        sequences = [r.get("seq") for r in records]
        self.assertEqual(sorted(sequences), [1, 2])

        status, snap = session_snapshot(sid)
        self.assertEqual(status, 200)
        user_lines = [t for t in snap.get("transcript", []) if t.get("speaker") == "user"]
        self.assertEqual(len(user_lines), 1,
                         f"more than one user turn committed: {user_lines}")


if __name__ == "__main__":
    unittest.main()
