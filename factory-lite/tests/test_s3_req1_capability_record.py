"""Stage 3 (factory-lite/spec/stage-3.md): "Verify current vendor docs and
actual account capability before coding."

Contract convention: factory-lite/docs/stage3-capability-record.md must
exist, with substantive (non-placeholder) "## Capabilities", "## Unknowns",
and an account-capability section, each citing at least one
developers.napster.com / napster.com evidence URL, and must explicitly
state that no live calls, credentials, or cost were used to produce it.
This test never touches the network; it only inspects the record's text.
"""
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "factory-lite" / "docs" / "stage3-capability-record.md"
REQUIRED_HEADINGS = ("Capabilities", "Unknowns", "Account capability")
EVIDENCE_DOMAINS = ("developers.napster.com", "napster.com", "docs.napster.ai")
PLACEHOLDER_MARKERS = ("tbd", "todo", "fixme", "placeholder", "coming soon", "none yet")
# "n/a" is checked separately with word-boundary-aware lookaround below,
# since the plain substring also matches inside URL paths like
# ".../introduction/authentication" (the "n/authentication" segment).
PLACEHOLDER_REGEXES = (re.compile(r"(?<![a-zA-Z])n/a(?![a-zA-Z])"),)
MIN_SECTION_WORDS = 15


def section_text(text, heading):
    m = re.search(rf"^##\s*{re.escape(heading)}[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    return m.group(1).strip() if m else None


def substantive_issue(section_body):
    if not section_body:
        return "section is empty"
    low = section_body.lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker in low:
            return f"placeholder marker {marker!r} found"
    for pattern in PLACEHOLDER_REGEXES:
        if pattern.search(section_body):
            return f"placeholder marker {pattern.pattern!r} found"
    words = re.findall(r"\w+", section_body)
    if len(words) < MIN_SECTION_WORDS:
        return f"only {len(words)} word(s), need >= {MIN_SECTION_WORDS}"
    return None


class TestStage3CapabilityRecord(unittest.TestCase):
    def test_capability_record_exists(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}; required before any Stage 3 implementation")

    def test_required_sections_present_and_substantive(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")
        problems = {}
        for heading in REQUIRED_HEADINGS:
            body = section_text(text, heading)
            issue = substantive_issue(body)
            if issue:
                problems[heading] = issue
        self.assertEqual(problems, {}, f"{DOC} has non-substantive required section(s): {problems}")

    def test_cites_at_least_one_official_evidence_url(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")
        urls = re.findall(r"https?://\S+", text)
        official = [u for u in urls if any(d in u for d in EVIDENCE_DOMAINS)]
        self.assertTrue(official, f"{DOC} cites no developers.napster.com/napster.com evidence URL")

    def test_states_no_live_calls_credentials_or_cost_were_used(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8").lower()
        for phrase in ("no live api calls", "no credentials", "no cost"):
            self.assertIn(phrase, text, f"{DOC} must explicitly state {phrase!r}")

    def test_account_capability_marked_unverified_pending_live_check(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")
        body = section_text(text, "Account capability")
        self.assertIsNotNone(body, f"no account-capability section in {DOC}")
        self.assertIn("unverified", body.lower(), "account capability must be explicitly marked unverified pending a live check")


if __name__ == "__main__":
    unittest.main()
