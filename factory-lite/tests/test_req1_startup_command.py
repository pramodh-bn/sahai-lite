"""Req 1 (stage-1.md): "One documented local startup command."

Contract convention (Verifier-defined; see factory-lite/tests/CONTRACT.md for
the full rationale, open for Lead review before Builder implementation):
  - app/RUN.md must exist.
  - It must contain exactly one fenced code block under a "## Run" heading.
  - That block must contain exactly one non-empty, non-comment command line.
"""
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DOC = REPO_ROOT / "app" / "RUN.md"


def extract_section_block(text, heading):
    m = re.search(rf"##\s*{heading}\b.*?```(?:\w+)?\n(.*?)```", text, re.S | re.I)
    return m.group(1) if m else None


class TestDocumentedStartupCommand(unittest.TestCase):
    def test_run_doc_exists(self):
        self.assertTrue(RUN_DOC.is_file(), f"missing documented startup command at {RUN_DOC}")

    def test_run_doc_has_exactly_one_command(self):
        self.assertTrue(RUN_DOC.is_file(), f"missing {RUN_DOC}; cannot verify a single startup command")
        block = extract_section_block(RUN_DOC.read_text(encoding="utf-8"), "Run")
        self.assertIsNotNone(block, f"no '## Run' fenced command block found in {RUN_DOC}")
        lines = [ln for ln in block.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        self.assertEqual(len(lines), 1, f"expected exactly one startup command, found {len(lines)}: {lines}")


if __name__ == "__main__":
    unittest.main()
