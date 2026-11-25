"""Shared, vendor-agnostic test tooling for the Stage 3 authorized live
Napster probe. Not a test module itself (doesn't match test_*.py).

Defines, and is proven here (factory-lite/tests/test_s3_req3/4_*.py)
against local fixtures only, never a real vendor:
  - the live-authorization gate check (live_gate_status)
  - a bounded-retry helper for 409/429 (call_with_bounded_retry)
  - a session registry that rejects a duplicate start per capability and
    guarantees cleanup exactly once on success or error (SessionRegistry)
  - a redacted-evidence schema + redact() helper, used by
    test_s3_live_napster.py if/when the owner enables the live gate
"""
import os

LIVE_GATE_ENV = "SAH_NAPSTER_LIVE"
REQUIRED_CREDENTIAL_ENV_VARS = ("NAPSTER_API_KEY",)
MAX_RETRIES = 3
RETRYABLE_STATUSES = (409, 429)

REDACTED_EVIDENCE_SCHEMA_FIELDS = (
    "probe_id",
    "capability",
    "started_at",
    "ended_at",
    "outcome",
    "http_status",
    "redacted",
    "evidence_text",
)
SENSITIVE_KEY_MARKERS = ("key", "token", "secret", "password", "credential", "authorization")


def live_gate_status():
    """Return (is_open, reason). Never raises; never includes a secret
    value in the reason string -- only env *var names*, never values."""
    if os.environ.get(LIVE_GATE_ENV) != "1":
        return False, f"{LIVE_GATE_ENV} is not set to '1'"
    missing = [v for v in REQUIRED_CREDENTIAL_ENV_VARS if not os.environ.get(v)]
    if missing:
        return False, f"missing required credential env var(s): {missing}"
    return True, "authorized"


def redact(evidence):
    """Return a copy of evidence with any sensitive-looking key's value
    masked, regardless of what that value is."""
    out = {}
    for key, value in evidence.items():
        if any(marker in key.lower() for marker in SENSITIVE_KEY_MARKERS):
            out[key] = "REDACTED"
        else:
            out[key] = value
    return out


class DuplicateSessionError(Exception):
    pass


class SessionRegistry:
    """Tracks at most one active probe session per capability name;
    rejects a duplicate start and guarantees cleanup() runs exactly once
    per started session, whether its body succeeds or raises."""

    def __init__(self):
        self._active = set()

    def session(self, capability, cleanup_fn):
        if capability in self._active:
            raise DuplicateSessionError(f"a session for {capability!r} is already active")
        self._active.add(capability)
        return _SessionContext(self, capability, cleanup_fn)


class _SessionContext:
    def __init__(self, registry, capability, cleanup_fn):
        self._registry = registry
        self._capability = capability
        self._cleanup_fn = cleanup_fn
        self._cleaned_up = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()
        return False  # never swallow exceptions

    def cleanup(self):
        if not self._cleaned_up:
            self._cleaned_up = True
            self._registry._active.discard(self._capability)
            self._cleanup_fn()


def call_with_bounded_retry(fn, max_retries=MAX_RETRIES, retryable_statuses=RETRYABLE_STATUSES, sleep_fn=lambda seconds: None):
    """Call fn() -> (status, result) up to 1 + max_retries times total.
    Retries only while status is in retryable_statuses; any other status,
    including a still-retryable one once the bound is hit, is returned
    as-is (never raises on behalf of the caller). Returns
    (status, result, attempts_made)."""
    attempt = 0
    while True:
        attempt += 1
        status, result = fn()
        if status not in retryable_statuses:
            return status, result, attempt
        if attempt > max_retries:
            return status, result, attempt
        sleep_fn(min(2 ** attempt, 8))
