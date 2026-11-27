"""Stage 4C requirement 4: packaging artifacts.

Semantic minima for the submission packaging: a substantive README, a demo
script capped at three minutes, a real/mock matrix, a judging-rubric
self-check and a 100-500 word write-up. Wording is free; only the required
topics and structure are asserted.

Contract: ``factory-lite/docs/stage-4c-acceptance-contract.md`` section 8.
"""
import re
import unittest

from s4c_helpers import markdown_table_rows, read_repo_text, word_count

REQUIRED_README_TERMS = (
    "body double",
    "consent",
    "synthetic",
    "real",
    "mock",
    "offline",
    "evidence",
)

REQUIRED_DEMO_TOPICS = (
    "scenario",
    "demonstrat",
    "practice",
    "feedback",
    "retry",
    "delet",
)

REQUIRED_MATRIX_TOPICS = (
    "persona",
    "turn",
    "consent",
    "vendor",
    "delet",
    "ui",
    "evidence",
    "fidelity",
)

REQUIRED_RUBRIC_TOPICS = (
    "fidelity",
    "disclosure",
    "authority",
    "safety",
    "hidden need",
    "evidence",
    "responsive",
    "privacy",
)


def _duration_seconds(text):
    """Smallest duration stated in the demo script, in seconds, or None."""
    values = []
    for match in re.finditer(r"(\d+)\s*(seconds?|secs?|s)\b", text, re.I):
        values.append(int(match.group(1)))
    for match in re.finditer(r"(\d+)\s*(minutes?|mins?|m)\b", text, re.I):
        values.append(int(match.group(1)) * 60)
    return min(values) if values else None


class TestPackagingArtifacts(unittest.TestCase):
    def test_readme_is_substantive_and_covers_product_and_run(self):
        text = read_repo_text("README.md")
        self.assertIsNotNone(text, "README.md is missing")
        self.assertGreaterEqual(len(text), 1500, f"README.md is too thin ({len(text)} chars)")
        self.assertRegex(text, r"(?m)^#{1,3}\s*Run\b",
                         "README.md has no '## Run' section")
        lowered = text.lower()
        missing = [term for term in REQUIRED_README_TERMS if term not in lowered]
        self.assertEqual(missing, [], f"README.md does not mention: {missing}")
        self.assertTrue("privacy" in lowered or "retention" in lowered,
                        "README.md does not describe privacy or retention")

    def test_demo_script_is_numbered_and_under_three_minutes(self):
        text = read_repo_text("docs/DEMO.md")
        self.assertIsNotNone(text, "docs/DEMO.md is missing")
        steps = [line for line in text.splitlines() if re.match(r"^\s*\d+[.)]\s+\S", line)]
        self.assertGreaterEqual(len(steps), 6,
                                f"demo script has only {len(steps)} numbered steps")
        lowered = text.lower()
        missing = [topic for topic in REQUIRED_DEMO_TOPICS if topic not in lowered]
        self.assertEqual(missing, [], f"demo script does not cover: {missing}")
        seconds = _duration_seconds(text)
        self.assertIsNotNone(seconds, "demo script states no duration")
        self.assertLessEqual(seconds, 180, f"demo script runs {seconds}s, over the 3-minute cap")

    def test_real_mock_matrix_is_a_table_with_required_coverage(self):
        text = read_repo_text("docs/REAL_MOCK_MATRIX.md")
        self.assertIsNotNone(text, "docs/REAL_MOCK_MATRIX.md is missing")
        rows = markdown_table_rows(text)
        self.assertGreaterEqual(len(rows), 9,
                                f"real/mock matrix has only {len(rows)} table lines")
        header = rows[0].lower()
        for column in ("feature", "real", "mock"):
            self.assertIn(column, header, f"matrix header lacks a {column!r} column: {rows[0]}")
        lowered = text.lower()
        missing = [topic for topic in REQUIRED_MATRIX_TOPICS if topic not in lowered]
        self.assertEqual(missing, [], f"real/mock matrix does not cover: {missing}")

    def test_rubric_selfcheck_scores_every_required_dimension(self):
        text = read_repo_text("docs/RUBRIC_SELFCHECK.md")
        self.assertIsNotNone(text, "docs/RUBRIC_SELFCHECK.md is missing")
        rows = markdown_table_rows(text)
        self.assertGreaterEqual(len(rows), 9,
                                f"rubric self-check has only {len(rows)} table lines")
        lowered = text.lower()
        missing = [topic for topic in REQUIRED_RUBRIC_TOPICS if topic not in lowered]
        self.assertEqual(missing, [], f"rubric self-check does not score: {missing}")

    def test_writeup_is_100_to_500_words(self):
        text = read_repo_text("docs/WRITEUP.md")
        self.assertIsNotNone(text, "docs/WRITEUP.md is missing")
        count = word_count(text)
        self.assertGreaterEqual(count, 100, f"write-up is {count} words, under 100")
        self.assertLessEqual(count, 500, f"write-up is {count} words, over 500")


if __name__ == "__main__":
    unittest.main()
