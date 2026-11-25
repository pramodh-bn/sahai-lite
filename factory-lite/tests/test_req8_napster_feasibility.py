"""Req 8 (stage-1.md): "Record Napster documented capabilities and unknowns;
no paid calls."

Contract convention: factory-lite/docs/napster-feasibility.md documents
current capabilities, unknowns, and evidence sources with substantive,
non-placeholder content, cites at least one HTTP(S) evidence source, and
explicitly states that no live or paid calls were made. The ban on
executable live-call constructs (requests.*, fetch(, curl, bearer headers,
client secrets) does not extend to plainly citing a vendor/API domain as
evidence -- that is expected, documented-only evidence, not a live call.
"""
import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "factory-lite" / "docs" / "napster-feasibility.md"
REQUIRED_HEADINGS = ("Capabilities", "Unknowns", "Evidence")

# Executable/credential markers only -- NOT plain mentions of API/vendor
# domains, which are expected evidence citations, not live calls.
LIVE_CALL_MARKERS = (
    "requests.post",
    "requests.get",
    "fetch(",
    "curl ",
    "authorization: bearer",
    "client_secret",
)

PLACEHOLDER_MARKERS = (
    "tbd",
    "todo",
    "n/a",
    "fixme",
    "placeholder",
    "coming soon",
    "none yet",
    "lorem ipsum",
    "xxx",
)
MIN_SECTION_WORDS = 15


def section_text(text, heading):
    m = re.search(rf"^##\s*{heading}[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    return m.group(1).strip() if m else None


def substantive_issue(section_body):
    """Return a reason string if the section is not substantive, else None."""
    if not section_body:
        return "section is empty"
    low = section_body.lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker in low:
            return f"placeholder marker {marker!r} found"
    words = re.findall(r"\w+", section_body)
    if len(words) < MIN_SECTION_WORDS:
        return f"only {len(words)} word(s), need >= {MIN_SECTION_WORDS}"
    return None


def sentences(text):
    return re.split(r"(?<=[.!?])\s+", text)


def has_no_live_or_paid_statement(text):
    for sentence in sentences(text):
        low = sentence.lower()
        if "no" in low and "live" in low and "paid" in low and "call" in low:
            return True
    return False


class TestNapsterFeasibilityDocOnly(unittest.TestCase):
    def test_feasibility_doc_exists(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")

    def test_feasibility_doc_has_required_sections(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")
        missing = [h for h in REQUIRED_HEADINGS if not re.search(rf"##\s*{h}", text, re.I)]
        self.assertEqual(missing, [], f"{DOC} missing required section(s): {missing}")

    def test_required_sections_have_substantive_content(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")
        problems = {}
        for heading in REQUIRED_HEADINGS:
            issue = substantive_issue(section_text(text, heading))
            if issue:
                problems[heading] = issue
        self.assertEqual(problems, {}, f"{DOC} has non-substantive section(s): {problems}")

    def test_evidence_section_cites_http_source(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")
        evidence_body = section_text(text, "Evidence")
        self.assertIsNotNone(evidence_body, f"no '## Evidence...' section found in {DOC}")
        urls = re.findall(r"https?://\S+", evidence_body)
        self.assertTrue(urls, f"{DOC} Evidence section has no http(s) evidence citation")

    def test_doc_states_no_live_or_paid_calls_were_made(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")
        self.assertTrue(
            has_no_live_or_paid_statement(text),
            f"{DOC} must explicitly state that no live or paid calls were made",
        )

    def test_feasibility_doc_contains_no_executable_live_call_markers(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8").lower()
        hits = [m for m in LIVE_CALL_MARKERS if m in text]
        self.assertEqual(hits, [], f"{DOC} appears to contain an executable live-call construct: {hits}")

    def test_no_napster_credential_files_tracked(self):
        out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        tracked = out.stdout.splitlines()
        suspects = [f for f in tracked if "napster" in f.lower() and f.lower().endswith((".env", ".key", ".pem"))]
        self.assertEqual(suspects, [], f"suspicious Napster credential file(s) tracked: {suspects}")


if __name__ == "__main__":
    unittest.main()
