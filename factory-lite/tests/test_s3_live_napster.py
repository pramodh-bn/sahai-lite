"""Stage 3 AUTHORIZED LIVE-ONLY PROBE for Napster companion/avatar, audio,
and handoff capability (factory-lite/spec/stage-3.md).

Run in isolation, as its own command, never as a substitute for the
cumulative offline suite:

    py -3.12 -m unittest factory-lite.tests.test_s3_live_napster -v

GATE: this module makes ZERO vendor calls unless BOTH
`SAH_NAPSTER_LIVE=1` AND every credential env var named in
`s3_live_gate.REQUIRED_CREDENTIAL_ENV_VARS` (currently just
`NAPSTER_API_KEY`) are set. Without the gate, every test here is skipped
with an explicit, non-certifying message -- never a false pass, never a
silent no-op. Passing the cumulative `discover` run (which also collects
this file, since it matches `test_*.py`) never certifies anything live;
see factory-lite/docs/stage3-certification-status.md.

No credential value, and no rehearsal transcript content, is ever printed
or logged by this module, gate open or closed.

The Verifier authoring this file has NEVER run it with the gate enabled.
"""
import json
import time
import unittest
from pathlib import Path

try:
    from s3_live_gate import REDACTED_EVIDENCE_SCHEMA_FIELDS, live_gate_status, redact
except ImportError:
    from .s3_live_gate import REDACTED_EVIDENCE_SCHEMA_FIELDS, live_gate_status, redact

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "factory-lite" / "tests" / "evidence" / "live"
CAPABILITIES = ("companion_avatar", "audio", "handoff")


def write_redacted_evidence(probe_id, capability, outcome, http_status, evidence_text):
    """Write one redacted evidence record for a real probe run. Any
    sensitive-looking field is masked by redact() regardless of content."""
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    record = redact({
        "probe_id": probe_id,
        "capability": capability,
        "started_at": None,
        "ended_at": None,
        "outcome": outcome,
        "http_status": http_status,
        "redacted": True,
        "evidence_text": evidence_text,
    })
    missing = [f for f in REDACTED_EVIDENCE_SCHEMA_FIELDS if f not in record]
    assert not missing, f"evidence record missing required field(s): {missing}"
    path = EVIDENCE_DIR / f"{probe_id}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return path


class TestAuthorizedLiveNapsterProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        is_open, reason = live_gate_status()
        if not is_open:
            raise unittest.SkipTest(
                f"Stage 3 live probe BLOCKED, not authorized: {reason}. "
                "This skip is intentional and non-certifying -- it is not a pass, "
                "and the cumulative offline suite passing does not change that."
            )
        cls._probe_started_at = time.time()

    def test_companion_avatar_probe(self):
        self._run_capability_probe("companion_avatar")

    def test_audio_probe(self):
        self._run_capability_probe("audio")

    def test_handoff_probe(self):
        self._run_capability_probe("handoff")

    def _run_capability_probe(self, capability):
        # Reached only when the owner has explicitly enabled the gate.
        # Intentionally left as a loud failure, not a fabricated pass:
        # no credentials have ever been exercised against this body, so
        # it must not claim real embodied evidence it never produced.
        # A real implementation here must: use
        # s3_live_gate.SessionRegistry to guarantee at most one session
        # per capability and cleanup on success/error, use
        # s3_live_gate.call_with_bounded_retry for 409/429, capture real
        # redacted evidence via write_redacted_evidence(), and never
        # print a credential or raw rehearsal transcript.
        self.fail(
            f"live probe body for {capability!r} is not implemented against the real "
            f"Napster API; refusing to report a pass without real, redacted evidence"
        )


if __name__ == "__main__":
    unittest.main()
