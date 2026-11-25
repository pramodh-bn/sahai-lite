"""Stage 3: "no duplicate sessions," "cleanup on error."

Proves the Verifier-owned session-registry harness (s3_live_gate.py),
which the authorized live probe must use, actually enforces: at most one
active session per capability, and cleanup runs exactly once whether the
session body succeeds or raises. Fixtures only -- no vendor call, no
network, no real Napster session is ever opened by this test.
"""
import unittest

from s3_live_gate import DuplicateSessionError, SessionRegistry


class TestSessionLifecycle(unittest.TestCase):
    def test_duplicate_session_for_same_capability_is_rejected(self):
        registry = SessionRegistry()
        cleaned = []
        with registry.session("companion_avatar", lambda: cleaned.append("first")):
            with self.assertRaises(DuplicateSessionError):
                registry.session("companion_avatar", lambda: cleaned.append("second"))

    def test_cleanup_runs_on_success(self):
        registry = SessionRegistry()
        cleaned = []
        with registry.session("audio", lambda: cleaned.append("audio")):
            pass
        self.assertEqual(cleaned, ["audio"])

    def test_cleanup_runs_on_error_and_the_capability_is_freed_afterward(self):
        registry = SessionRegistry()
        cleaned = []
        with self.assertRaises(RuntimeError):
            with registry.session("handoff", lambda: cleaned.append("handoff")):
                raise RuntimeError("boom")
        self.assertEqual(cleaned, ["handoff"], "cleanup did not run when the session body raised")

        # Freed: starting a new session for the same capability now succeeds.
        with registry.session("handoff", lambda: cleaned.append("handoff-2")):
            pass
        self.assertEqual(cleaned, ["handoff", "handoff-2"])

    def test_cleanup_is_idempotent_if_called_manually_before_context_exit(self):
        registry = SessionRegistry()
        cleaned = []
        with registry.session("companion_avatar", lambda: cleaned.append("x")) as sess:
            sess.cleanup()
            sess.cleanup()  # second call must not clean up twice
        self.assertEqual(cleaned, ["x"])

    def test_different_capabilities_can_run_concurrently(self):
        registry = SessionRegistry()
        with registry.session("audio", lambda: None):
            with registry.session("handoff", lambda: None):
                pass  # no DuplicateSessionError for a different capability


if __name__ == "__main__":
    unittest.main()
