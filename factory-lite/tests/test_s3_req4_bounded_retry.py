"""Stage 3: "bounded retry for 409/429."

Black-box subprocess test of the frozen app/napster_adapter.py CLI
against a local fake vendor (s3_fake_vendor.py) that scripts 409/429
responses. Exercises the real app-owned integration; must fail against
the exact base, where app/napster_adapter.py does not exist yet.

Per CONTRACT.md "Stage 3 adapter CLI": the adapter retries a 409/429
response up to MAX_RETRIES (3) additional times (4 attempts total per
vendor call) before giving up.
"""
import tempfile
import unittest
from pathlib import Path

from s3_adapter_client import run_adapter
from s3_fake_vendor import FakeVendorServer
from s3_live_gate import MAX_RETRIES


class TestBoundedRetry(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="s3-retry-test-")
        self.state_dir = Path(self._tmp.name) / "state"
        self.evidence_dir = Path(self._tmp.name) / "evidence"
        self.state_dir.mkdir(parents=True)
        self.evidence_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_retries_409_then_succeeds(self):
        with FakeVendorServer() as vendor:
            vendor.script("/v1/sessions", [409, 409, 200])
            code, parsed, out, err = run_adapter("audio", vendor.base_url, self.state_dir, self.evidence_dir)
            attempts = vendor.request_count("/v1/sessions")
        self.assertEqual(code, 0, f"stdout={out!r} stderr={err!r}")
        self.assertEqual(attempts, 3, "adapter must retry exactly until the vendor succeeds")

    def test_retries_429_then_succeeds(self):
        with FakeVendorServer() as vendor:
            vendor.script("/v1/sessions", [429, 200])
            code, parsed, out, err = run_adapter("companion_avatar", vendor.base_url, self.state_dir, self.evidence_dir)
            attempts = vendor.request_count("/v1/sessions")
        self.assertEqual(code, 0, f"stdout={out!r} stderr={err!r}")
        self.assertEqual(attempts, 2)

    def test_retry_is_bounded_not_infinite(self):
        with FakeVendorServer() as vendor:
            vendor.script("/v1/sessions", [429])  # repeats forever
            code, parsed, out, err = run_adapter("handoff", vendor.base_url, self.state_dir, self.evidence_dir)
            attempts = vendor.request_count("/v1/sessions")
        self.assertNotEqual(code, 0, "a permanently-429 vendor must not be reported as success")
        self.assertEqual(
            attempts, MAX_RETRIES + 1,
            f"adapter must stop at exactly 1 + MAX_RETRIES ({MAX_RETRIES}) attempts, made {attempts}",
        )
        self.assertFalse(
            (self.state_dir / "handoff.lock").exists(),
            "cleanup must still run after retries are exhausted",
        )

    def test_non_retryable_status_is_not_retried(self):
        with FakeVendorServer() as vendor:
            vendor.script("/v1/sessions", [500])
            code, parsed, out, err = run_adapter("audio", vendor.base_url, self.state_dir, self.evidence_dir)
            attempts = vendor.request_count("/v1/sessions")
        self.assertNotEqual(code, 0)
        self.assertEqual(attempts, 1, "a non-retryable status (500) must not trigger a retry loop")


if __name__ == "__main__":
    unittest.main()
