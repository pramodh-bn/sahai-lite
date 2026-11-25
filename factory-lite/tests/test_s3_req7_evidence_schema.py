"""Stage 3: strengthened redacted-evidence schema.

Proves factory-lite/tests/s3_live_gate.validate_evidence_record() -- used
identically by the offline adapter tests and by the real live run --
accepts only a complete, concrete, non-sensitive record and rejects null
timestamps, missing outcome, ambiguous/missing status, unredacted
records, and credential/transcript-like evidence_text. Pure fixture
data; no vendor call, no network.
"""
import unittest

from s3_live_gate import validate_evidence_record

GOOD_RECORD = {
    "probe_id": "abc123",
    "capability": "companion_avatar",
    "started_at": "2026-11-25T13:50:00+00:00",
    "ended_at": "2026-11-25T13:50:02+00:00",
    "outcome": "success",
    "http_status": 200,
    "redacted": True,
    "evidence_text": "companion_avatar session started and completed normally.",
}


class TestEvidenceSchema(unittest.TestCase):
    def test_well_formed_record_is_valid(self):
        is_valid, problems = validate_evidence_record(dict(GOOD_RECORD))
        self.assertTrue(is_valid, problems)
        self.assertEqual(problems, [])

    def test_null_started_at_is_rejected(self):
        record = dict(GOOD_RECORD, started_at=None)
        is_valid, problems = validate_evidence_record(record)
        self.assertFalse(is_valid)
        self.assertTrue(any("started_at" in p for p in problems))

    def test_null_ended_at_is_rejected(self):
        record = dict(GOOD_RECORD, ended_at=None)
        is_valid, problems = validate_evidence_record(record)
        self.assertFalse(is_valid)
        self.assertTrue(any("ended_at" in p for p in problems))

    def test_ended_before_started_is_rejected(self):
        record = dict(GOOD_RECORD, started_at="2026-11-25T13:50:10+00:00", ended_at="2026-11-25T13:50:00+00:00")
        is_valid, problems = validate_evidence_record(record)
        self.assertFalse(is_valid)

    def test_missing_outcome_is_rejected(self):
        record = dict(GOOD_RECORD, outcome=None)
        is_valid, problems = validate_evidence_record(record)
        self.assertFalse(is_valid)

    def test_missing_both_status_and_transport_result_is_rejected(self):
        record = dict(GOOD_RECORD)
        del record["http_status"]
        is_valid, problems = validate_evidence_record(record)
        self.assertFalse(is_valid)

    def test_both_status_and_transport_result_present_is_rejected(self):
        record = dict(GOOD_RECORD, transport_result="connection_reset")
        is_valid, problems = validate_evidence_record(record)
        self.assertFalse(is_valid, "exactly one of http_status/transport_result must be set, not both")

    def test_transport_result_alone_is_valid(self):
        record = dict(GOOD_RECORD, transport_result="connection_reset")
        del record["http_status"]
        is_valid, problems = validate_evidence_record(record)
        self.assertTrue(is_valid, problems)

    def test_unredacted_record_is_rejected(self):
        record = dict(GOOD_RECORD, redacted=False)
        is_valid, problems = validate_evidence_record(record)
        self.assertFalse(is_valid)

    def test_credential_looking_evidence_text_is_rejected(self):
        record = dict(GOOD_RECORD, evidence_text="Used X-Api-Key: sk-super-secret-value to connect.")
        is_valid, problems = validate_evidence_record(record)
        self.assertFalse(is_valid)

    def test_raw_credential_value_in_evidence_text_is_rejected(self):
        record = dict(GOOD_RECORD, evidence_text="Connected successfully using sk-super-secret-value.")
        is_valid, problems = validate_evidence_record(record, credential_value="sk-super-secret-value")
        self.assertFalse(is_valid)

    def test_transcript_like_evidence_text_is_rejected(self):
        record = dict(GOOD_RECORD, evidence_text="Line one.\nLine two.\nLine three.\nLine four.")
        is_valid, problems = validate_evidence_record(record)
        self.assertFalse(is_valid, "multi-line transcript-like evidence_text must be rejected")

    def test_invalid_capability_is_rejected(self):
        record = dict(GOOD_RECORD, capability="sip_transfer")
        is_valid, problems = validate_evidence_record(record)
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
