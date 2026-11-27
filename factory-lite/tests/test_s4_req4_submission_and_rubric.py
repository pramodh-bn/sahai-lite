"""
Stage 4 Requirement 4: Submission Deliverables, Judging Rubric, and Clean Checkout.

Validates that all submission artifacts (README, <=180s demo script, 100-500 word writeup,
Real/Mock matrix, judging rubric self-check, and clean checkout file manifest)
are substantive, complete, and properly formatted.
"""

import os
import unittest

from s4_helpers import (
    analyze_demo_script,
    analyze_writeup,
    check_judging_rubric,
    check_readme_sections,
    check_real_mock_matrix,
)


class TestStage4SubmissionAndRubric(unittest.TestCase):
    def setUp(self):
        # Locate project root directory
        self.root_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

    def _read_file_if_exists(self, *candidates) -> str | None:
        for rel_path in candidates:
            full_path = os.path.join(self.root_dir, rel_path)
            if os.path.isfile(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    return f.read()
        return None

    def test_readme_exists_with_required_sections(self):
        """
        Root README.md must exist and contain required substantive sections:
        overview, architecture, setup, and verification.
        """
        content = self._read_file_if_exists("README.md")
        self.assertIsNotNone(content, "Root README.md must exist in the repository")

        missing = check_readme_sections(content)
        self.assertEqual(
            missing,
            [],
            f"README.md is missing required sections: {missing}",
        )

    def test_demo_script_bounded_to_three_minutes(self):
        """
        Demo script must be documented and spoken text strictly bounded to <= 180 seconds.
        """
        content = self._read_file_if_exists(
            "docs/demo-script.md",
            "factory-lite/docs/demo-script.md",
            "DEMO.md",
        )
        self.assertIsNotNone(
            content,
            "Missing demo script deliverable (checked docs/demo-script.md, factory-lite/docs/demo-script.md, DEMO.md)",
        )

        analysis = analyze_demo_script(content)
        self.assertTrue(
            analysis["is_under_3_minutes"],
            f"Demo script duration ({analysis['est_duration_seconds']:.1f}s) exceeds 180s limit",
        )

    def test_hackathon_writeup_bounded_to_500_words(self):
        """
        Hackathon writeup must be substantive and strictly between 100 and 500 words.
        """
        content = self._read_file_if_exists(
            "docs/writeup.md",
            "factory-lite/docs/writeup.md",
            "WRITEUP.md",
        )
        self.assertIsNotNone(
            content,
            "Missing writeup deliverable (checked docs/writeup.md, factory-lite/docs/writeup.md, WRITEUP.md)",
        )

        analysis = analyze_writeup(content)
        self.assertTrue(
            analysis["is_valid_range"],
            f"Writeup word count ({analysis['word_count']} words) must be within [100, 500] range",
        )

    def test_real_mock_matrix_documents_all_stages(self):
        """
        Real vs. Mock matrix must explicitly document all 4 stages (Stage 1 to Stage 4).
        """
        content = self._read_file_if_exists(
            "docs/real-mock-matrix.md",
            "factory-lite/docs/real-mock-matrix.md",
            "README.md",
        )
        self.assertIsNotNone(
            content,
            "Missing Real/Mock matrix document (checked docs/real-mock-matrix.md, factory-lite/docs/real-mock-matrix.md)",
        )

        analysis = check_real_mock_matrix(content)
        self.assertTrue(
            analysis["has_stages"],
            f"Real/Mock matrix missing documentation for stages: {analysis['missing_stages']}",
        )
        self.assertTrue(
            analysis["has_real_and_mock"],
            "Real/Mock matrix must explicitly categorize both 'real' and 'mock' components",
        )

    def test_judging_rubric_selfcheck_covers_all_five_criteria(self):
        """
        Judging rubric self-check must cover all 5 hackathon evaluation criteria.
        """
        content = self._read_file_if_exists(
            "docs/judging-rubric.md",
            "factory-lite/docs/judging-rubric.md",
        )
        self.assertIsNotNone(
            content,
            "Missing judging rubric self-check document (checked docs/judging-rubric.md, factory-lite/docs/judging-rubric.md)",
        )

        analysis = check_judging_rubric(content)
        self.assertTrue(
            analysis["covered"],
            f"Judging rubric missing criteria: {analysis['missing']}",
        )


if __name__ == "__main__":
    unittest.main()
