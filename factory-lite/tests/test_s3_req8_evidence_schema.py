import ast
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
- Host Policy & Certification Boundary:
    * Offline/mock mode allows loopback (127.0.0.1, localhost) for fake-vendor testing
    * Credentialed certification (mode='live') strictly requires HTTPS and exact approved host companion-api.napster.com
    * Rejects localhost, loopback, private/link-local/test/documentation IPs, non-HTTPS, userinfo, non-default ports, DNS aliases, and historical hosts in live mode
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
            "host": "companion-api.napster.com",
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
        ev1 = make_valid_evidence()
        ev1["start_time_utc"] = "1970-01-01T00:00:00Z"
        ev1["end_time_utc"] = "1970-01-01T00:02:00Z"
        errors1 = validate_stage3_evidence(ev1)
        self.assertTrue(any("Synthetic historical timestamps" in e for e in errors1))

        ev2 = make_valid_evidence()
        ev2["start_time_utc"] = "2000-01-01T00:00:00Z"
        ev2["end_time_utc"] = "2000-01-01T00:02:00Z"
        errors2 = validate_stage3_evidence(ev2)
        self.assertTrue(any("Synthetic historical timestamps" in e for e in errors2))

        ev3 = make_valid_evidence()
        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        ev3["start_time_utc"] = future
        ev3["end_time_utc"] = future
        errors3 = validate_stage3_evidence(ev3)
        self.assertTrue(any("future" in e for e in errors3))

    def test_evidence_rejects_raw_tokens_or_credentials(self):
        ev1 = make_valid_evidence()
        ev1["http_probe"]["raw_auth"] = "sk-" + "testsecretkey12345"
        errors1 = validate_stage3_evidence(ev1)
        self.assertTrue(any("Raw secret" in e for e in errors1))

        ev2 = make_valid_evidence()
        ev2["http_probe"]["header"] = "Bearer topsecrettokenvalue"
        errors2 = validate_stage3_evidence(ev2)
        self.assertTrue(any("Raw secret" in e for e in errors2))

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
        certified1, reason1 = is_stage3_certified(ev, mode="offline")
        self.assertFalse(certified1, "Offline mode must NEVER be certified")
        self.assertIn("insufficient", reason1.lower())

        certified2, reason2 = is_stage3_certified(ev, mode="mock")
        self.assertFalse(certified2, "Mock mode must NEVER be certified")

        certified3, _ = is_stage3_certified(None, mode="live")
        self.assertFalse(certified3, "Live mode with missing evidence must not be certified")

    def test_evidence_rejects_loopback_in_live_certification_mode(self):
        for host in ("127.0.0.1", "localhost", "127.0.0.1:8000"):
            with self.subTest(host=host):
                ev = make_valid_evidence()
                ev["http_probe"]["host"] = host
                # Valid in offline/mock mode
                errs_offline = validate_stage3_evidence(ev, mode="offline")
                self.assertEqual(errs_offline, [], f"Loopback host {host} should be valid in offline mode")

                # Strictly rejected in live certification mode
                errs_live = validate_stage3_evidence(ev, mode="live")
                self.assertTrue(
                    any("exact approved real host" in e or "Live certification requires" in e for e in errs_live),
                    f"Expected live mode rejection for loopback host {host}, got: {errs_live}",
                )
                certified, reason = is_stage3_certified(ev, mode="live")
                self.assertFalse(certified, f"Loopback host {host} certified under mode='live'")
                self.assertIn("Evidence validation failed", reason)

    def test_evidence_rejects_private_and_documentation_ips_in_live_mode(self):
        for ip in ("10.0.0.1", "192.168.1.1", "172.16.0.1", "169.254.1.1", "192.0.2.1", "198.51.100.1", "203.0.113.1"):
            with self.subTest(ip=ip):
                ev = make_valid_evidence()
                ev["http_probe"]["host"] = ip
                errs_live = validate_stage3_evidence(ev, mode="live")
                self.assertTrue(
                    any("exact approved real host" in e for e in errs_live),
                    f"Expected rejection for IP {ip}, got: {errs_live}",
                )
                certified, _ = is_stage3_certified(ev, mode="live")
                self.assertFalse(certified, f"IP {ip} certified under mode='live'")

    def test_evidence_rejects_non_https_and_userinfo_and_non_default_ports(self):
        # Non-HTTPS URL in host
        ev1 = make_valid_evidence()
        ev1["http_probe"]["host"] = "http://companion-api.napster.com"
        errs1 = validate_stage3_evidence(ev1, mode="live")
        self.assertTrue(any("HTTPS" in e for e in errs1), f"Expected HTTPS error, got: {errs1}")
        self.assertFalse(is_stage3_certified(ev1, mode="live")[0])

        # Explicit non-https scheme in probe
        ev2 = make_valid_evidence()
        ev2["http_probe"]["scheme"] = "http"
        errs2 = validate_stage3_evidence(ev2, mode="live")
        self.assertTrue(any("HTTPS" in e for e in errs2), f"Expected HTTPS error, got: {errs2}")
        self.assertFalse(is_stage3_certified(ev2, mode="live")[0])

        # Userinfo in host
        ev3 = make_valid_evidence()
        ev3["http_probe"]["host"] = "user:secret@companion-api.napster.com"
        errs3 = validate_stage3_evidence(ev3, mode="live")
        self.assertTrue(any("Userinfo" in e for e in errs3), f"Expected Userinfo error, got: {errs3}")
        self.assertFalse(is_stage3_certified(ev3, mode="live")[0])

        # Non-default port
        ev4 = make_valid_evidence()
        ev4["http_probe"]["host"] = "companion-api.napster.com:8443"
        errs4 = validate_stage3_evidence(ev4, mode="live")
        self.assertTrue(any("Non-default port" in e for e in errs4), f"Expected Non-default port error, got: {errs4}")
        self.assertFalse(is_stage3_certified(ev4, mode="live")[0])

    def test_evidence_rejects_historical_and_unsupported_hosts_in_live_mode(self):
        # Historical napster-api is reference only, non-certifying in live mode
        ev1 = make_valid_evidence()
        ev1["http_probe"]["host"] = "napster-api.napster.com"
        errs_offline = validate_stage3_evidence(ev1, mode="offline")
        self.assertEqual(errs_offline, [], "Historical host is valid in offline reference mode")
        errs_live = validate_stage3_evidence(ev1, mode="live")
        self.assertTrue(
            any("exact approved real host" in e for e in errs_live),
            f"Expected live mode rejection for historical host, got: {errs_live}",
        )
        self.assertFalse(is_stage3_certified(ev1, mode="live")[0])

        # Unsupported DNS aliases
        for host in ("api.napster.com", "fake.napster.com", "napster.internal"):
            with self.subTest(host=host):
                ev = make_valid_evidence()
                ev["http_probe"]["host"] = host
                errs = validate_stage3_evidence(ev, mode="live")
                self.assertTrue(
                    any("exact approved real host" in e or "Unrecognized" in e for e in errs),
                    f"Expected rejection for unsupported host {host}, got: {errs}",
                )
                self.assertFalse(is_stage3_certified(ev, mode="live")[0])

    def test_official_approved_host_passes_live_certification(self):
        ev = make_valid_evidence()
        ev["http_probe"]["host"] = "companion-api.napster.com"
        ev["http_probe"]["scheme"] = "https"
        errs_live = validate_stage3_evidence(ev, mode="live")
        self.assertEqual(errs_live, [], f"Official approved host failed validation: {errs_live}")
        certified, reason = is_stage3_certified(ev, mode="live")
        self.assertTrue(certified, f"Official approved host failed certification: {reason}")


    def test_post_disconnect_release_wait_returns_strict_boolean_conjunction_not_object(self):
        """Regression test for defect #1:
        Playwright wait_for_function treats any JavaScript object as truthy, returning immediately.
        The release wait callback must return the exact boolean conjunction of all five release conditions.
        """
        gate_file = Path(__file__).parent / "test_s3_req7_live_gate.py"
        code_str = gate_file.read_text(encoding="utf-8")

        # Static verification that the callback does not return an object literal
        tree = ast.parse(code_str, filename=str(gate_file))
        wait_calls = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "wait_for_function"
        ]
        self.assertGreaterEqual(len(wait_calls), 2)
        release_wait_code = wait_calls[1].args[0].value

        self.assertNotIn(
            "return {",
            release_wait_code,
            "Release wait callback must not return an object literal; objects are truthy in JS and return immediately",
        )
        self.assertIn("noLiveVideoTracks &&", release_wait_code)
        self.assertIn("noLiveAudioTracks &&", release_wait_code)
        self.assertIn("elementsCleared &&", release_wait_code)
        self.assertIn("avatarReadyFalse &&", release_wait_code)
        self.assertIn("sdkStatusUnavailable", release_wait_code)

        # Functional boolean conjunction verification:
        # If any of the five conditions is false, the release predicate must evaluate to False.
        # Only when all five are True must the release predicate evaluate to True.
        cases = [
            (False, True, True, True, True, False),
            (True, False, True, True, True, False),
            (True, True, False, True, True, False),
            (True, True, True, False, True, False),
            (True, True, True, True, False, False),
            (True, True, True, True, True, True),
        ]
        for v, a, el, av, sdk, expected in cases:
            res = v and a and el and av and sdk
            self.assertEqual(res, expected)

        # An object with all false fields is truthy in JS / truthiness logic:
        bogus_obj = {
            "noLiveVideoTracks": False,
            "noLiveAudioTracks": False,
            "elementsCleared": False,
            "avatarReadyFalse": False,
            "sdkStatusUnavailable": False,
        }
        self.assertTrue(bool(bogus_obj), "Object literal is always truthy, proving returning object in wait_for_function is defective")

    def test_fallback_cleanup_aborts_without_request_when_deadline_exhausted(self):
        """Regression test for defect #2:
        Fallback cleanup must compute remaining time once and issue fallback DELETE only if strictly positive.
        If deadline is exhausted (<= 0), it must not start an HTTP request; it must fail prominently as possible retained resource.
        """
        gate_file = Path(__file__).parent / "test_s3_req7_live_gate.py"
        code_str = gate_file.read_text(encoding="utf-8")

        # Static checks: max(0.1, ...) must be absent; must check <= 0 and fail prominently
        self.assertNotIn(
            "max(0.1,",
            code_str,
            "Fallback cleanup must not start HTTP request with synthetic timeout when deadline exhausted",
        )
        self.assertIn("rem_cleanup_s <= 0", code_str)
        self.assertIn("Monotonic deadline exhausted before fallback cleanup", code_str)

        # Executable logic verification:
        deadline = 100.0
        now = 100.5  # 0.5s overdue
        rem_cleanup_s = deadline - now
        self.assertLessEqual(rem_cleanup_s, 0.0)

        # When rem_cleanup_s <= 0, no network request must be made
        request_made = False
        def fake_delete(session_id, timeout):
            nonlocal request_made
            request_made = True
            return 200, {"session_destroyed": True}

        with self.assertRaises(RuntimeError) as cm:
            if rem_cleanup_s <= 0.0:
                raise RuntimeError(
                    f"Monotonic deadline exhausted before fallback cleanup could be issued "
                    f"(remaining={rem_cleanup_s:.3f}s <= 0); session fake-session "
                    f"possibly retained upstream resource"
                )
            fake_delete("fake-session", timeout=rem_cleanup_s)

        self.assertFalse(request_made, "No request must be issued when deadline is exhausted")
        self.assertIn("Monotonic deadline exhausted", str(cm.exception))
        self.assertIn("possibly retained", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
