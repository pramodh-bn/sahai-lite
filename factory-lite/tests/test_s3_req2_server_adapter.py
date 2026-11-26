"""Requirement 2 & 3: Server-side Napster adapter contract and fake-vendor harness.

Contract conventions:
- Server-side Napster session creation endpoint:
    POST /api/rehearsal/sessions/{session_id}/napster-session
- Upstream call uses X-Api-Key and NAPSTER_AGENT_ID at:
    {NAPSTER_BASE_URL}/public/agents/{agent_id}/connections
- Body includes channelType: "webrtc" and externalClientId
- Returns {token, connection_id, status} - NEVER exposes the API key to browser or logs
- Bounded retry: exactly 1 retry (2 attempts max) only for HTTP 409 or 429; no retry for other errors
- Single-flight duplicate rejection: returns 409 conflict if a session is already connecting
- Cleanup endpoint: DELETE /api/rehearsal/sessions/{session_id}/napster-session
"""
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import json
import os
import unittest
import urllib.request
from pathlib import Path

from s2_helpers import AppProcess, app_base_url
from s3_helpers import (
    FakeNapsterServer,
    delete_napster_session,
    post_napster_session,
)


class TestNapsterServerAdapter(unittest.TestCase):
    app = None
    fake_vendor = None

    @classmethod
    def setUpClass(cls):
        # Start fake vendor on loopback
        cls.fake_vendor = FakeNapsterServer()
        cls.fake_vendor.__enter__()
        # Set environment to point app to fake vendor
        os.environ["NAPSTER_BASE_URL"] = cls.fake_vendor.base_url
        os.environ["NAPSTER_API_KEY"] = "fake-napster-key-stage3"
        os.environ["NAPSTER_AGENT_ID"] = "agent-alex-dana-v3"
        cls.app = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()
        if cls.fake_vendor is not None:
            cls.fake_vendor.__exit__(None, None, None)
        os.environ.pop("NAPSTER_BASE_URL", None)
        os.environ.pop("NAPSTER_API_KEY", None)
        os.environ.pop("NAPSTER_AGENT_ID", None)

    def setUp(self):
        self.fake_vendor.clear_requests()
        # Create a fresh rehearsal session
        req = urllib.request.Request(
            f"{app_base_url()}/api/rehearsal/sessions",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.session_id = data["session_id"]

    def test_adapter_creates_agent_scoped_webrtc_session(self):
        status, data = post_napster_session(self.session_id, channel_type="webrtc")
        self.assertEqual(status, 200, f"Expected 200 from napster-session, got {status}: {data}")
        self.assertIn("token", data, "Response missing short-lived connection token")
        self.assertIn("connection_id", data, "Response missing connection_id")

        # Verify upstream call to fake vendor
        reqs = self.fake_vendor.get_requests()
        self.assertTrue(len(reqs) >= 1, "No request received by fake Napster vendor")
        last_req = reqs[-1]
        self.assertEqual(last_req["method"], "POST")
        self.assertIn("/public/agents/agent-alex-dana-v3/connections", last_req["path"])
        self.assertEqual(last_req["headers"].get("X-Api-Key"), "fake-napster-key-stage3")
        self.assertEqual(last_req["body"].get("channelType"), "webrtc")
        self.assertTrue(bool(last_req["body"].get("externalClientId")), "externalClientId missing in vendor payload")

    def test_adapter_never_exposes_api_key_to_browser_or_evidence(self):
        status, data = post_napster_session(self.session_id, channel_type="webrtc")
        self.assertEqual(status, 200)

        # Inspect session response
        raw_json = json.dumps(data)
        self.assertNotIn("fake-napster-key-stage3", raw_json)
        self.assertNotIn("X-Api-Key", raw_json)
        self.assertNotIn("api_key", raw_json.lower())

        # Inspect rehearsal session snapshot
        with urllib.request.urlopen(f"{app_base_url()}/api/rehearsal/sessions/{self.session_id}", timeout=5) as resp:
            snap = json.loads(resp.read().decode("utf-8"))
            snap_json = json.dumps(snap)
            self.assertNotIn("fake-napster-key-stage3", snap_json)
            self.assertNotIn("X-Api-Key", snap_json)

    def test_adapter_honors_configurable_napster_base_url(self):
        # The fake_vendor is already on a dynamic port; verify requests hit it
        status, _ = post_napster_session(self.session_id, channel_type="webrtc")
        self.assertEqual(status, 200)
        self.assertTrue(len(self.fake_vendor.get_requests()) > 0, "Requests did not reach configured NAPSTER_BASE_URL")

    def test_adapter_retries_bounded_only_on_409_and_429(self):
        # Case 1: 429 followed by 200 -> succeeds after exactly 2 requests
        self.fake_vendor.clear_requests()
        self.fake_vendor.set_response_sequence([429, 200])
        status, data = post_napster_session(self.session_id, channel_type="webrtc")
        self.assertEqual(status, 200, f"Expected retry success on 429, got {status}: {data}")
        self.assertEqual(len(self.fake_vendor.get_requests()), 2, "Expected exactly 2 requests (1 bounded retry) for 429")

        # Case 2: 409 followed by 200 -> succeeds after exactly 2 requests
        self.fake_vendor.clear_requests()
        self.fake_vendor.set_response_sequence([409, 200])
        status, data = post_napster_session(self.session_id, channel_type="webrtc")
        self.assertEqual(status, 200, f"Expected retry success on 409, got {status}: {data}")
        self.assertEqual(len(self.fake_vendor.get_requests()), 2, "Expected exactly 2 requests (1 bounded retry) for 409")

        # Case 3: persistent 429 -> fails after bounded 2 attempts (no endless retry loop)
        self.fake_vendor.clear_requests()
        self.fake_vendor.set_response_sequence([429, 429, 429])
        status, _ = post_napster_session(self.session_id, channel_type="webrtc")
        self.assertIn(status, (429, 502, 503), f"Expected failure status for exhausted 429 retries, got {status}")
        self.assertEqual(len(self.fake_vendor.get_requests()), 2, "Expected strictly bounded retry limit of 2 attempts")

    def test_adapter_does_not_retry_on_400_401_403_or_500(self):
        for unretryable_code in (400, 401, 403, 500):
            with self.subTest(code=unretryable_code):
                self.fake_vendor.clear_requests()
                self.fake_vendor.set_response_sequence([unretryable_code, 200])
                status, _ = post_napster_session(self.session_id, channel_type="webrtc")
                self.assertNotEqual(status, 200, f"Expected immediate failure on HTTP {unretryable_code}")
                self.assertEqual(
                    len(self.fake_vendor.get_requests()),
                    1,
                    f"HTTP {unretryable_code} must not be retried; expected 1 attempt only",
                )

    def test_adapter_single_flight_duplicate_rejection(self):
        self.fake_vendor.set_simulate_inflight_conflict(True)
        # Attempt duplicate creation
        self.fake_vendor.set_response_sequence([200])
        status1, _ = post_napster_session(self.session_id, channel_type="webrtc")
        # Attempting second connect on the same active session
        status2, data2 = post_napster_session(self.session_id, channel_type="webrtc")
        self.assertEqual(status2, 409, f"Duplicate session connection must return 409 conflict: {data2}")
        self.fake_vendor.set_simulate_inflight_conflict(False)

    def test_adapter_cleanup_on_session_delete_and_error(self):
        # Create session first
        status, _ = post_napster_session(self.session_id, channel_type="webrtc")
        self.assertEqual(status, 200)

        # Call DELETE
        del_status, del_data = delete_napster_session(self.session_id)
        self.assertEqual(del_status, 200, f"DELETE /napster-session failed: {del_data}")


if __name__ == "__main__":
    unittest.main()
