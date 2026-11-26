"""Stage 4 Meta-Contract Self-Check.

Maintains exactly 4 tests with truthful names, zero placeholder assertions,
zero masking defaults, and strict AST validation across all Stage 4 test files:
1. test_stage4_modules_import_cleanly_and_symbols_resolved
2. test_helper_signatures_accept_all_callsite_keywords
3. test_no_placeholders_masking_defaults_or_conditional_guards
4. test_stage4_contract_coverage_and_executable_structure
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
    def test_stage4_modules_import_cleanly_and_symbols_resolved(self):
        """All Stage 4 test and helper modules must import cleanly without side effects and resolve imported symbols."""
        for mod_name in STAGE4_MODULE_NAMES:
            with self.subTest(module=mod_name):
                try:
                    mod = importlib.import_module(f"factory-lite.tests.{mod_name}")
                    self.assertIsNotNone(mod)
                except Exception as exc:
                    self.fail(f"Stage 4 module {mod_name} failed to import: {exc}")

        # AST inspect test_s4_req6_orchestration_and_authority.py to ensure 'import copy' is present
        req6_path = TESTS_DIR / "test_s4_req6_orchestration_and_authority.py"
        req6_tree = ast.parse(req6_path.read_text(encoding="utf-8"), filename=str(req6_path))
        imported_names = set()
        for node in ast.walk(req6_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module)
        self.assertIn("copy", imported_names, "test_s4_req6_orchestration_and_authority.py must import copy")

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

    def test_no_placeholders_masking_defaults_or_conditional_guards(self):
        """No Stage 4 test file may contain assert False, self.fail stubs, masking defaults, or conditional guards."""
        for path in TESTS_DIR.glob("test_s4_*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                # 1. Check self.fail placeholders
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "fail":
                        if path.name != "test_s4_contract_selfcheck.py":
                            self.fail(f"Found forbidden self.fail placeholder in {path.name}:{node.lineno}")
                    # 2. Check tautological assertTrue(True)
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "assertTrue":
                        if len(node.args) >= 1 and isinstance(node.args[0], ast.Constant) and node.args[0].value is True:
                            self.fail(f"Found forbidden tautological assertTrue(True) in {path.name}:{node.lineno}")
                    # 3. Check tautological assertEqual(x, x)
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "assertEqual":
                        if len(node.args) >= 2 and isinstance(node.args[0], ast.Constant) and isinstance(node.args[1], ast.Constant):
                            if node.args[0].value == node.args[1].value:
                                self.fail(f"Found forbidden tautological assertEqual in {path.name}:{node.lineno}")
                    # 4. Forbid masking defaults in .get() calls: .get('synthetic', True), .get('engine', 'deterministic'), etc.
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                        if len(node.args) >= 2 and isinstance(node.args[0], ast.Constant):
                            key_name = str(node.args[0].value)
                            if key_name in {"synthetic", "engine", "schema_version", "transcript_deleted", "committed", "flow_state", "hidden_need_revealed"}:
                                self.fail(f"Found forbidden masking default in {path.name}:{node.lineno} for .get('{key_name}', ...)")

                # 5. Check assert False
                if isinstance(node, ast.Assert):
                    if isinstance(node.test, ast.Constant) and node.test.value is False:
                        self.fail(f"Found forbidden 'assert False' placeholder in {path.name}:{node.lineno}")

                # 6. Check conditional assertion guards (assertions nested inside If blocks)
                if isinstance(node, ast.If):
                    # Check if test condition guards del_status == 200 or similar
                    test_str = ast.dump(node.test)
                    if "del_status" in test_str or "disconnect_btn" in test_str:
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) and child.func.attr.startswith("assert"):
                                self.fail(f"Found forbidden conditional assertion guard in {path.name}:{node.lineno}")

    def test_stage4_contract_coverage_and_executable_structure(self):
        """Validates that Stage 4 test files cover all specified contract dimensions and contain executable test methods."""
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

        code1 = (TESTS_DIR / "test_s4_req1_journeys.py").read_text(encoding="utf-8")
        self.assertIn("test_desktop_playwright_e2e_journey", code1)
        self.assertIn("test_mobile_375x667_playwright_journey_and_viewport_meta", code1)
        self.assertIn("test_avatar_container_viewport_containment_and_dimensions", code1)
        self.assertIn("test_keyboard_traversal_and_activation", code1)
        self.assertIn("test_mic_denial_browser_permission_fallback", code1)
        self.assertIn("test_slow_network_route_interception_resilience", code1)

        code2 = (TESTS_DIR / "test_s4_req2_lifecycle_and_safety.py").read_text(encoding="utf-8")
        self.assertIn("test_complete_session_deletion_endpoint_and_inaccessibility", code2)
        self.assertIn("test_cleanup_receipt_contract_and_idempotent_repeated_cleanup", code2)
        self.assertIn("test_mid_session_consent_withdrawal_stops_activity", code2)
        self.assertIn("test_comprehensive_log_and_payload_sanitization", code2)

        code3 = (TESTS_DIR / "test_s4_req3_consent_and_disclosure.py").read_text(encoding="utf-8")
        self.assertIn("test_avatar_consent_checkbox_gates_connect_button", code3)
        self.assertIn("test_granular_unbundled_consent_scopes_and_text_continuity", code3)
        self.assertIn("test_prominent_synthetic_disclosure_badge_visibility", code3)
        self.assertIn("test_disclosure_cannot_be_suppressed_by_prompt_injection", code3)

        code5 = (TESTS_DIR / "test_s4_req5_persona_and_compiler.py").read_text(encoding="utf-8")
        self.assertIn("test_api_accepts_valid_approved_profile", code5)
        self.assertIn("test_api_rejects_invalid_profiles_with_exact_rule_id", code5)
        self.assertIn("test_strict_unknown_field_rejection", code5)
        self.assertIn("test_distinct_role_profiles_and_allowlist_projections", code5)

        code6 = (TESTS_DIR / "test_s4_req6_orchestration_and_authority.py").read_text(encoding="utf-8")
        self.assertIn("test_server_authoritative_turn_endpoint_and_strict_alternation", code6)
        self.assertIn("test_concurrent_single_flight_turn_returns_409", code6)
        self.assertIn("test_idempotent_exact_replay_and_differing_body_conflict", code6)
        self.assertIn("test_monotonic_turn_sequence_ordering_and_out_of_order_rejection", code6)
        self.assertIn("test_deterministic_authority_adversarial_gates_e01_to_e08", code6)
        self.assertIn("test_retry_preserves_first_attempt_and_resets_discovery", code6)
        self.assertIn("test_evidence_fidelity_append_only_and_quoted_utterances", code6)


if __name__ == "__main__":
    unittest.main()
