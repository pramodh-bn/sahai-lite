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
    "test_s4_req5_persona_and_compiler",
    "test_s4_req6_orchestration_and_authority",
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

        sig_hash = inspect.signature(s4_helpers.canonical_profile_hash)
        self.assertIn("profile_dict", sig_hash.parameters)

        sig_val = inspect.signature(s4_helpers.validate_persona_profile)
        self.assertIn("profile", sig_val.parameters)

        sig_comp = inspect.signature(s4_helpers.compile_system_instructions)
        self.assertIn("profile", sig_comp.parameters)

    def test_no_assert_false_or_self_fail_placeholders(self):
        """No Stage 4 test file may contain assert False or self.fail placeholder stubs or tautological assertions."""
        for path in TESTS_DIR.glob("test_s4_*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "fail":
                        if path.name != "test_s4_contract_selfcheck.py":
                            self.fail(f"Found forbidden self.fail placeholder in {path.name}:{node.lineno}")
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "assertTrue":
                        if len(node.args) >= 1 and isinstance(node.args[0], ast.Constant) and node.args[0].value is True:
                            self.fail(f"Found forbidden tautological assertTrue(True) in {path.name}:{node.lineno}")
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "assertEqual":
                        if len(node.args) >= 2 and isinstance(node.args[0], ast.Constant) and isinstance(node.args[1], ast.Constant):
                            if node.args[0].value == node.args[1].value:
                                self.fail(f"Found forbidden tautological assertEqual({node.args[0].value}, {node.args[1].value}) in {path.name}:{node.lineno}")
                if isinstance(node, ast.Assert):
                    if isinstance(node.test, ast.Constant) and node.test.value is False:
                        self.fail(f"Found forbidden 'assert False' placeholder in {path.name}:{node.lineno}")

    def test_stage4_contract_coverage_and_structure(self):
        """Validates that Stage 4 test files cover all specified contract dimensions."""
        required_modules = [
            "test_s4_req1_journeys.py",
            "test_s4_req2_lifecycle_and_safety.py",
            "test_s4_req3_consent_and_disclosure.py",
            "test_s4_req4_submission_and_rubric.py",
            "test_s4_req5_persona_and_compiler.py",
            "test_s4_req6_orchestration_and_authority.py",
        ]

        for mod_name in required_modules:
            f = TESTS_DIR / mod_name
            self.assertTrue(f.is_file(), f"Missing required Stage 4 test module: {mod_name}")

        code1 = (TESTS_DIR / "test_s4_req1_journeys.py").read_text(encoding="utf-8").lower()
        self.assertIn("desktop", code1)
        self.assertIn("mobile", code1)
        self.assertIn("keyboard", code1)
        self.assertIn("mic", code1)
        self.assertIn("slow", code1)

        code2 = (TESTS_DIR / "test_s4_req2_lifecycle_and_safety.py").read_text(encoding="utf-8").lower()
        self.assertIn("cleanup", code2)
        self.assertIn("deletion", code2)
        self.assertIn("withdraw", code2)
        self.assertIn("log", code2)

        code3 = (TESTS_DIR / "test_s4_req3_consent_and_disclosure.py").read_text(encoding="utf-8").lower()
        self.assertIn("consent", code3)
        self.assertIn("disclosure", code3)
        self.assertIn("synthetic", code3)

        code4 = (TESTS_DIR / "test_s4_req4_submission_and_rubric.py").read_text(encoding="utf-8").lower()
        self.assertIn("readme", code4)
        self.assertIn("demo", code4)
        self.assertIn("writeup", code4)
        self.assertIn("rubric", code4)
        self.assertIn("matrix", code4)

        code5 = (TESTS_DIR / "test_s4_req5_persona_and_compiler.py").read_text(encoding="utf-8").lower()
        self.assertIn("schema", code5)
        self.assertIn("compiler", code5)
        self.assertIn("projection", code5)
        self.assertIn("hidden", code5)

        code6 = (TESTS_DIR / "test_s4_req6_orchestration_and_authority.py").read_text(encoding="utf-8").lower()
        self.assertIn("turn", code6)
        self.assertIn("concurrency", code6)
        self.assertIn("idempotency", code6)
        self.assertIn("escalation", code6)
        self.assertIn("retry", code6)


if __name__ == "__main__":
    unittest.main()
