"""Stage 3: "no invented voice cloning or relay control."

Static scan: no tracked file may claim, in its own voice, that this
project joins/controls a live third-party meeting, or clones a real
user's voice -- capabilities Napster's own documentation does not
describe for this integration (see
factory-lite/docs/stage3-capability-record.md "Unknowns": no meeting-join
or meeting-relay/control capability is documented at all). Quoting what
Napster's documentation says (e.g. "voice is cloned from the video's own
audio track", about a pre-recorded reference video, not a live user) is
not banned -- only first-person product claims are.
"""
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
THIS_FILE = Path(__file__).resolve()

BANNED_PHRASES = (
    "join your meeting",
    "joins your meeting",
    "joined your meeting",
    "join the meeting on your behalf",
    "joins the meeting on your behalf",
    "relay control of your meeting",
    "control your meeting",
    "controls your meeting",
    "controlling your meeting",
    "clone your voice",
    "clone the user's voice",
    "cloning your voice",
    "we can join",
    "sah joins",
    "sah can join",
    "sah will join",
)


def tracked_text_files():
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    for rel in out.stdout.splitlines():
        path = REPO_ROOT / rel
        if path.resolve() == THIS_FILE:
            continue
        if not path.is_file():
            continue
        try:
            yield rel, path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue


class TestNoFabricatedCapabilityClaims(unittest.TestCase):
    def test_no_tracked_file_claims_meeting_join_control_or_voice_cloning(self):
        findings = []
        for rel, text in tracked_text_files():
            low = text.lower()
            for phrase in BANNED_PHRASES:
                if phrase in low:
                    findings.append((rel, phrase))
        self.assertEqual(findings, [], f"forbidden capability claim(s) found: {findings}")


if __name__ == "__main__":
    unittest.main()
