"""Stage 4 Requirement 4: Submission Deliverables, Rubric Self-Check, Real/Mock Matrix, and Clean Checkout.

Mandates:
- Root README.md with overview, architecture, setup/run, safety/consent.
- Demo script bounded to <= 180 seconds (3 minutes).
- Writeup bounded to <= 500 words.
- Documented Real/Mock matrix across all 4 stages.
- Judging rubric self-check covering all 5 criteria.
- Clean checkout cumulative test run validation.
"""
import os
import re
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent

if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s4_helpers import (
    README_PATH,
    DEMO_SCRIPT_PATHS,
    WRITEUP_PATHS,
    REAL_MOCK_MATRIX_PATHS,
    RUBRIC_SELFCHECK_PATHS,
    find_first_existing_file,
    count_words_in_markdown,
)


class TestStage4SubmissionAndRubric(unittest.TestCase):
    def test_readme_exists_with_required_sections(self):
        """README.md must exist at repository root and include required substantive sections."""
        self.assertTrue(README_PATH.is_file(), f"Missing required README.md at repo root: {README_PATH}")
        content = README_PATH.read_text(encoding="utf-8").lower()

        required_keywords = [
            "overview",
            "architecture",
            "run",
            "safety",
        ]
        for kw in required_keywords:
            self.assertIn(kw, content, f"README.md missing required section/keyword: '{kw}'")

    def test_demo_script_bounded_to_three_minutes(self):
        """Demo script must exist and specify execution budget <= 180 seconds (3 minutes)."""
        path, text = find_first_existing_file(DEMO_SCRIPT_PATHS, required_heading="demo")
        self.assertIsNotNone(path, "Missing demo script deliverable (checked docs/demo-script.md, README.md, DEMO_SCRIPT.md)")

        content = text.lower()
        has_time_bound = any(
            t in content for t in ["180 seconds", "180s", "3 minutes", "3 min", "under 3 minutes", "<= 180"]
        )
        self.assertTrue(
            has_time_bound,
            f"Demo script in {path.name} must specify explicit duration bound <= 180 seconds (3 minutes)",
        )

    def test_hackathon_writeup_bounded_to_500_words(self):
        """Hackathon writeup must exist and be strictly bounded to <= 500 words and >= 100 words."""
        path, text = find_first_existing_file(WRITEUP_PATHS, required_heading="writeup")
        self.assertIsNotNone(path, "Missing writeup deliverable (checked docs/writeup.md, README.md, WRITEUP.md)")

        word_count = count_words_in_markdown(text)
        self.assertGreaterEqual(word_count, 100, f"Writeup in {path.name} too short ({word_count} words); requires >= 100 words")
        self.assertLessEqual(word_count, 500, f"Writeup in {path.name} exceeds 500-word limit ({word_count} words)")

    def test_real_mock_matrix_documents_all_stages(self):
        """Real/Mock matrix must document mock vs live behavior across all 4 stages."""
        path, text = find_first_existing_file(REAL_MOCK_MATRIX_PATHS, required_heading="matrix")
        self.assertIsNotNone(path, "Missing Real/Mock matrix document (checked docs/real-mock-matrix.md, README.md)")

        content = text.lower()
        for stage in ["stage 1", "stage 2", "stage 3", "stage 4"]:
            self.assertIn(stage, content, f"Real/Mock matrix missing documentation for '{stage}'")
        self.assertIn("mock", content)
        self.assertIn("live", content)

    def test_judging_rubric_selfcheck_covers_all_five_criteria(self):
        """Judging rubric self-check must address all five hackathon evaluation criteria."""
        path, text = find_first_existing_file(RUBRIC_SELFCHECK_PATHS, required_heading="rubric")
        self.assertIsNotNone(path, "Missing judging rubric self-check document (checked docs/judging-rubric.md, README.md)")

        content = text.lower()
        criteria = [
            "innovation",
            "technical",
            "user experience",
            "embodied",
            "safety",
        ]
        for c in criteria:
            self.assertIn(c, content, f"Judging rubric self-check missing criterion: '{c}'")

    def test_clean_checkout_prior_stages_cumulative_integrity(self):
        """Prior stages 1-3 test suite files must all be present."""
        expected_files = [
            "test_req1_startup_command.py",
            "test_req2_health_version.py",
            "test_req3_container_nonroot.py",
            "test_req4_dependency_lock.py",
            "test_req5_no_secrets.py",
            "test_req6_harness_contract.py",
            "test_req7_clean_checkout_startup.py",
            "test_req8_napster_feasibility.py",
            "test_s2_req1_transitions.py",
            "test_s2_req2_counterpart_hidden_need.py",
            "test_s2_req3_evidence_scoring.py",
            "test_s2_req4_retry_pivot.py",
            "test_s2_req5_isolation_replay.py",
            "test_s2_req6_offline_mode.py",
            "test_s2_req7_ui_journey.py",
            "test_s3_contract_selfcheck.py",
            "test_s3_req2_server_adapter.py",
            "test_s3_req4_ui_journey.py",
            "test_s3_req6_app_local_handoff.py",
            "test_s3_req7_live_gate.py",
            "test_s3_req8_evidence_schema.py",
            "test_s3_req10_sdk_provenance_and_demo.py",
        ]
        for filename in expected_files:
            fpath = TESTS_DIR / filename
            self.assertTrue(fpath.is_file(), f"Missing prior stage test file: {filename}")


if __name__ == "__main__":
    unittest.main()
