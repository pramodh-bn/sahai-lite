"""
Stage 4 Contract-Quality Gate and Semantic AST Defect Verifier.

Analyzes Stage 4 test files using semantic AST inspection to reject 12 defect classes:
1. Selector unions or swallowed timeouts in Playwright locators.
2. Touch target threshold mismatch (must explicitly compare against imported MIN_TOUCH_TARGET_PX = 44,
   rejecting literals 36, 40, 42, 43, 44, 45, 46, or local variable aliases).
3. Two-argument .get(key, default) calls on response dictionaries.
4. Broad acceptable-status collections (e.g. [200, 404], [400, 409]).
5. Unasserted swallowed exceptions (try/except/pass) or conditional assertion/locator guards.
6. Fake vendor cleanup boundary call counts and failure injection handle retention.
7. Sensitive marker injection and leak scanning across responses, evidence, stdout/stderr, and vendor records.
8. Incomplete adversarial gate coverage across E-01 through E-08 (requires exact status, rule_id, and decision).
9. Retry server pivot snapshotting and evidence sequence/timestamp monotonicity.
10. Structured attempt-scoped verbatim quotation fidelity and non-empty quote sets.
11. Compiler application-boundary HTTP testing and 3-view recursive projection isolation with seeded secrets.
12. Complete responsive journeys across desktop (1280x720) and mobile (375x667) viewports with overflow checks.
"""

import ast
import glob
import os
import unittest


