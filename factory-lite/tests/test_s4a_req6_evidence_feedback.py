"""Stage 4A requirement 6: append-only ``sah.evidence.v1`` and feedback quotes.

Proves the evidence log keeps a stable prefix with strictly increasing
sequence numbers, that turn records carry the required audit fields, that no
hidden marker/secret/media leaks in, and that feedback quotations are
structured, verbatim, and isolated to the attempt that produced them.
"""
import json
import unittest

from s4_helpers import (
    BD_MARKER,
    CP_MARKER,
    POLICY_VERSION,
    S4App,
    SHA256_RE,
    attempts,
    evidence,
    make_practice_session,
    post_json,
    require_ok,
    send_turn,
    session_snapshot,
    standard_personas,
    walk,
)

FORBIDDEN_EVIDENCE_KEYS = {
    "audio", "video", "media", "biometric", "voice_sample",
    "raw_vendor_id", "credentials", "token", "api_key",
}
FORBIDDEN_EVIDENCE_PATTERNS = (
    CP_MARKER, BD_MARKER, "sk-", "Bearer ", "eyJ", "conn_",
    "data:audio", "data:video",
)


def user_utterances(attempts_body, attempt_number):
    entry = next(a for a in attempts_body["attempts"] if a.get("attempt") == attempt_number)
    return {t.get("utterance") for t in entry.get("transcript", [])
            if t.get("speaker") == "user"}


