import ast
import inspect
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


class TestStage3ContractSelfCheck(unittest.TestCase):
    """Verifier-owned meta-contract proving contract integrity and signature safety."""

    def test_stage3_modules_import_cleanly(self):
        modules = [
            "s3_helpers",
            "test_s3_req2_server_adapter",
            "test_s3_req4_ui_journey",
            "test_s3_req6_app_local_handoff",
            "test_s3_req7_live_gate",
            "test_s3_req8_evidence_schema",
            "test_s3_req10_sdk_provenance_and_demo",
        ]
        for mod_name in modules:
            with self.subTest(module=mod_name):
                try:
                    mod = __import__(mod_name)
                    self.assertIsNotNone(mod)
                except Exception as exc:
                    self.fail(f"Module {mod_name} failed to import: {exc}")

    def test_helper_signatures_accept_all_callsite_keywords(self):
        import s3_helpers

        helper_funcs = {
            "post_napster_session": s3_helpers.post_napster_session,
            "delete_napster_session": s3_helpers.delete_napster_session,
            "validate_stage3_evidence": s3_helpers.validate_stage3_evidence,
            "is_stage3_certified": s3_helpers.is_stage3_certified,
        }

        # Explicit check: post_napster_session must accept simulate_error
        sig_post = inspect.signature(s3_helpers.post_napster_session)
        self.assertIn(
            "simulate_error",
            sig_post.parameters,
            "post_napster_session must explicitly accept simulate_error parameter",
        )

        # AST scan of all test_s3_*.py files to ensure no call passes an unaccepted keyword
        for path in TESTS_DIR.glob("test_s3_*.py"):
            if path.name == "test_s3_contract_selfcheck.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = None
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr

                    if func_name in helper_funcs:
                        fn = helper_funcs[func_name]
                        sig = inspect.signature(fn)
                        accepted_params = set(sig.parameters.keys())
                        has_var_keyword = any(
                            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
                        )
                        for kw in node.keywords:
                            if not has_var_keyword:
                                self.assertIn(
                                    kw.arg,
                                    accepted_params,
                                    f"File {path.name}:{node.lineno} passes unaccepted keyword '{kw.arg}' to {func_name}",
                                )

    def test_no_assert_false_or_self_fail_placeholders(self):
        for path in TESTS_DIR.glob("test_s3_*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                # Check for self.fail calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "fail":
                        # Allow self.fail only inside selfcheck test_stage3_modules_import_cleanly
                        if path.name != "test_s3_contract_selfcheck.py":
                            self.fail(f"Found forbidden self.fail placeholder in {path.name}:{node.lineno}")

                # Check for assert False
                if isinstance(node, ast.Assert):
                    if (
                        isinstance(node.test, ast.Constant)
                        and node.test.value is False
                    ):
                        self.fail(f"Found forbidden 'assert False' placeholder in {path.name}:{node.lineno}")

    def test_stable_live_module_exists_and_checks_gate_prerequisites(self):
        live_file = TESTS_DIR / "test_s3_req7_live_gate.py"
        self.assertTrue(live_file.is_file(), "Missing stable live module test_s3_req7_live_gate.py")

        tree = ast.parse(live_file.read_text(encoding="utf-8"), filename=str(live_file))
        code_str = live_file.read_text(encoding="utf-8")

        # Must check SAH_NAPSTER_LIVE, NAPSTER_API_KEY, and NAPSTER_AGENT_ID
        self.assertIn("SAH_NAPSTER_LIVE", code_str)
        self.assertIn("NAPSTER_API_KEY", code_str)
        self.assertIn("NAPSTER_AGENT_ID", code_str)
        self.assertIn("SkipTest", code_str)


if __name__ == "__main__":
    unittest.main()
