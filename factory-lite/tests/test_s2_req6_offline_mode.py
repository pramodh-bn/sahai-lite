"""Stage 2: "Offline mode clearly labeled."

Contract convention: every session-creation response and every session
snapshot must carry an explicit "mode" field equal to "offline" -- Stage 2
makes no live/paid calls, and that must be visible in the API itself, not
just in documentation. All requests in this suite (like the rest of the
contract) only ever reach the localhost URL documented in app/RUN.md.
"""
import unittest

from s2_helpers import AppProcess, post_json, get_json


class TestOfflineModeLabeled(unittest.TestCase):
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = AppProcess().start()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            cls.app.stop()

    def test_session_creation_response_labels_offline_mode(self):
        status, body = post_json("/api/rehearsal/sessions")
        self.assertEqual(status, 201, f"body={body}")
        self.assertEqual(body.get("mode"), "offline", f"session creation did not label offline mode: {body}")

    def test_session_snapshot_labels_offline_mode(self):
        _, created = post_json("/api/rehearsal/sessions")
        sid = created["session_id"]
        status, snapshot = get_json(f"/api/rehearsal/sessions/{sid}")
        self.assertEqual(status, 200)
        self.assertEqual(snapshot.get("mode"), "offline", f"session snapshot did not label offline mode: {snapshot}")


if __name__ == "__main__":
    unittest.main()