class TestAppendOnlyEvidence(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = S4App().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def _practice(self):
        personas = standard_personas()
        return make_practice_session(personas), personas

    def test_log_is_versioned_and_keeps_a_stable_strictly_increasing_prefix(self):
        sid, _ = self._practice()
        status, first = send_turn(sid, "First question about scope.", 1, f"{sid}-e1")
        self.assertEqual(status, 200, f"body={first}")
        status, ev1 = evidence(sid)
        require_ok(status, ev1, "evidence after turn 1")
        self.assertEqual(ev1.get("schema"), "sah.evidence.v1")
        records_1 = ev1["records"]
        self.assertEqual(len(records_1), 2,
                         "one committed turn must append exactly a user/counterpart record pair")
        seqs_1 = [r["seq"] for r in records_1]
        self.assertEqual(seqs_1, sorted(seqs_1))
        self.assertEqual(len(set(seqs_1)), len(seqs_1), "duplicate evidence sequence number")
        self.assertEqual(seqs_1[0], 1, "evidence sequence does not start at 1")

        status, second = send_turn(sid, "Second question about timing.", 2, f"{sid}-e2")
        self.assertEqual(status, 200, f"body={second}")
        status, ev2 = evidence(sid)
        require_ok(status, ev2, "evidence after turn 2")
        records_2 = ev2["records"]
        self.assertEqual(len(records_2), 4)
        self.assertEqual(records_2[:2], records_1,
                         "evidence prefix was rewritten by a later append")
        seqs_2 = [r["seq"] for r in records_2]
        self.assertEqual(seqs_2, sorted(seqs_2))
        self.assertGreater(seqs_2[-1], seqs_2[-2], "sequence did not strictly increase")
        self.assertEqual(seqs_2, [1, 2, 3, 4])

    def test_turn_records_carry_role_attempt_hashes_and_policy_decision(self):
        sid, personas = self._practice()
        status, turn = send_turn(sid, "Please walk me through the constraints.", 1, f"{sid}-audit")
        self.assertEqual(status, 200, f"body={turn}")
        status, snap = session_snapshot(sid)
        require_ok(status, snap, "session snapshot")
        instruction_hash = (snap.get("instruction_hashes") or {}).get("counterpart", "")
        self.assertRegex(instruction_hash, SHA256_RE)

        status, ev = evidence(sid)
        require_ok(status, ev, "evidence")
        records = ev["records"]
        self.assertEqual([r.get("role") for r in records], ["user", "counterpart"],
                         "turn evidence roles do not alternate user -> counterpart")
        for record in records:
            self.assertEqual(record.get("record_type"), "turn")
            self.assertEqual(record.get("attempt"), 1)
            self.assertEqual(record.get("profile_hash"), personas["counterpart"]["profile_hash"])
            self.assertEqual(record.get("instruction_hash"), instruction_hash)
            self.assertRegex(record.get("projection_hash", ""), SHA256_RE,
                             "turn evidence lacks the applied projection hash")
            self.assertRegex(record.get("text_sha256", ""), SHA256_RE)
            policy = record.get("policy") or {}
            self.assertEqual(policy.get("decision"), "allow")
            self.assertEqual(policy.get("policy_version"), POLICY_VERSION)
            self.assertIs(record.get("synthetic"), True)

    def test_evidence_never_contains_hidden_markers_secrets_or_media(self):
        sid, _ = self._practice()
        status, turn = send_turn(sid, "What is your budget and what terms work?", 1, f"{sid}-leak")
        self.assertEqual(status, 200, f"body={turn}")
        status, fb = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        self.assertEqual(status, 200, f"body={fb}")

        status, ev = evidence(sid)
        require_ok(status, ev, "evidence")
        rendered = json.dumps(ev, ensure_ascii=False)
        for pattern in FORBIDDEN_EVIDENCE_PATTERNS:
            self.assertNotIn(pattern, rendered,
                             f"evidence leaked forbidden value/pattern {pattern!r}")
        present = {key for _, key, _ in walk(ev) if key in FORBIDDEN_EVIDENCE_KEYS}
        self.assertEqual(sorted(present), [],
                         f"evidence contains forbidden media/credential key(s): {sorted(present)}")

    def test_feedback_quotes_are_nonempty_structured_and_verbatim(self):
        sid, _ = self._practice()
        utterances = ["My budget is tight this quarter.", "What terms could work?"]
        attempt_id = None
        for index, utterance in enumerate(utterances, start=1):
            status, body = send_turn(sid, utterance, index, f"{sid}-q{index}")
            self.assertEqual(status, 200, f"body={body}")
            attempt_id = attempt_id or body.get("attempt_id")
        self.assertTrue(attempt_id, "turn response carries no attempt_id")

        status, fb = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        self.assertEqual(status, 200, f"body={fb}")
        status, ev = evidence(sid)
        require_ok(status, ev, "evidence")

        quotes = [r for r in ev["records"] if r.get("record_type") == "feedback_quote"]
        self.assertTrue(quotes, "feedback produced no structured quotation records")
        for record in quotes:
            self.assertEqual(record.get("attempt"), 1)
            self.assertEqual(record.get("attempt_id"), attempt_id,
                             "quotation is not bound to the attempt that produced it")
            quote = record.get("quote")
            self.assertIsInstance(quote, str)
            self.assertTrue(quote.strip(), "feedback quotation is empty")
            self.assertIn(quote, utterances,
                          f"feedback quoted text that the user never sent: {quote!r}")

    def test_feedback_quotes_are_isolated_between_two_attempts(self):
        sid, _ = self._practice()
        attempt_one = ["U1 budget is my main concern.", "U1 how flexible are the terms?"]
        attempt_one_id = None
        for index, utterance in enumerate(attempt_one, start=1):
            status, body = send_turn(sid, utterance, index, f"{sid}-iso-a1-{index}")
            self.assertEqual(status, 200, f"body={body}")
            attempt_one_id = attempt_one_id or body.get("attempt_id")
        status, fb1 = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        self.assertEqual(status, 200, f"body={fb1}")
        status, ev_after_one = evidence(sid)
        require_ok(status, ev_after_one, "evidence after attempt 1")
        quotes_one = [r for r in ev_after_one["records"]
                      if r.get("record_type") == "feedback_quote"]
        self.assertTrue(quotes_one)
        self.assertTrue(all(r.get("attempt") == 1 for r in quotes_one))

        status, retry = post_json(f"/api/rehearsal/sessions/{sid}/retry")
        self.assertEqual(status, 200, f"body={retry}")
        attempt_two = ["U2 completely different scope question.", "U2 different timeline question."]
        attempt_two_id = None
        for index, utterance in enumerate(attempt_two, start=1):
            status, body = send_turn(sid, utterance, index, f"{sid}-iso-a2-{index}")
            self.assertEqual(status, 200, f"body={body}")
            attempt_two_id = attempt_two_id or body.get("attempt_id")
        self.assertNotEqual(attempt_one_id, attempt_two_id,
                            "two attempts share one attempt_id")
        status, fb2 = post_json(f"/api/rehearsal/sessions/{sid}/feedback")
        self.assertEqual(status, 200, f"body={fb2}")

        status, real_attempts = attempts(sid)
        require_ok(status, real_attempts, "attempts")
        set_one = user_utterances(real_attempts, 1)
        set_two = user_utterances(real_attempts, 2)

        status, ev = evidence(sid)
        require_ok(status, ev, "evidence after attempt 2")
        records = ev["records"]
        self.assertEqual(records[:len(ev_after_one["records"])], ev_after_one["records"],
                         "attempt-1 evidence prefix changed when attempt 2 appended")
        quotes = [r for r in records if r.get("record_type") == "feedback_quote"]
        by_attempt = {1: [], 2: []}
        for record in quotes:
            by_attempt.setdefault(record.get("attempt"), []).append(record)
            target = set_one if record.get("attempt") == 1 else set_two
            self.assertIn(record.get("quote"), target,
                          f"attempt {record.get('attempt')} quote is not from that attempt: "
                          f"{record.get('quote')!r}")
        self.assertTrue(by_attempt[1], "no attempt-1 quotations recorded")
        self.assertTrue(by_attempt[2], "no attempt-2 quotations recorded")
        for record in by_attempt[1]:
            self.assertEqual(record.get("attempt_id"), attempt_one_id)
        for record in by_attempt[2]:
            self.assertEqual(record.get("attempt_id"), attempt_two_id)
        self.assertFalse(set(record["quote"] for record in by_attempt[1]) & set_two,
                         "attempt-1 quotation also appears in attempt 2 utterances")


if __name__ == "__main__":
    unittest.main()
