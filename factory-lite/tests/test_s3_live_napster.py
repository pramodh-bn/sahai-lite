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
silent no-op.

This test is immutable: it invokes the exact same frozen
app/napster_adapter.py CLI the offline req3/req4 tests exercise against a
fake vendor (CONTRACT.md "Stage 3 adapter CLI"), only with
NAPSTER_BASE_URL pointed at the real vendor instead of a local fixture.
Builder makes this test pass by implementing app/napster_adapter.py
correctly -- no edit to this file is ever required or permitted for that.

No credential value, and no rehearsal transcript content, is ever printed
or logged by this module, gate open or closed. Real evidence is validated
with the same strengthened schema (s3_live_gate.validate_evidence_record)
used offline -- a real run that produces a weak/incomplete evidence
record fails this test, it does not pass.

The Verifier authoring this file has NEVER run it with the gate enabled.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

try:
    from s3_adapter_client import run_adapter
    from s3_live_gate import CAPABILITIES, live_gate_status, validate_evidence_record
except ImportError:
    from .s3_adapter_client import run_adapter
    from .s3_live_gate import CAPABILITIES, live_gate_status, validate_evidence_record

# Documented, official Napster API base; only ever used when the owner has
# explicitly enabled the live gate. Override with NAPSTER_LIVE_BASE_URL if
# the owner's account requires a different documented base.
DEFAULT_LIVE_BASE_URL = "https://api.napster.com"


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
        cls._tmp = tempfile.TemporaryDirectory(prefix="s3-live-probe-")
        cls._state_dir = Path(cls._tmp.name) / "state"
        cls._evidence_dir = Path(cls._tmp.name) / "evidence"
        cls._state_dir.mkdir(parents=True)
        cls._evidence_dir.mkdir(parents=True)
        cls._base_url = os.environ.get("NAPSTER_LIVE_BASE_URL", DEFAULT_LIVE_BASE_URL)
        cls._api_key = os.environ["NAPSTER_API_KEY"]

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_tmp"):
            cls._tmp.cleanup()

    def test_companion_avatar_probe(self):
        self._run_and_validate("companion_avatar")

    def test_audio_probe(self):
        self._run_and_validate("audio")

    def test_handoff_probe(self):
        self._run_and_validate("handoff")

    def _run_and_validate(self, capability):
        code, parsed, out, err = run_adapter(
            capability, self._base_url, self._state_dir, self._evidence_dir, api_key=self._api_key,
        )
        self.assertNotIn(self._api_key, out, "adapter stdout must never contain the raw credential")
        self.assertNotIn(self._api_key, err, "adapter stderr must never contain the raw credential")
        self.assertEqual(code, 0, f"live adapter run for {capability!r} did not report success: stdout={out!r} stderr={err!r}")
        self.assertIsNotNone(parsed, "adapter must print one JSON line")
        evidence_path = parsed.get("evidence_path")
        self.assertTrue(evidence_path, "adapter must report its evidence file path")
        record = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
        is_valid, problems = validate_evidence_record(record, credential_value=self._api_key)
        self.assertTrue(is_valid, f"real evidence record failed schema validation: {problems}")
        self.assertEqual(record.get("capability"), capability)
        self.assertEqual(record.get("outcome"), "success")

    def test_all_three_capabilities_are_covered(self):
        self.assertEqual(set(CAPABILITIES), {"companion_avatar", "audio", "handoff"})


if __name__ == "__main__":
    unittest.main()