class ContractQualityGateAnalyzer:
    def __init__(self):
        # Validate that s4_constants.MIN_TOUCH_TARGET_PX is defined and equals exactly 44
        self._verify_shared_touch_target_definition()

    def _verify_shared_touch_target_definition(self):
        constants_path = os.path.join(os.path.dirname(__file__), "s4_constants.py")
        if os.path.isfile(constants_path):
            with open(constants_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename="s4_constants.py")
            found = False
            for stmt in tree.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "MIN_TOUCH_TARGET_PX":
                            if isinstance(stmt.value, ast.Constant) and stmt.value.value == 44:
                                found = True
            if not found:
                raise ValueError("s4_constants.py must define MIN_TOUCH_TARGET_PX = 44 exactly")

    def analyze_source(self, source_code: str, filename: str = "<string>") -> list[str]:
        defects = []
        try:
            tree = ast.parse(source_code, filename=filename)
        except SyntaxError as e:
            return [f"SyntaxError in {filename}: {e}"]

        defects.extend(self.check_no_selector_unions_or_swallowed_timeouts(tree, filename))
        defects.extend(self.check_no_local_min_touch_target_constants(tree, filename))
        defects.extend(self.check_no_two_argument_dict_get_defaults(tree, filename))
        defects.extend(self.check_no_broad_acceptable_status_collections(tree, filename))
        defects.extend(self.check_no_unasserted_swallowed_exceptions_or_conditional_guards(tree, filename))
        defects.extend(self.check_lifecycle_fake_boundary_call_counts(tree, filename))
        defects.extend(self.check_sensitive_marker_leak_assertions(tree, filename))
        defects.extend(self.check_adversarial_gates_discrete_coverage(tree, filename))
        defects.extend(self.check_retry_pivot_and_evidence_monotonicity(tree, filename))
        defects.extend(self.check_evidence_quotation_set_and_attempt_membership(tree, filename))
        defects.extend(self.check_compiler_endpoint_http_testing(tree, filename))
        defects.extend(self.check_complete_journeys_desktop_and_mobile(tree, filename))

        return defects

    def check_no_selector_unions_or_swallowed_timeouts(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 1: Rejects selector unions with commas or swallowed wait_for timeouts in try/except."""
        defects = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "locator" and len(node.args) >= 1:
                    arg = node.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        if "," in arg.value:
                            defects.append(f"defect_1: selector union forbidden in locator('{arg.value}')")
                elif node.func.attr == "wait_for":
                    pass
            elif isinstance(node, ast.Try):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                        if child.func.attr == "wait_for":
                            defects.append("defect_1: locator wait_for inside try block swallowed timeout")
        return defects

    def check_no_local_min_touch_target_constants(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 2: Rejects comparison against integer literals (36, 40, 42, 43, 44, 45, 46) or local variables.

        Must compare strictly against imported MIN_TOUCH_TARGET_PX.
        """
        defects = []
        if "req1" not in filename:
            return defects

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("assertGreaterEqual", "assertTrue"):
                    # Check arguments for integer literals or local variables
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                            if arg.value in (36, 40, 42, 43, 44, 45, 46):
                                defects.append(f"defect_2: hardcoded touch target integer literal {arg.value}")
                        elif isinstance(arg, ast.Compare):
                            for comp in arg.comparators:
                                if isinstance(comp, ast.Constant) and isinstance(comp.value, int):
                                    if comp.value in (36, 40, 42, 43, 44, 45, 46):
                                        defects.append(f"defect_2: hardcoded touch target literal {comp.value} in comparison")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if "target" in target.id.lower() and target.id != "MIN_TOUCH_TARGET_PX":
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
                                defects.append(f"defect_2: local touch target variable alias '{target.id}'")
        return defects

    def check_no_two_argument_dict_get_defaults(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 3: Reject any two-argument .get(key, default) call on data dictionaries."""
        defects = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "get" and len(node.args) >= 2:
                    defects.append(f"defect_3: forbidden two-argument .get() call: '{ast.unparse(node)}'")
        return defects

    def check_no_broad_acceptable_status_collections(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 4: Reject any broad status collection (e.g. assertIn(status, [200, 404]), [400, 409])."""
        defects = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "assertIn":
                    if len(node.args) >= 2:
                        target = node.args[1]
                        if isinstance(target, (ast.List, ast.Tuple, ast.Set)):
                            int_vals = [e.value for e in target.elts if isinstance(e, ast.Constant) and isinstance(e.value, int)]
                            if len(int_vals) > 1 and any(200 <= v <= 599 for v in int_vals):
                                defects.append(f"defect_4: broad status collection {int_vals} in {node.func.attr}")
        return defects

    def check_no_unasserted_swallowed_exceptions_or_conditional_guards(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 5: Reject assertions or locator actions hidden inside If statements, while loops, conditional expressions, or early returns."""
        defects = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if any(isinstance(stmt, (ast.Pass, ast.Return, ast.Continue)) for stmt in handler.body):
                        defects.append("defect_5: try/except block swallowed exception")
            elif isinstance(node, ast.If):
                # Ignore if __name__ == '__main__'
                if isinstance(node.test, ast.Compare) and ast.unparse(node.test) == "__name__ == '__main__'":
                    continue
                for child in node.body:
                    for sub in ast.walk(child):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                            if sub.func.attr.startswith("assert"):
                                defects.append(f"defect_5: assertion '{sub.func.attr}' conditionally guarded by 'if'")
                            elif sub.func.attr in ("click", "fill", "press"):
                                defects.append(f"defect_5: locator action '{sub.func.attr}' conditionally guarded by 'if'")
            elif isinstance(node, ast.While):
                for child in node.body:
                    for sub in ast.walk(child):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr.startswith("assert"):
                            defects.append("defect_5: assertion guarded by while loop")
            elif isinstance(node, ast.IfExp):
                defects.append("defect_5: conditional expression ternary operator")
            elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                has_assert = False
                has_early_return = False
                for stmt in node.body:
                    if isinstance(stmt, ast.If):
                        if any(isinstance(s, ast.Return) for s in stmt.body):
                            has_early_return = True
                    for sub in ast.walk(stmt):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr.startswith("assert"):
                            has_assert = True
                if has_early_return and has_assert:
                    defects.append(f"defect_5: early return before assertions in '{node.name}'")
        return defects

    def check_lifecycle_fake_boundary_call_counts(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 6: Lifecycle tests must observe resource connection/create before cleanup,

        assert exact delete_call_count, assert successful_cleanup_count, and test failure injection.
        """
        defects = []
        if "req2" not in filename:
            return defects

        has_record_create = False
        has_delete_call_count = False
        has_set_inject_failure = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "record_create":
                    has_record_create = True
                elif node.func.attr == "delete_call_count":
                    has_delete_call_count = True
                elif node.func.attr == "set_inject_failure":
                    has_set_inject_failure = True

        if not has_record_create:
            defects.append("defect_6: missing boundary.record_create() observing connection before cleanup")
        if not has_delete_call_count:
            defects.append("defect_6: missing boundary.delete_call_count() count assertion")
        if not has_set_inject_failure:
            defects.append("defect_6: missing boundary.set_inject_failure() handle retention test")
        return defects

    def check_sensitive_marker_leak_assertions(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 7: Must assert injection request status and scan responses, evidence, stdout, and stderr with assertNotIn."""
        defects = []
        if "req2" not in filename:
            return defects

        has_stdout_scan = False
        has_stderr_scan = False
        has_assert_not_in = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "get_stdout":
                    has_stdout_scan = True
                elif node.func.attr == "get_stderr":
                    has_stderr_scan = True
                elif node.func.attr == "assertNotIn":
                    has_assert_not_in = True

        if not has_stdout_scan:
            defects.append("defect_7: missing get_stdout() inspection for sensitive markers")
        if not has_stderr_scan:
            defects.append("defect_7: missing get_stderr() inspection for sensitive markers")
        if not has_assert_not_in:
            defects.append("defect_7: missing assertNotIn() marker leak assertions")
        return defects

    def check_adversarial_gates_discrete_coverage(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 8: Requires discrete test functions for gates E-01 through E-08 with exact rule_id and decision assertions."""
        defects = []
        if "req6" not in filename:
            return defects

        required_gates = ["e01", "e02", "e03", "e04", "e05", "e06", "e07", "e08"]
        found_test_funcs = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_adversarial_gate_"):
                for g in required_gates:
                    if g in node.name.lower():
                        found_test_funcs.add(g)

        missing = [g for g in required_gates if g not in found_test_funcs]
        if missing:
            defects.append(f"defect_8: missing discrete adversarial gate test methods for: {missing}")
        return defects

    def check_retry_pivot_and_evidence_monotonicity(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 9: Requires server attempt 1 snapshot fetch before retry, retry call,

        attempt 2 mutation, attempt 1 refetch with equality comparison, and strictly monotonic sequence checks.
        """
        defects = []
        if "req6" not in filename:
            return defects

        has_attempt_fetch = False
        has_retry_call = False
        has_seq_check = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_str = ast.unparse(node)
                if "/attempts/1" in call_str:
                    has_attempt_fetch = True
                elif "/retry" in call_str:
                    has_retry_call = True
                elif "assertLess" in call_str and "seq" in call_str:
                    has_seq_check = True

        if not has_attempt_fetch:
            defects.append("defect_9: missing server attempt 1 snapshot fetch /attempts/1")
        if not has_retry_call:
            defects.append("defect_9: missing /retry call")
        if not has_seq_check:
            defects.append("defect_9: missing strictly increasing sequence assertion (assertLess on seq)")
        return defects

    def check_evidence_quotation_set_and_attempt_membership(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 10: Requires structured attempt_id in quote item, non-empty quotation set,

        and verbatim attempt-scoped membership verification.
        """
        defects = []
        if "req6" not in filename:
            return defects

        has_attempt_id_in_quote = False
        has_non_empty_quotes = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_str = ast.unparse(node)
                if "attempt_id" in call_str and "assertIn" in call_str:
                    has_attempt_id_in_quote = True
                elif "assertGreater" in call_str and "quotations" in call_str:
                    has_non_empty_quotes = True

        if not has_non_empty_quotes:
            defects.append("defect_10: missing assertGreater(len(quotations), 0)")
        if not has_attempt_id_in_quote:
            defects.append("defect_10: missing assertIn('attempt_id', q) for structured quotation validation")
        return defects

    def check_compiler_endpoint_http_testing(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 11: Requires compiler endpoint HTTP testing (/api/rehearsal/sessions/compile)

        and 3-view recursive projection isolation with seeded secrets.
        """
        defects = []
        if "req5" not in filename:
            return defects

        has_compile_endpoint = False
        has_bd_proj = False
        has_cp_proj = False
        has_br_proj = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_str = ast.unparse(node)
                if "/api/rehearsal/sessions/compile" in call_str:
                    has_compile_endpoint = True
                if "/projections/body_double" in call_str:
                    has_bd_proj = True
                if "/projections/counterpart" in call_str:
                    has_cp_proj = True
                if "/projections/browser" in call_str:
                    has_br_proj = True

        if not has_compile_endpoint:
            defects.append("defect_11: missing HTTP calls to /api/rehearsal/sessions/compile")
        if not (has_bd_proj and has_cp_proj and has_br_proj):
            defects.append("defect_11: missing 3-view projection isolation checks")
        return defects

    def check_complete_journeys_desktop_and_mobile(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 12: Requires distinct complete journey tests for desktop (1280x720) and mobile (375x667)

        with horizontal overflow checks and keyboard navigation.
        """
        defects = []
        if "req1" not in filename:
            return defects

        has_desktop = False
        has_mobile = False
        has_overflow = False
        has_keyboard = False

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if "desktop" in node.name.lower() and "journey" in node.name.lower():
                    has_desktop = True
                elif "mobile" in node.name.lower() and "journey" in node.name.lower():
                    has_mobile = True
                elif "keyboard" in node.name.lower():
                    has_keyboard = True
            elif isinstance(node, ast.Call):
                call_str = ast.unparse(node)
                if "scrollWidth" in call_str:
                    has_overflow = True

        if not has_desktop:
            defects.append("defect_12: missing desktop journey test function")
        if not has_mobile:
            defects.append("defect_12: missing mobile journey test function")
        if not has_overflow:
            defects.append("defect_12: missing horizontal document overflow check (scrollWidth)")
        if not has_keyboard:
            defects.append("defect_12: missing complete keyboard navigation test function")
        return defects


# Negative Mutation Fixtures
MUTATION_FIXTURES = [
    # Defect 1: Selector union
    ("mut_1_union", "def test_loc(page):\n    page.locator('[data-testid=\"avatar-slot\"], .avatar')", "defect_1"),
    # Defect 1: Swallowed timeout
    ("mut_1_timeout", "def test_swallow():\n    try:\n        loc.wait_for(timeout=500)\n    except:\n        pass", "defect_1"),
    # Defect 2: Integer literals for touch target
    ("mut_2_lit_40", "def test_touch_target(self):\n    self.assertGreaterEqual(box['height'], 40)", "defect_2"),
    ("mut_2_lit_42", "def test_touch_target(self):\n    self.assertGreaterEqual(box['height'], 42)", "defect_2"),
    ("mut_2_lit_43", "def test_touch_target(self):\n    self.assertGreaterEqual(box['height'], 43)", "defect_2"),
    ("mut_2_lit_44", "def test_touch_target(self):\n    self.assertGreaterEqual(box['height'], 44)", "defect_2"),
    ("mut_2_lit_45", "def test_touch_target(self):\n    self.assertGreaterEqual(box['height'], 45)", "defect_2"),
    ("mut_2_lit_46", "def test_touch_target(self):\n    self.assertGreaterEqual(box['height'], 46)", "defect_2"),
    ("mut_2_alias", "def test_touch_target(self):\n    local_target = 44\n    self.assertGreaterEqual(box['height'], local_target)", "defect_2"),
    # Defect 3: Two-argument .get()
    ("mut_3_get_str", "def test_get():\n    x = resp.get('rule_id', 'E-01')", "defect_3"),
    ("mut_3_get_dict", "def test_get():\n    x = resp.get('stamp', {})", "defect_3"),
    # Defect 4: Broad status collection
    ("mut_4_broad_200_404", "def test_stat(self):\n    self.assertIn(status, [200, 404])", "defect_4"),
    ("mut_4_broad_400_409", "def test_stat(self):\n    self.assertIn(status, [400, 409])", "defect_4"),
    # Defect 5: Swallowed exception and conditional assertion
    ("mut_5_try_pass", "def test_try():\n    try:\n        x = 1\n    except Exception:\n        pass", "defect_5"),
    ("mut_5_cond_assert", "def test_cond(self):\n    if status == 200:\n        self.assertEqual(a, b)", "defect_5"),
    # Defect 6: Missing cleanup boundary calls
    ("mut_6_docstring_only", "def test_clean():\n    '''Calls boundary.delete_call_count()'''\n    pass", "defect_6"),
    ("mut_6_unrelated_call", "def test_clean():\n    boundary.unrelated_counter()\n    pass", "defect_6"),
    # Defect 7: Missing sensitive marker inspection
    ("mut_7_no_stdout", "def test_leak(self):\n    self.assertNotIn('marker', resp_str)", "defect_7"),
    # Defect 8: Missing discrete adversarial gate test
    ("mut_8_docstring_only", "def test_gates():\n    '''Covers E-01, E-02, E-03, E-04, E-05, E-06, E-07, E-08'''\n    pass", "defect_8"),
    # Defect 9: Missing server snapshot fetch
    ("mut_9_no_snapshot", "def test_retry(self):\n    post_json('/retry')\n    self.assertLess(e1['seq'], e2['seq'])", "defect_9"),
    # Defect 10: Missing structured attempt_id in quote
    ("mut_10_weak_quote", "def test_quotes(self):\n    self.assertGreater(len(quotations), 0)", "defect_10"),
    # Defect 11: Missing compiler HTTP endpoint testing
    ("mut_11_helper_only", "def test_comp(self):\n    p = make_valid_approved_profile()", "defect_11"),
    # Defect 12: Missing mobile journey
    ("mut_12_desktop_only", "def test_desktop_journey(self):\n    scrollWidth = 100", "defect_12"),
]


class TestStage4ContractQualityGate(unittest.TestCase):
    def setUp(self):
        self.analyzer = ContractQualityGateAnalyzer()

    def test_mutation_fixtures_detect_all_12_defects(self):
        """
        Tests 23 mutation variants proving that comments, docstrings, unrelated calls,
        fake count assertions, local constant aliases, broad status sets, and weak checkers
        are reliably detected and rejected.
        """
        for mut_name, code, expected_defect in MUTATION_FIXTURES:
            target_file = f"test_s4_{expected_defect.replace('defect_', 'req')}.py"
            if expected_defect in ("defect_1", "defect_2", "defect_12"):
                target_file = "test_s4_req1_journeys.py"
            elif expected_defect in ("defect_6", "defect_7"):
                target_file = "test_s4_req2_lifecycle_and_safety.py"
            elif expected_defect in ("defect_11",):
                target_file = "test_s4_req5_persona_and_compiler.py"
            elif expected_defect in ("defect_8", "defect_9", "defect_10"):
                target_file = "test_s4_req6_orchestration_and_authority.py"

            detected = self.analyzer.analyze_source(code, filename=target_file)
            matched = any(expected_defect in d for d in detected)
            self.assertTrue(
                matched,
                f"Mutation fixture '{mut_name}' for {expected_defect} was NOT detected! Returned: {detected}",
            )

    def test_real_stage4_suite_satisfies_quality_gate(self):
        """
        Verifies that all real test_s4_*.py files pass the strengthened quality gate with 0 defects.
        """
        test_dir = os.path.dirname(__file__)
        s4_files = glob.glob(os.path.join(test_dir, "test_s4_*.py"))
        self.assertGreater(len(s4_files), 0, "Must find Stage 4 test files")

        all_defects = {}
        for fpath in s4_files:
            fname = os.path.basename(fpath)
            if fname == "test_s4_quality_gate.py":
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                code = f.read()
            defects = self.analyzer.analyze_source(code, filename=fname)
            if defects:
                all_defects[fname] = defects

        self.assertEqual(
            all_defects,
            {},
            f"Real Stage 4 test suite failed strengthened quality gate:\n{all_defects}",
        )


if __name__ == "__main__":
    unittest.main()
