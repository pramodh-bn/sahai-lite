"""Stage 4 Requirement 4: Submission Deliverables & Rubric Self-Check.

Covers:
1. Root README.md with required substantive sections
2. Demo script bounded to <= 180 seconds (3 minutes)
3. Hackathon writeup strictly bounded to 100-500 words
4. Real/Mock matrix documenting mock vs live across all 4 stages
5. Judging rubric self-check addressing Innovation, Technical Execution, UX, Embodied Experience, Safety/Ethics
6. Clean checkout cumulative files verification
"""
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
        self.assertTrue(README_PATH.is_file(), f"Missing README.md at repo root: {README_PATH}")
        content = README_PATH.read_text(encoding="utf-8").lower()
        for kw in ["overview", "quickstart", "architecture", "safety"]:
            self.assertIn(kw, content, f"README.md missing required section/keyword: '{kw}'")

    def test_demo_script_bounded_to_three_minutes(self):
        """Demo script must exist and specify execution budget <= 180 seconds (3 minutes)."""
        path, text = find_first_existing_file(DEMO_SCRIPT_PATHS, required_heading="demo")
        self.assertIsNotNone(path, "Missing demo script deliverable (checked docs/demo-script.md, README.md, DEMO_SCRIPT.md)")
        low = text.lower()
        has_time_bound = any(t in low for t in ["180", "3 min", "3-minute", "three minute", "180s", "180 seconds"])
        self.assertTrue(has_time_bound, "Demo script must explicitly declare total duration budget <= 180s (3 minutes)")

    def test_hackathon_writeup_bounded_to_500_words(self):
        """Hackathon writeup must exist and be strictly bounded to <= 500 words and >= 100 words."""
        path, text = find_first_existing_file(WRITEUP_PATHS, required_heading="writeup")
        self.assertIsNotNone(path, "Missing writeup deliverable (checked docs/writeup.md, README.md, WRITEUP.md)")
        wc = count_words_in_markdown(text)
        self.assertGreaterEqual(wc, 100, f"Writeup must be at least 100 words, found {wc}")
        self.assertLessEqual(wc, 500, f"Writeup must not exceed 500 words, found {wc}")

    def test_real_mock_matrix_documents_all_stages(self):
        """Real/Mock matrix must document mock vs live behavior across all 4 stages."""
        path, text = find_first_existing_file(REAL_MOCK_MATRIX_PATHS, required_heading="matrix")
        self.assertIsNotNone(path, "Missing Real/Mock matrix document (checked docs/real-mock-matrix.md, README.md)")
        low = text.lower()
        for stage in ["stage 1", "stage 2", "stage 3", "stage 4"]:
            self.assertIn(stage, low, f"Real/Mock matrix missing documentation for {stage}")

    def test_judging_rubric_selfcheck_covers_all_five_criteria(self):
        """Judging rubric self-check must address all five hackathon evaluation criteria."""
        path, text = find_first_existing_file(RUBRIC_SELFCHECK_PATHS, required_heading="rubric")
        self.assertIsNotNone(path, "Missing judging rubric self-check document (checked docs/judging-rubric.md, README.md)")
        low = text.lower()
        for criterion in [
            "innovation",
            "technical",
            "user experience",
            "embodied",
            "safety",
        ]:
            self.assertIn(criterion, low, f"Judging rubric missing evaluation criterion: '{criterion}'")

    def test_clean_checkout_cumulative_files_verification(self):
        """Verifies cumulative test suite files are all present in repo tree."""
        s1_tests = TESTS_DIR / "test_req1_bootstrap.py"
        s2_tests = TESTS_DIR / "test_s2_req1_transitions.py"
        s3_tests = TESTS_DIR / "test_s3_req1_webrtc_readiness.py"
        for st in [s1_tests, s2_tests, s3_tests]:
            self.assertTrue(st.is_file(), f"Missing required cumulative test file: {st.name}")


if __name__ == "__main__":
    unittest.main()
