"""Req 8 (stage-1.md): "Record Napster documented capabilities and unknowns;
no paid calls."

Contract convention: factory-lite/docs/napster-feasibility.md documents
current capabilities, unknowns, and evidence sources. It must contain no
markers of live/paid API calls, and no Napster credential files may be
tracked in the repo.
"""
import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "factory-lite" / "docs" / "napster-feasibility.md"
REQUIRED_HEADINGS = ("Capabilities", "Unknowns", "Evidence")
LIVE_CALL_MARKERS = (
    "requests.post",
    "requests.get",
    "fetch(",
    "curl ",
    "api.napster.com",
    "authorization: bearer",
    "client_secret",
)


class TestNapsterFeasibilityDocOnly(unittest.TestCase):
    def test_feasibility_doc_exists(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")

    def test_feasibility_doc_has_required_sections(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")
        missing = [h for h in REQUIRED_HEADINGS if not re.search(rf"##\s*{h}", text, re.I)]
        self.assertEqual(missing, [], f"{DOC} missing required section(s): {missing}")

    def test_feasibility_doc_contains_no_live_call_markers(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8").lower()
        hits = [m for m in LIVE_CALL_MARKERS if m in text]
        self.assertEqual(hits, [], f"{DOC} appears to reference live/executable calls: {hits}")

    def test_no_napster_credential_files_tracked(self):
        out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        tracked = out.stdout.splitlines()
        suspects = [f for f in tracked if "napster" in f.lower() and f.lower().endswith((".env", ".key", ".pem"))]
        self.assertEqual(suspects, [], f"suspicious Napster credential file(s) tracked: {suspects}")


if __name__ == "__main__":
    unittest.main()
