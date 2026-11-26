"""Stage 4 Meta-Contract Self-Check.

Maintains exactly 4 tests with truthful names and zero placeholder assertions:
1. test_stage4_modules_import_cleanly
2. test_helper_signatures_accept_all_callsite_keywords
3. test_no_assert_false_or_self_fail_placeholders
4. test_stage4_contract_coverage_and_structure
"""
import ast
import importlib
import inspect
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


STAGE4_MODULE_NAMES = [
    "s4_helpers",
    "test_s4_contract_selfcheck",
    "test_s4_req1_journeys",
    "test_s4_req2_lifecycle_and_safety",
    "test_s4_req3_consent_and_disclosure",
    "test_s4_req4_submission_and_rubric",
]


class TestStage4ContractSelfCheck(unittest.TestCase):
    def test_stage4_modules_import_cleanly(self):
        """All Stage 4 test and helper modules must import cleanly without side effects."""
        for mod_name in STAGE4_MODULE_NAMES:
            with self.subTest(module=mod_name):
                try:
                    mod = importlib.import_module(f"factory-lite.tests.{mod_name}")
                    self.assertIsNotNone(mod)
                except Exception as exc:
                    self.fail(f"Stage 4 module {mod_name} failed to import: {exc}")

    def test_helper_signatures_accept_all_callsite_keywords(self):
        """s4_helpers functions must have stable signatures for callers."""
        import s4_helpers

        sig_desk = inspect.signature(s4_helpers.create_desktop_context)
        self.assertIn("browser", sig_desk.parameters)

        sig_mob = inspect.signature(s4_helpers.create_mobile_context)
        self.assertIn("browser", sig_mob.parameters)

        sig_net = inspect.signature(s4_helpers.attach_slow_network)
        self.assertIn("context", sig_net.parameters)
        self.assertIn("delay_ms", sig_net.parameters)

        sig_wc = inspect.signature(s4_helpers.count_words_in_markdown)
        self.assertIn("text", sig_wc.parameters)

    def test_no_assert_false_or_self_fail_placeholders(self):
        """No Stage 4 test file may contain assert False or self.fail placeholder stubs."""
        for path in TESTS_DIR.glob("test_s4_*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "fail":
                        if path.name != "test_s4_contract_selfcheck.py":
                            self.fail(f"Found forbidden self.fail placeholder in {path.name}:{node.lineno}")
                if isinstance(node, ast.Assert):
                    if isinstance(node.test, ast.Constant) and node.test.value is False:
                        self.fail(f"Found forbidden 'assert False' placeholder in {path.name}:{node.lineno}")

    def test_stage4_contract_coverage_and_structure(self):
        """Validates that Stage 4 test files cover all specified contract dimensions."""
        req1_file = TESTS_DIR / "test_s4_req1_journeys.py"
        req2_file = TESTS_DIR / "test_s4_req2_lifecycle_and_safety.py"
        req3_file = TESTS_DIR / "test_s4_req3_consent_and_disclosure.py"
        req4_file = TESTS_DIR / "test_s4_req4_submission_and_rubric.py"

        for f in [req1_file, req2_file, req3_file, req4_file]:
            self.assertTrue(f.is_file(), f"Missing required Stage 4 test module: {f.name}")

        code1 = req1_file.read_text(encoding="utf-8")
        self.assertIn("desktop", code1.lower())
        self.assertIn("mobile", code1.lower())
        self.assertIn("keyboard", code1.lower())
        self.assertIn("mic", code1.lower())
        self.assertIn("slow", code1.lower())

        code2 = req2_file.read_text(encoding="utf-8")
        self.assertIn("cleanup", code2.lower())
        self.assertIn("deletion", code2.lower())
        self.assertIn("log", code2.lower())

        code3 = req3_file.read_text(encoding="utf-8")
        self.assertIn("consent", code3.lower())
        self.assertIn("disclosure", code3.lower())
        self.assertIn("synthetic", code3.lower())

        code4 = req4_file.read_text(encoding="utf-8")
        self.assertIn("readme", code4.lower())
        self.assertIn("demo", code4.lower())
        self.assertIn("writeup", code4.lower())
        self.assertIn("rubric", code4.lower())
        self.assertIn("matrix", code4.lower())


if __name__ == "__main__":
    unittest.main()
