"""Stage 3: "no duplicate sessions," "cleanup on error."

Black-box subprocess test of the frozen app/napster_adapter.py CLI (see
CONTRACT.md "Stage 3 adapter CLI") against a local fake vendor
(s3_fake_vendor.py). This exercises the real app-owned integration, not
Verifier test tooling: it must fail against the exact base, where
app/napster_adapter.py does not exist yet.

Exit codes per CONTRACT.md: 0 success, 2 usage/config error, 3 duplicate
rejected, 4 vendor error after exhausting retries.
"""
import tempfile
import unittest
from pathlib import Path

from s3_adapter_client import run_adapter
from s3_fake_vendor import FakeVendorServer


class TestSessionLifecycle(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="s3-adapter-test-")
        self.state_dir = Path(self._tmp.name) / "state"
        self.evidence_dir = Path(self._tmp.name) / "evidence"
        self.state_dir.mkdir(parents=True)
        self.evidence_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_cleanup_runs_on_success_and_writes_evidence(self):
        with FakeVendorServer() as vendor:
            code, parsed, out, err = run_adapter("audio", vendor.base_url, self.state_dir, self.evidence_dir)
        self.assertEqual(code, 0, f"stdout={out!r} stderr={err!r}")
        self.assertIsNotNone(parsed, f"adapter must print one JSON line; got stdout={out!r}")
        self.assertEqual(parsed.get("outcome"), "success")
        self.assertFalse(
            (self.state_dir / "audio.lock").exists(),
            "lock file for 'audio' must be removed after a successful run",
        )
        evidence_files = list(self.evidence_dir.glob("*.json"))
        self.assertEqual(len(evidence_files), 1, "exactly one evidence file must be written on success")

    def test_duplicate_session_for_same_capability_is_rejected_without_a_vendor_call(self):
        (self.state_dir / "companion_avatar.lock").write_text("held", encoding="utf-8")
        with FakeVendorServer() as vendor:
            code, parsed, out, err = run_adapter("companion_avatar", vendor.base_url, self.state_dir, self.evidence_dir)
            self.assertEqual(vendor.request_count(), 0, "a duplicate-rejected run must never call the vendor")
        self.assertEqual(code, 3, f"stdout={out!r} stderr={err!r}")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.get("outcome"), "duplicate_rejected")

    def test_cleanup_runs_on_vendor_error_and_capability_is_freed_afterward(self):
        with FakeVendorServer() as vendor:
            vendor.script("/v1/sessions", [500])
            code, parsed, out, err = run_adapter("handoff", vendor.base_url, self.state_dir, self.evidence_dir)
        self.assertNotEqual(code, 0, "a permanent vendor error must not be reported as success")
        self.assertFalse(
            (self.state_dir / "handoff.lock").exists(),
            "cleanup must remove the lock even when the vendor call ultimately fails",
        )

        # Freed: a fresh run for the same capability now succeeds.
        with FakeVendorServer() as vendor:
            code, parsed, out, err = run_adapter("handoff", vendor.base_url, self.state_dir, self.evidence_dir)
        self.assertEqual(code, 0, f"stdout={out!r} stderr={err!r}")

    def test_handoff_is_the_sah_product_handoff_not_a_sip_transfer(self):
        """Req: "never claim SIP/meeting relay/control... treat documented
        SIP transfer as vendor context, not the product handoff." The
        adapter's handoff request body must use the product's own
        handoff_type, never a SIP/meeting-transfer vocabulary."""
        with FakeVendorServer() as vendor:
            run_adapter("handoff", vendor.base_url, self.state_dir, self.evidence_dir)
            handoff_requests = [b for (_, path, b) in vendor.requests if path.endswith("/handoff")]
        self.assertTrue(handoff_requests, "adapter never called the handoff endpoint")
        for body in handoff_requests:
            self.assertEqual(body.get("handoff_type"), "embodied_demo_to_practice")
            dumped = str(body).lower()
            for banned in ("sip", "transfer", "meeting", "relay"):
                self.assertNotIn(banned, dumped, f"handoff request body must not reference {banned!r}")


if __name__ == "__main__":
    unittest.main()
