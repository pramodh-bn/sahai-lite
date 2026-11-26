"""Requirement 8 & 9: Real evidence schema validation and mock-insufficient certification.

Mandate:
- Real evidence schema requires:
    * non-null UTC start_time and end_time (valid ISO-8601 strings)
    * 64-character hexadecimal probe correlation hash (SHA-256)
    * documented HTTP probe: host, path, method, status_code
    * ready proof: event: "onAvatarReady", avatar_ready: True, status: "readyVideo"
    * media proof: video_mounted, audio_mounted, video_track_live, audio_track_live
    * cleanup proof: session_destroyed: True, resources_released: True
    * redacted: True
- Strict rejection of:
    * raw tokens, API keys, Bearer headers, JWTs
    * raw agent or connection IDs
    * personal rehearsal transcript or user utterances
    * placeholder markers (TODO, TBD, placeholder, fixture)
    * synthetic epoch timestamps (1970, 2000) or future timestamps
- Requirement 9:
    * Mock/offline success is explicitly insufficient for Stage 3 certification
"""
import copy
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s3_helpers import validate_stage3_evidence, is_stage3_certified


def make_valid_evidence():
    now = datetime.now(timezone.utc)
    start_str = (now - timedelta(seconds=90)).isoformat()
    end_str = (now - timedelta(seconds=10)).isoformat()
    return {
        "start_time_utc": start_str,
        "end_time_utc": end_str,
        "probe_correlation_hash": "a" * 64,
        "http_probe": {
            "host": "napster-api.napster.com",
            "path": "/public/agents/[REDACTED]/connections",
            "method": "POST",
            "status_code": 200,
        },
        "ready_proof": {
            "event": "onAvatarReady",
            "avatar_ready": True,
            "status": "readyVideo",
        },
        "media_proof": {
            "video_mounted": True,
            "audio_mounted": True,
            "video_track_live": True,
            "audio_track_live": True,
        },
        "cleanup_proof": {
            "session_destroyed": True,
            "resources_released": True,
        },
        "redacted": True,
    }


class TestEvidenceSchemaAndCertification(unittest.TestCase):
    def test_valid_stage3_evidence_passes(self):
        ev = make_valid_evidence()
        errors = validate_stage3_evidence(ev)
        self.assertEqual(errors, [], f"Valid evidence had unexpected errors: {errors}")

    def test_evidence_rejects_missing_or_null_utc_timestamps(self):
        ev = make_valid_evidence()
        ev["start_time_utc"] = None
        errors = validate_stage3_evidence(ev)
        self.assertTrue(any("start_time_utc" in e for e in errors))

        ev2 = make_valid_evidence()
        ev2.pop("end_time_utc")
        errors2 = validate_stage3_evidence(ev2)
        self.assertTrue(any("end_time_utc" in e for e in errors2))

    def test_evidence_rejects_synthetic_epoch_or_future_timestamps(self):
        # 1. Epoch 1970
        ev1 = make_valid_evidence()
        ev1["start_time_utc"] = "1970-01-01T00:00:00Z"
        ev1["end_time_utc"] = "1970-01-01T00:02:00Z"
        errors1 = validate_stage3_evidence(ev1)
        self.assertTrue(any("Synthetic historical timestamps" in e for e in errors1))

        # 2. Year 2000
        ev2 = make_valid_evidence()
        ev2["start_time_utc"] = "2000-01-01T00:00:00Z"
        ev2["end_time_utc"] = "2000-01-01T00:02:00Z"
        errors2 = validate_stage3_evidence(ev2)
        self.assertTrue(any("Synthetic historical timestamps" in e for e in errors2))

        # 3. Future timestamp
        ev3 = make_valid_evidence()
        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        ev3["start_time_utc"] = future
        ev3["end_time_utc"] = future
        errors3 = validate_stage3_evidence(ev3)
        self.assertTrue(any("future" in e for e in errors3))

    def test_evidence_rejects_raw_tokens_or_credentials(self):
        # Secret key pattern
        ev1 = make_valid_evidence()
        ev1["http_probe"]["raw_auth"] = "sk-live1234567890abcdef"
        errors1 = validate_stage3_evidence(ev1)
        self.assertTrue(any("Raw secret" in e for e in errors1))

        # Bearer token pattern
        ev2 = make_valid_evidence()
        ev2["http_probe"]["header"] = "Bearer topsecrettokenvalue"
        errors2 = validate_stage3_evidence(ev2)
        self.assertTrue(any("Raw secret" in e for e in errors2))

        # JWT pattern
        ev3 = make_valid_evidence()
        ev3["raw_token"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0"
        errors3 = validate_stage3_evidence(ev3)
        self.assertTrue(any("Raw secret" in e for e in errors3))

    def test_evidence_rejects_placeholders_and_fixture_ids(self):
        for placeholder in ("TODO", "TBD", "placeholder", "fixture", "mock_id"):
            with self.subTest(placeholder=placeholder):
                ev = make_valid_evidence()
                ev["note"] = f"Check this {placeholder} later"
                errors = validate_stage3_evidence(ev)
                self.assertTrue(any("Placeholder" in e for e in errors), f"Expected rejection for {placeholder}")

    def test_evidence_rejects_personal_transcript_content(self):
        ev = make_valid_evidence()
        ev["transcript"] = [{"utterance": "We need $120k base salary"}]
        errors = validate_stage3_evidence(ev)
        self.assertTrue(any("Personal rehearsal transcript" in e for e in errors))

    def test_evidence_requires_redacted_flag_true(self):
        ev1 = make_valid_evidence()
        ev1["redacted"] = False
        errors1 = validate_stage3_evidence(ev1)
        self.assertTrue(any("redacted must be explicitly True" in e for e in errors1))

        ev2 = make_valid_evidence()
        ev2.pop("redacted")
        errors2 = validate_stage3_evidence(ev2)
        self.assertTrue(any("redacted must be explicitly True" in e for e in errors2))

    def test_mock_or_offline_success_is_insufficient_for_stage3_certification(self):
        ev = make_valid_evidence()
        # Case 1: offline mode with valid evidence -> still uncertified
        certified1, reason1 = is_stage3_certified(ev, mode="offline")
        self.assertFalse(certified1, "Offline mode must NEVER be certified")
        self.assertIn("insufficient", reason1.lower())

        # Case 2: mock mode -> uncertified
        certified2, reason2 = is_stage3_certified(ev, mode="mock")
        self.assertFalse(certified2, "Mock mode must NEVER be certified")

        # Case 3: missing evidence -> uncertified
        certified3, _ = is_stage3_certified(None, mode="live")
        self.assertFalse(certified3, "Live mode with missing evidence must not be certified")


if __name__ == "__main__":
    unittest.main()
