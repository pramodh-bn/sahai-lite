"""Stage 3: "bounded retry for 409/429."

Proves the Verifier-owned retry harness (s3_live_gate.call_with_bounded_retry)
retries only on 409/429, stops after a bounded number of attempts, and
never retries on any other status. Fixtures only -- the "vendor" here is a
local Python callable, never a real network call.
"""
import unittest

from s3_live_gate import MAX_RETRIES, RETRYABLE_STATUSES, call_with_bounded_retry


class TestBoundedRetry(unittest.TestCase):
    def test_retries_on_409_then_succeeds(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] < 3:
                return 409, None
            return 200, "ok"

        status, result, attempts = call_with_bounded_retry(fn, sleep_fn=lambda s: None)
        self.assertEqual(status, 200)
        self.assertEqual(result, "ok")
        self.assertEqual(attempts, 3)
        self.assertEqual(calls["n"], 3)

    def test_retries_on_429_then_succeeds(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] < 2:
                return 429, None
            return 200, "ok"

        status, result, attempts = call_with_bounded_retry(fn, sleep_fn=lambda s: None)
        self.assertEqual(status, 200)
        self.assertEqual(attempts, 2)

    def test_retry_is_bounded_not_infinite(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            return 429, None

        status, result, attempts = call_with_bounded_retry(fn, sleep_fn=lambda s: None)
        self.assertEqual(status, 429, "a permanently-429 call must still return the real status, not raise or hang")
        self.assertEqual(attempts, MAX_RETRIES + 1, "must stop at exactly 1 + MAX_RETRIES attempts")
        self.assertEqual(calls["n"], attempts)

    def test_non_retryable_status_is_not_retried(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            return 500, "server error"

        status, result, attempts = call_with_bounded_retry(fn, sleep_fn=lambda s: None)
        self.assertEqual(status, 500)
        self.assertEqual(attempts, 1)
        self.assertEqual(calls["n"], 1)

    def test_retryable_statuses_are_exactly_409_and_429(self):
        self.assertEqual(set(RETRYABLE_STATUSES), {409, 429})


if __name__ == "__main__":
    unittest.main()
