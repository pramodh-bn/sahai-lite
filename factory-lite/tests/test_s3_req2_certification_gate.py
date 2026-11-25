"""Stage 3: "mock tests separate and insufficient for stage certification";
"No certification for missing evidence" (PROTOCOL.md).

Contract convention: factory-lite/docs/stage3-certification-status.md
tracks four certification gates -- live authorization, credentials
present, account capability confirmed, redacted real evidence captured --
and must read "NOT CERTIFIED" until all four are met with evidence. This
test is itself an offline/static check: passing it (like any offline test
in this suite) never certifies Stage 3 by itself, which is exactly the
point it enforces.
"""
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "factory-lite" / "docs" / "stage3-certification-status.md"
REQUIRED_GATES = (
    "live authorization",
    "credentials present",
    "account capability",
    "redacted real evidence",
)


class TestCertificationGateHonest(unittest.TestCase):
    def test_certification_status_doc_exists(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")

    def test_status_reads_not_certified_while_any_gate_is_unmet(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")
        self.assertIn(
            "NOT CERTIFIED", text,
            f"{DOC} must explicitly read NOT CERTIFIED while any gate below is unmet",
        )

    def test_all_four_required_gates_are_tracked(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8").lower()
        missing = [g for g in REQUIRED_GATES if g not in text]
        self.assertEqual(missing, [], f"{DOC} does not track required gate(s): {missing}")

    def test_offline_suite_passing_is_explicitly_not_equated_with_certification(self):
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8").lower()
        self.assertTrue(
            re.search(r"mock|offline", text) and re.search(r"not\b.{0,40}certif", text),
            f"{DOC} must explicitly state that passing mock/offline tests does not certify Stage 3",
        )


if __name__ == "__main__":
    unittest.main()
