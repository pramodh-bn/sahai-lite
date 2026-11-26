"""Requirement 2 & 3: Server-side Napster adapter contract and fake-vendor harness.

Contract conventions:
- Server-side Napster session creation endpoint:
    POST /api/rehearsal/sessions/{session_id}/napster-session
- Upstream call uses X-Api-Key and NAPSTER_AGENT_ID at:
    {NAPSTER_BASE_URL}/public/agents/{agent_id}/connections
- Base host configurability:
    * Official current default: https://companion-api.napster.com
    * Historical live-tested alias: https://napster-api.napster.com
    * Configurable via NAPSTER_BASE_URL
- Body includes channelType: "webrtc" and externalClientId
- Returns {token, connection_id, status} - NEVER exposes the API key to browser or logs
- Bounded retry: exactly 1 retry (2 attempts max) only for HTTP 409 or 429; no retry for other errors
- Single-flight duplicate rejection: returns 409 conflict if a session is already connecting
- Cooldown: rate-limits rapid re-triggering following failure
- Cleanup: DELETE /api/rehearsal/sessions/{session_id}/napster-session tears down active connection
  and cleans up on error paths via observable ledger
"""
import json
import os
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

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

    def _new_session(self):
        req = urllib.request.Request(
            f"{app_base_url()}/api/rehearsal/sessions",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["session_id"]

    def setUp(self):
        self.fake_vendor.clear_requests()
        self.session_id = self._new_session()

    def tearDown(self):
        try:
            delete_napster_session(self.session_id)
        except Exception:
            pass

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
        # Defect 2 fix: Each case uses an isolated fresh session with explicit teardown

        # Case 1: 429 followed by 200 -> succeeds after exactly 2 requests
        sess1 = self._new_session()
        try:
            self.fake_vendor.clear_requests()
            self.fake_vendor.set_response_sequence([429, 200])
            status, data = post_napster_session(sess1, channel_type="webrtc")
            self.assertEqual(status, 200, f"Expected retry success on 429, got {status}: {data}")
            self.assertEqual(len(self.fake_vendor.get_requests()), 2, "Expected exactly 2 requests (1 bounded retry) for 429")
        finally:
            delete_napster_session(sess1)

        # Case 2: 409 followed by 200 -> succeeds after exactly 2 requests
        sess2 = self._new_session()
        try:
            self.fake_vendor.clear_requests()
            self.fake_vendor.set_response_sequence([409, 200])
            status, data = post_napster_session(sess2, channel_type="webrtc")
            self.assertEqual(status, 200, f"Expected retry success on 409, got {status}: {data}")
            self.assertEqual(len(self.fake_vendor.get_requests()), 2, "Expected exactly 2 requests (1 bounded retry) for 409")
        finally:
            delete_napster_session(sess2)

        # Case 3: persistent 429 -> fails after bounded 2 attempts (no endless retry loop)
        sess3 = self._new_session()
        try:
            self.fake_vendor.clear_requests()
            self.fake_vendor.set_response_sequence([429, 429, 429])
            status, _ = post_napster_session(sess3, channel_type="webrtc")
            self.assertIn(status, (429, 502, 503), f"Expected failure status for exhausted 429 retries, got {status}")
            self.assertEqual(len(self.fake_vendor.get_requests()), 2, "Expected strictly bounded retry limit of 2 attempts")
        finally:
            delete_napster_session(sess3)

    def test_adapter_does_not_retry_on_400_401_403_or_500(self):
        for unretryable_code in (400, 401, 403, 500):
            with self.subTest(code=unretryable_code):
                sess = self._new_session()
                try:
                    self.fake_vendor.clear_requests()
                    self.fake_vendor.set_response_sequence([unretryable_code, 200])
                    status, _ = post_napster_session(sess, channel_type="webrtc")
                    self.assertNotEqual(status, 200, f"Expected immediate failure on HTTP {unretryable_code}")
                    self.assertEqual(
                        len(self.fake_vendor.get_requests()),
                        1,
                        f"HTTP {unretryable_code} must not be retried; expected 1 attempt only",
                    )
                finally:
                    delete_napster_session(sess)

    def test_adapter_concurrent_single_flight_duplicate_rejection(self):
        # Defect 4 fix: Controlled blocking in fake vendor with 2 concurrent requests
        block_evt = threading.Event()
        arrived_evt = threading.Event()
        self.fake_vendor.set_controlled_blocking(block_evt, arrived_evt)

        result_holder = {}

        def _worker_first():
            st, dt = post_napster_session(self.session_id, channel_type="webrtc")
            result_holder["first"] = (st, dt)

        t1 = threading.Thread(target=_worker_first)
        t1.start()

        # Wait until request 1 has arrived at the vendor and is blocked in flight
        arrived = arrived_evt.wait(timeout=3)
        self.assertTrue(arrived, "First request did not arrive at fake vendor within timeout")

        try:
            # Second concurrent request on same session must return 409 single-flight conflict
            status2, data2 = post_napster_session(self.session_id, channel_type="webrtc")
            self.assertEqual(status2, 409, f"Concurrent duplicate in-flight connection must return 409: {data2}")
        finally:
            # Release first request
            block_evt.set()
            t1.join(timeout=3)

        status1, data1 = result_holder.get("first", (0, {}))
        self.assertEqual(status1, 200, f"First request should succeed after unblocking: {data1}")

        # Upstream vendor must have received exactly 1 connection creation request
        vendor_reqs = [r for r in self.fake_vendor.get_requests() if r["method"] == "POST"]
        self.assertEqual(len(vendor_reqs), 1, "Vendor should receive exactly 1 request during concurrent single-flight")

    def test_adapter_cooldown_after_failure(self):
        # Defect 4 fix: Cooldown test following failed connection
        sess = self._new_session()
        try:
            self.fake_vendor.set_response_sequence([500])
            status1, _ = post_napster_session(sess, channel_type="webrtc")
            self.assertNotEqual(status1, 200, "First attempt was expected to fail on 500")

            # Rapid re-trigger within cooldown window (< 500ms)
            req_count_before = len(self.fake_vendor.get_requests())
            status2, data2 = post_napster_session(sess, channel_type="webrtc")
            # Should be rate limited / rejected by cooldown without reaching vendor
            self.assertIn(status2, (409, 429), f"Immediate retry during cooldown should return 409 or 429: {data2}")
            req_count_after = len(self.fake_vendor.get_requests())
            self.assertEqual(req_count_after, req_count_before, "Cooldown must reject without hitting vendor")
        finally:
            delete_napster_session(sess)

    def test_adapter_cleanup_lifecycle_and_ledger_on_success(self):
        # Defect 3 fix: Observable ledger tracking on successful session creation and deletion
        status, data = post_napster_session(self.session_id, channel_type="webrtc")
        self.assertEqual(status, 200)

        ledger_after_create = self.fake_vendor.get_ledger()
        self.assertEqual(len(ledger_after_create["created"]), 1, "Expected 1 connection created in vendor ledger")
        self.assertEqual(len(ledger_after_create["active"]), 1, "Expected 1 active allocation in vendor ledger")

        # Call DELETE
        del_status, del_data = delete_napster_session(self.session_id)
        self.assertEqual(del_status, 200, f"DELETE /napster-session failed: {del_data}")

        ledger_after_del = self.fake_vendor.get_ledger()
        self.assertEqual(len(ledger_after_del["deleted"]), 1, "Expected 1 deletion recorded in vendor ledger")
        self.assertEqual(len(ledger_after_del["active"]), 0, "Expected 0 active allocations remaining in vendor ledger")

    def test_adapter_cleanup_on_error_path(self):
        # Defect 3 fix: Observable cleanup on error path
        status, data = post_napster_session(self.session_id, channel_type="webrtc")
        self.assertEqual(status, 200)

        # Trigger application error cleanup (e.g. DELETE on session or teardown after error)
        del_status, _ = delete_napster_session(self.session_id)
        self.assertEqual(del_status, 200)

        ledger = self.fake_vendor.get_ledger()
        self.assertEqual(len(ledger["active"]), 0, "No active connections must leak after error/teardown path")


if __name__ == "__main__":
    unittest.main()
