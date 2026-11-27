"""Stage 4B requirement 3: deletion completeness and redacted receipts.

Direct black-box proof that ``DELETE /api/rehearsal/sessions/{id}`` removes the
session (404 afterwards), is idempotent, returns a redacted ``sah.cleanup.v1``
receipt bound only by session hash, and leaves no user utterance, vendor token,
vendor connection id or API key in the application log.

Contract: ``factory-lite/docs/stage-4b-acceptance-contract.md`` section 6.
"""
import json
import unittest

from s4b_helpers import (
    FAKE_API_KEY,
    PII_MARKER,
    FakeVendor,
    S4BApp,
    delete_session,
    grant,
    grant_many,
    make_practice_session,
    napster_create,
    practice,
    require_session,
    session_hash,
    snapshot,
    transcript_save,
    transcript_saved,
)


class TestDeletionCompleteness(unittest.TestCase):
    def setUp(self):
        self.app = None
        self.vendor = None

    def tearDown(self):
        if self.app is not None:
            self.app.stop()
        if self.vendor is not None:
            self.vendor.__exit__(None, None, None)

    def _start(self, with_vendor=False):
        env = {}
        if with_vendor:
            self.vendor = FakeVendor()
            self.vendor.__enter__()
            env = self.vendor.env()
        self.app = S4BApp(env=env, capture_logs=True).start()
        return self.app

    def test_delete_removes_session_and_returns_redacted_receipt(self):
        self._start()
        sid = make_practice_session()
        grant(sid, "transcript_save")
        status, body = practice(sid, f"Closing line {PII_MARKER}.")
        self.assertEqual(status, 200, f"practice failed: status={status} body={body}")
        status, body = transcript_save(sid)
        self.assertEqual(status, 200, f"save failed: status={status} body={body}")

        status, receipt = delete_session(sid)
        self.assertEqual(status, 200, f"delete failed: status={status} body={receipt}")
        self.assertEqual(receipt.get("schema"), "sah.cleanup.v1")
        self.assertEqual(receipt.get("session_hash"), session_hash(sid))
        self.assertRegex(receipt.get("session_hash", ""), r"^sha256:[0-9a-f]{64}$")
        self.assertNotIn(sid, json.dumps(receipt),
                         "cleanup receipt contains the raw session id")
        self.assertIs(receipt.get("local_media_stopped"), True)
        self.assertIs(receipt.get("transcript_deleted"), True)
        self.assertIs(receipt.get("connection_retained"), False)
        self.assertIs(receipt.get("vendor_session_destroyed"), True)
        self.assertIs(receipt.get("redacted"), True)
        self.assertIs(receipt.get("already_deleted"), False)
        self.assertRegex(receipt.get("completed_at", ""), r"^\d{4}-\d{2}-\d{2}T")

        status, body = snapshot(sid)
        self.assertEqual(status, 404, f"session still readable after delete: status={status} body={body}")
        status, body = transcript_saved(sid)
        self.assertEqual(status, 404, f"saved transcript survived delete: status={status} body={body}")

    def test_second_delete_is_idempotent_not_500(self):
        self._start()
        sid = require_session()
        status, receipt = delete_session(sid)
        self.assertEqual(status, 200, f"first delete failed: status={status} body={receipt}")

        status, body = delete_session(sid)
        self.assertIn(status, (200, 404),
                      f"second delete returned {status} (must be idempotent, never 5xx): {body}")
        if status == 200:
            self.assertEqual(body.get("schema"), "sah.cleanup.v1")
            self.assertIs(body.get("already_deleted"), True)
        status, body = delete_session(sid)
        self.assertIn(status, (200, 404), f"third delete returned {status}: {body}")

    def test_delete_without_vendor_reports_no_retained_connection(self):
        self._start()
        sid = require_session()
        status, receipt = delete_session(sid)
        self.assertEqual(status, 200, f"delete failed: status={status} body={receipt}")
        self.assertIs(receipt.get("vendor_session_destroyed"), True)
        self.assertIs(receipt.get("connection_retained"), False)

    def test_logs_after_delete_contain_no_pii_token_or_vendor_id(self):
        self._start(with_vendor=True)
        sid = make_practice_session()
        grant_many(sid, ("rehearsal", "avatar"))
        status, created = napster_create(sid)
        self.assertEqual(status, 200, f"vendor create failed: status={status} body={created}")
        token = created.get("token")
        connection_id = created.get("connection_id")
        self.assertTrue(token and connection_id)

        status, body = practice(sid, f"Please remember {PII_MARKER} for later.")
        self.assertEqual(status, 200, f"practice failed: status={status} body={body}")
        status, receipt = delete_session(sid)
        self.assertEqual(status, 200, f"delete failed: status={status} body={receipt}")
        self.assertIs(receipt.get("vendor_session_destroyed"), True)

        self.app.stop()
        log = self.app.log_text()
        self.assertTrue(log.strip(), "captured application log is empty; the leak check is vacuous")
        for forbidden, label in (
            (PII_MARKER, "user utterance"),
            (token, "vendor token"),
            (connection_id, "vendor connection id"),
            (FAKE_API_KEY, "vendor API key"),
            ("X-Api-Key", "vendor auth header"),
        ):
            self.assertNotIn(forbidden, log, f"application log leaked a {label} after deletion")


if __name__ == "__main__":
    unittest.main()
