import ast
import inspect
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


class TestStage3ContractSelfCheck(unittest.TestCase):
    """Verifier-owned meta-contract proving contract integrity, signature safety, and host policy."""

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

        # Explicit check: delete_napster_session must accept timeout
        sig_del = inspect.signature(s3_helpers.delete_napster_session)
        self.assertIn(
            "timeout",
            sig_del.parameters,
            "delete_napster_session must explicitly accept timeout parameter",
        )

        # Explicit check: validate_stage3_evidence must accept mode
        sig_val = inspect.signature(s3_helpers.validate_stage3_evidence)
        self.assertIn(
            "mode",
            sig_val.parameters,
            "validate_stage3_evidence must explicitly accept mode parameter",
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

        code_str = live_file.read_text(encoding="utf-8")
        tree = ast.parse(code_str, filename=str(live_file))

        # 1. Gate prerequisite checks
        self.assertIn("SAH_NAPSTER_LIVE", code_str)
        self.assertIn("NAPSTER_API_KEY", code_str)
        self.assertIn("NAPSTER_AGENT_ID", code_str)
        self.assertIn("SkipTest", code_str)

        # 2. Under open gate must require fresh SAH_STAGE3_EVIDENCE_PATH and clean temp files
        self.assertIn("SAH_STAGE3_EVIDENCE_PATH", code_str)
        self.assertIn("evidence_path.exists()", code_str)
        self.assertIn("temp_evidence.unlink()", code_str)

        # 3. Statically reject direct preallocation / double-session logic in live gate
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                if func_name == "post_napster_session":
                    self.fail(
                        f"Direct preallocation call '{func_name}' forbidden in live gate; "
                        "must use single browser-owned flow"
                    )
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if alias.name == "post_napster_session":
                        self.fail(
                            "Importing 'post_napster_session' is forbidden in live gate; "
                            "must rely strictly on single browser-owned session creation"
                        )

        # 4. Monotonic deadline helper & remaining-time use
        self.assertIn("monotonic", code_str)
        self.assertIn("get_remaining_timeout_ms", code_str)
        self.assertIn("CLEANUP_RESERVE_S", code_str)

        # 5. Exact observed POST status 200 without fallback default substitution
        self.assertNotIn('post_status"] or 200', code_str)
        self.assertNotIn("post_status'] or 200", code_str)
        normalized_code = code_str.replace('"', "'")
        self.assertIn("conn_hash_holder['post_status']", normalized_code)
        found_post_status_200 = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                if func_name == "assertEqual":
                    args_dump = [ast.dump(a) for a in node.args]
                    if any("post_status" in s for s in args_dump) and any("200" in s for s in args_dump):
                        found_post_status_200 = True
        self.assertTrue(found_post_status_200, "Must assert post_status == 200")

        # 6. Request observer accounting for outgoing requests
        self.assertIn('page.on("request"', code_str)
        self.assertIn("cleanup_attempted['sent'] = True", normalized_code)

        # 7. Deadline-bound click actions
        self.assertIn("connect_btn.click(timeout=", code_str)
        self.assertIn("disconnect_btn.click(timeout=", code_str)

        # 8. Deadline-bound wait_for_function for readiness and release predicates
        wait_for_func_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and getattr(node.func, "attr", None) == "wait_for_function"
        ]
        self.assertGreaterEqual(
            len(wait_for_func_calls),
            2,
            "Must use page.wait_for_function for both readiness and release predicates",
        )
        # Release wait callback must return exact boolean conjunction, NOT an object
        release_wait_code = wait_for_func_calls[1].args[0].value
        self.assertNotIn(
            "return {",
            release_wait_code,
            "Release wait callback must not return an object literal; objects are truthy in JS and return immediately",
        )
        self.assertIn("noLiveVideoTracks &&", release_wait_code)
        self.assertIn("noLiveAudioTracks &&", release_wait_code)
        self.assertIn("elementsCleared &&", release_wait_code)
        self.assertIn("avatarReadyFalse &&", release_wait_code)
        self.assertIn("sdkStatusUnavailable", release_wait_code)

        # 9. Exactly-once cleanup guard & deterministic observation
        self.assertIn("expect_response", code_str)
        self.assertIn("cleanup_attempted", code_str)
        self.assertIn("delete_napster_session", code_str)
        self.assertIn("timeout=rem_cleanup_s", code_str)
        self.assertNotIn(
            "max(0.1,",
            code_str,
            "Fallback cleanup must not start HTTP request with synthetic timeout when deadline exhausted",
        )
        self.assertIn("rem_cleanup_s <= 0", code_str)
        self.assertIn("Monotonic deadline exhausted before fallback cleanup", code_str)
        self.assertIn("possible retained", code_str.lower())
        # Indeterminate cleanup guard when connection observed without session ID
        self.assertIn("request_counts['post_connection'] > 0", normalized_code)

        # 10. Live-Only Host Policy Enforcement
        self.assertIn("companion-api.napster.com", code_str)
        self.assertIn("derive_and_validate_live_vendor_host", code_str)
        self.assertIn("mode='live'", normalized_code)

        # 11. Non-sensitive operational telemetry in evidence
        self.assertIn("active_duration_seconds", code_str)
        self.assertIn("connection_create_requests", code_str)
        self.assertIn("cleanup_requests", code_str)

        # 12. Evidence validation, certification, and atomic writing
        self.assertIn("validate_stage3_evidence", code_str)
        self.assertIn("is_stage3_certified", code_str)
        self.assertIn("replace", code_str)  # Atomic rename via Path.replace
        self.assertIn("hashlib.sha256", code_str)  # SHA-256 correlation hash


if __name__ == "__main__":
    unittest.main()
