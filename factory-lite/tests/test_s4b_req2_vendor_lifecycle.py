"""Stage 4B requirement 2: application-connected fake vendor lifecycle.

The app is configured (``NAPSTER_BASE_URL`` etc.) to point at a loopback fake
vendor. These tests observe, at the application boundary, that a consented
create reaches the configured vendor exactly once, that teardown deletes the
same record exactly once, that a post-allocation error retains the handle and
a later cleanup completes it, and that a restarted process with a stored
handle (``SAH_STATE_DIR``) can still delete it.

Contract: ``factory-lite/docs/stage-4b-acceptance-contract.md`` sections 3, 5, 6.
"""
import json
import shutil
import tempfile
import unittest

from s4b_helpers import (
    FAKE_AGENT_ID,
    FAKE_API_KEY,
    FakeVendor,
    S4BApp,
    delete_session,
    grant_many,
    make_practice_session,
    napster_create,
    snapshot,
)


class TestVendorLifecycle(unittest.TestCase):
    app = None
    vendor = None

    @classmethod
    def setUpClass(cls):
        cls.vendor = FakeVendor()
        cls.vendor.__enter__()
        cls.app = S4BApp(env=cls.vendor.env(), capture_logs=False).start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()
        if cls.vendor is not None:
            cls.vendor.__exit__(None, None, None)

    def setUp(self):
        self.vendor.reset()
        self.sid = make_practice_session()

    def _consent(self, scopes=("rehearsal", "avatar")):
        grant_many(self.sid, scopes)

    def _create(self):
        status, body = napster_create(self.sid)
        self.assertEqual(status, 200, f"consented create failed: status={status} body={body}")
        return body

    def test_consented_create_reaches_the_configured_vendor(self):
        self._consent()
        body = self._create()
        self.assertTrue(body.get("token"), "create response carries no vendor token")
        self.assertTrue(body.get("connection_id"), "create response carries no connection id")
        self.assertNotIn(FAKE_API_KEY, json.dumps(body),
                         "create response leaked the vendor API key")

        requests = self.vendor.requests()
        posts = [r for r in requests if r["method"] == "POST"]
        self.assertEqual(len(posts), 1, f"expected one upstream create, saw {posts}")
        self.assertIn(f"/public/agents/{FAKE_AGENT_ID}/connections", posts[0]["path"])
        self.assertEqual(posts[0]["headers"].get("X-Api-Key"), FAKE_API_KEY)
        self.assertEqual(self.vendor.ledger()["created_count"], 1)

    def test_session_delete_destroys_the_vendor_record_exactly_once(self):
        self._consent()
        body = self._create()
        connection_id = body["connection_id"]

        status, receipt = delete_session(self.sid)
        self.assertEqual(status, 200, f"delete failed: status={status} body={receipt}")
        self.assertEqual(receipt.get("schema"), "sah.cleanup.v1")
        self.assertIs(receipt.get("vendor_session_destroyed"), True)
        self.assertIs(receipt.get("connection_retained"), False)

        ledger = self.vendor.ledger()
        self.assertEqual(ledger["created_count"], 1)
        self.assertEqual(len(ledger["deleted"]), 1,
                         f"expected exactly one upstream delete, saw {ledger}")
        self.assertIn(connection_id, ledger["deleted"][0])

        status2, body2 = delete_session(self.sid)
        self.assertIn(status2, (200, 404),
                      f"second delete must be idempotent, got {status2}: {body2}")
        ledger2 = self.vendor.ledger()
        self.assertEqual(ledger2["created_count"], 1, "idempotent delete created a new vendor record")
        self.assertEqual(len(ledger2["deleted"]), 1,
                         "idempotent delete sent another upstream delete")

    def test_post_allocation_failure_retains_handle_and_cleanup_completes(self):
        self._consent()
        self.vendor.fail_next_deletes(1)
        status, body = napster_create(self.sid, simulate_error="post_allocation_failure")
        self.assertEqual(status, 502, f"body={body}")
        self.assertIs(body.get("connection_retained"), True,
                      f"failed rollback did not retain the handle: {body}")
        self.assertEqual(self.vendor.ledger()["created_count"], 1,
                         "simulated failure created more than one vendor record")

        status, receipt = delete_session(self.sid)
        self.assertEqual(status, 200, f"cleanup failed with status={status}: {receipt}")
        self.assertIs(receipt.get("vendor_session_destroyed"), True)
        self.assertIs(receipt.get("connection_retained"), False)
        ledger = self.vendor.ledger()
        self.assertEqual(ledger["created_count"], 1,
                         "cleanup created a second vendor record")
        self.assertEqual(len(ledger["deleted"]), 1,
                         f"cleanup did not delete the retained handle exactly once: {ledger}")

    def test_failed_cleanup_on_delete_is_reported_then_retried(self):
        self._consent()
        body = self._create()
        connection_id = body["connection_id"]
        self.vendor.fail_next_deletes(1)

        status, receipt = delete_session(self.sid)
        self.assertEqual(status, 200, f"local delete must not 500: status={status} body={receipt}")
        self.assertIs(receipt.get("vendor_session_destroyed"), False)
        self.assertIs(receipt.get("connection_retained"), True)
        self.assertIs(receipt.get("local_media_stopped"), True)
        status, body = snapshot(self.sid)
        self.assertEqual(status, 404, f"local session survived deletion: status={status} body={body}")

        status, receipt = delete_session(self.sid)
        self.assertEqual(status, 200, f"retry failed with status={status}: {receipt}")
        self.assertIs(receipt.get("vendor_session_destroyed"), True)
        self.assertIs(receipt.get("connection_retained"), False)

        ledger = self.vendor.ledger()
        self.assertEqual(ledger["created_count"], 1)
        self.assertEqual(len(ledger["deleted"]), 1)
        self.assertIn(connection_id, ledger["deleted"][0])

        status, body = delete_session(self.sid)
        self.assertIn(status, (200, 404), f"third delete failed: {status} {body}")


