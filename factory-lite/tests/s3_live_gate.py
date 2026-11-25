"""Shared, vendor-agnostic test tooling for Stage 3 (factory-lite/spec/
stage-3.md). Not a test module itself (doesn't match test_*.py).

Session-lifecycle, cleanup, and bounded-retry *behavior* is owned by
app/napster_adapter.py (see CONTRACT.md "Stage 3 adapter CLI") and is
black-box tested there via subprocess against factory-lite/tests/
s3_fake_vendor.py -- this module no longer simulates that behavior
itself. What remains here is pure, reusable, non-simulating logic:
  - the live-authorization gate check (live_gate_status)
  - a redaction helper (redact)
  - the redacted-evidence schema validator (validate_evidence_record),
    used identically by the offline adapter tests and by
    test_s3_live_napster.py on a real run
"""
import os
import re
from datetime import datetime

LIVE_GATE_ENV = "SAH_NAPSTER_LIVE"
REQUIRED_CREDENTIAL_ENV_VARS = ("NAPSTER_API_KEY",)

# Documented expectation the app-owned adapter (app/napster_adapter.py)
# must honor; enforced black-box in test_s3_req4_bounded_retry.py against
# s3_fake_vendor.py, not by this module.
MAX_RETRIES = 3
RETRYABLE_STATUSES = (409, 429)

CAPABILITIES = ("companion_avatar", "audio", "handoff")
VALID_OUTCOMES = ("success", "error")
MAX_EVIDENCE_TEXT_LEN = 300
FORBIDDEN_EVIDENCE_TEXT_MARKERS = (
    "x-api-key",
    "api_key",
    "apikey",
    "bearer ",
    "authorization:",
    "password",
    "secret",
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


def _parse_iso8601(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_evidence_record(record, credential_value=None):
    """Validate a redacted Stage 3 evidence record against the frozen
    schema. Returns (is_valid, problems). Never raises on malformed
    input -- a malformed record is simply invalid, with the reason
    listed in problems. `credential_value`, if given, is compared
    against evidence_text and rejected if it appears there, but the
    credential value itself is never included in any problem message."""
    problems = []
    if not isinstance(record, dict):
        return False, ["record is not a JSON object"]

    probe_id = record.get("probe_id")
    if not isinstance(probe_id, str) or not probe_id.strip():
        problems.append("probe_id must be a non-empty string")

    capability = record.get("capability")
    if capability not in CAPABILITIES:
        problems.append(f"capability must be one of {CAPABILITIES}, got {capability!r}")

    started_at = _parse_iso8601(record.get("started_at"))
    if started_at is None:
        problems.append("started_at must be a non-null ISO-8601 timestamp")
    ended_at = _parse_iso8601(record.get("ended_at"))
    if ended_at is None:
        problems.append("ended_at must be a non-null ISO-8601 timestamp")
    if started_at is not None and ended_at is not None and ended_at < started_at:
        problems.append("ended_at must not be before started_at")

    outcome = record.get("outcome")
    if outcome not in VALID_OUTCOMES:
        problems.append(f"outcome must be one of {VALID_OUTCOMES}, got {outcome!r}")

    http_status = record.get("http_status")
    transport_result = record.get("transport_result")
    has_status = isinstance(http_status, int) and not isinstance(http_status, bool)
    has_transport = isinstance(transport_result, str) and bool(transport_result.strip())
    if has_status and has_transport:
        problems.append("exactly one of http_status / transport_result must be set, not both")
    elif not has_status and not has_transport:
        problems.append("exactly one of http_status (int) or transport_result (non-empty str) must be a concrete value")

    if record.get("redacted") is not True:
        problems.append("redacted must be the literal boolean true")

    evidence_text = record.get("evidence_text")
    if not isinstance(evidence_text, str) or not evidence_text.strip():
        problems.append("evidence_text must be a non-empty string")
    else:
        if len(evidence_text) > MAX_EVIDENCE_TEXT_LEN:
            problems.append(f"evidence_text exceeds {MAX_EVIDENCE_TEXT_LEN} characters")
        if evidence_text.count("\n") > 2:
            problems.append("evidence_text looks like a multi-line transcript, not a short summary")
        low = evidence_text.lower()
        hits = [m for m in FORBIDDEN_EVIDENCE_TEXT_MARKERS if m in low]
        if hits:
            problems.append(f"evidence_text contains forbidden marker(s): {hits}")
        if credential_value and credential_value in evidence_text:
            problems.append("evidence_text contains the raw credential value")

    return (len(problems) == 0), problems