class TestRestartRecovery(unittest.TestCase):
    def setUp(self):
        self.vendor = FakeVendor()
        self.vendor.__enter__()
        self.state_dir = tempfile.mkdtemp(prefix="sah-s4b-state-")
        self.apps = []

    def tearDown(self):
        for app in self.apps:
            try:
                app.stop()
            except Exception:
                pass
        self.vendor.__exit__(None, None, None)
        shutil.rmtree(self.state_dir, ignore_errors=True)

    def _start(self):
        env = dict(self.vendor.env())
        env["SAH_STATE_DIR"] = self.state_dir
        app = S4BApp(env=env, capture_logs=False).start()
        self.apps.append(app)
        return app

    def test_restart_with_stored_handle_deletes_it_exactly_once(self):
        app1 = self._start()
        sid = make_practice_session()
        grant_many(sid, ("rehearsal", "avatar"))
        status, created = napster_create(sid)
        self.assertEqual(status, 200, f"body={created}")
        connection_id = created["connection_id"]
        self.assertEqual(self.vendor.ledger()["created_count"], 1)
        app1.stop()

        self._start()
        status, receipt = delete_session(sid)
        self.assertEqual(status, 200,
                         f"restarted process could not clean the stored handle: status={status} body={receipt}")
        self.assertIs(receipt.get("vendor_session_destroyed"), True)
        self.assertIs(receipt.get("connection_retained"), False)
        ledger = self.vendor.ledger()
        self.assertEqual(ledger["created_count"], 1, "cleanup after restart created a new vendor record")
        self.assertEqual(len(ledger["deleted"]), 1,
                         f"stored handle was not deleted exactly once: {ledger}")
        self.assertIn(connection_id, ledger["deleted"][0])

        status, body = snapshot(sid)
        self.assertEqual(status, 404, f"body={body}")
        status, body = delete_session(sid)
        self.assertIn(status, (200, 404), f"second delete after restart failed: {status} {body}")
        self.assertEqual(self.vendor.ledger()["created_count"], 1)


if __name__ == "__main__":
    unittest.main()
