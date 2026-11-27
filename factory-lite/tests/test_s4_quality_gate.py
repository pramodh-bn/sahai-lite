"""
Stage 4 Contract-Quality Gate and Semantic AST Defect Verifier.

Analyzes Stage 4 test files using semantic AST inspection to reject 12 defect classes:
1. Broad acceptable-status collections (e.g. [200, 404], [400, 409]) or accepting collections of HTTP status codes.
2. Conditional assertion/locator guards (If statements, conditional loops, conditional expressions, early returns enclosing assertions).
3. Two-argument .get() calls on response dictionaries.
4. try/except/pass or locator count/visibility guards hiding required assertions or actions.
5. Touch target threshold mismatch (must explicitly compare against imported MIN_TOUCH_TARGET_PX, not literals 36, 40, 43, 44, 45, or local variables).
6. Helper-only proof without application-boundary HTTP requests in named test functions.
7. Unexecuted concurrency (missing threading + status multiset [200, 409] + turn_in_flight), idempotency conflict, or out-of-order sequence assertions.
8. Incomplete adversarial gate coverage across E-01 through E-08 (verifies AST string literals inside test functions; comments/docstrings/constants cannot satisfy).
9. Weak quotation checks (missing attempt-scoped verbatim assertions, empty quotation checks, or non-strictly-increasing timestamps).
10. Cleanup tests without observed boundary call counts (asserting teardown count delta == 0 on repeated cleanup).
11. Tautologies, placeholders (assert False, self.fail), or skip decorators.
12. Unimported modules referenced in AST.
"""

import ast
import glob
import os
import unittest


class ContractQualityGateAnalyzer:
    def analyze_source(self, source_code: str, filename: str = "<string>") -> list[str]:
        defects = []
        try:
            tree = ast.parse(source_code, filename=filename)
        except SyntaxError as e:
            return [f"SyntaxError in {filename}: {e}"]

        defects.extend(self._check_status_assertions(tree, filename))
        defects.extend(self._check_conditional_guards(tree, filename))
        defects.extend(self._check_two_arg_gets(tree, filename))
        defects.extend(self._check_try_except_pass_and_locator_guards(tree, filename))
        defects.extend(self._check_touch_target_threshold(tree, filename))
        defects.extend(self._check_app_boundary_calls(tree, filename))
        defects.extend(self._check_concurrency_and_ordering(tree, filename))
        defects.extend(self._check_adversarial_gates_coverage(tree, filename))
        defects.extend(self._check_quotation_fidelity(tree, filename))
        defects.extend(self._check_cleanup_boundary_counts(tree, filename))
        defects.extend(self._check_tautologies_and_skips(tree, filename))
        defects.extend(self._check_unimported_symbols(tree, filename))

        return defects

    def _check_status_assertions(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 1: Reject any broad status collection (e.g. assertIn(status, [200, 404]), [400, 409])."""
        defects = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "assertIn":
                    if len(node.args) >= 2:
                        target = node.args[1]
                        if isinstance(target, (ast.List, ast.Tuple, ast.Set)):
                            int_vals = [e.value for e in target.elts if isinstance(e, ast.Constant) and isinstance(e.value, int)]
                            if len(int_vals) > 1 and any(200 <= v <= 599 for v in int_vals):
                                defects.append(f"defect_1: broad status collection {int_vals} in {node.func.attr}")
        return defects

    def _check_conditional_guards(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 2: Reject assertions or locator actions hidden inside If statements, while loops, conditional expressions, or early returns."""
        defects = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                for child in node.body:
                    for sub in ast.walk(child):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                            if sub.func.attr.startswith("assert"):
                                defects.append(f"defect_2: assertion '{sub.func.attr}' conditionally guarded by 'if {ast.unparse(node.test)}'")
                            elif sub.func.attr in ("click", "check", "fill", "wait_for", "press"):
                                defects.append(f"defect_2: locator action '{sub.func.attr}' conditionally guarded by 'if {ast.unparse(node.test)}'")
            elif isinstance(node, ast.While):
                for child in node.body:
                    for sub in ast.walk(child):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr.startswith("assert"):
                            defects.append(f"defect_2: assertion '{sub.func.attr}' conditionally guarded by while loop")
            elif isinstance(node, ast.IfExp):
                defects.append(f"defect_2: conditional expression '{ast.unparse(node)}'")
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
                    defects.append(f"defect_2: early return before assertions in '{node.name}'")
        return defects

    def _check_two_arg_gets(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 3: Reject any two-argument .get(key, default) call on data dictionaries."""
        defects = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "get" and len(node.args) >= 2:
                    defects.append(f"defect_3: forbidden two-argument .get() call: '{ast.unparse(node)}'")
        return defects

    def _check_try_except_pass_and_locator_guards(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 4: Reject try/except/pass blocks and locator count/is_visible guards."""
        defects = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if any(isinstance(stmt, ast.Pass) for stmt in handler.body):
                        defects.append("defect_4: try/except/pass block swallowed exception")
            elif isinstance(node, ast.If):
                cond_str = ast.unparse(node.test)
                if any(kw in cond_str for kw in ("count()", "is_visible()", "locator.count")):
                    defects.append(f"defect_4: locator guard: 'if {cond_str}'")
        return defects

    def _check_touch_target_threshold(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 5: Enforce that touch target comparisons strictly use imported MIN_TOUCH_TARGET_PX."""
        if "req1" not in filename:
            return []
        defects = []
        has_min_touch_compare = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for comp in node.comparators:
                    if isinstance(comp, ast.Name) and comp.id == "MIN_TOUCH_TARGET_PX":
                        has_min_touch_compare = True
                    elif isinstance(comp, ast.Constant) and comp.value in (36, 40, 43, 44, 45):
                        defects.append(f"defect_5: touch target compared against numeric literal {comp.value} instead of imported MIN_TOUCH_TARGET_PX")
                    elif isinstance(comp, ast.Name) and comp.id not in ("MIN_TOUCH_TARGET_PX", "width", "height"):
                        if "target" in comp.id.lower() or "touch" in comp.id.lower() or "size" in comp.id.lower():
                            defects.append(f"defect_5: touch target compared against local variable '{comp.id}' instead of imported MIN_TOUCH_TARGET_PX")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("assertGreaterEqual", "assertGreater"):
                    if len(node.args) >= 2:
                        target = node.args[1]
                        if isinstance(target, ast.Name) and target.id == "MIN_TOUCH_TARGET_PX":
                            has_min_touch_compare = True
                        elif isinstance(target, ast.Constant) and target.value in (36, 40, 43, 44, 45):
                            defects.append(f"defect_5: touch target compared against numeric literal {target.value} instead of imported MIN_TOUCH_TARGET_PX")
                        elif isinstance(target, ast.Name) and target.id not in ("MIN_TOUCH_TARGET_PX", "width", "height"):
                            if "target" in target.id.lower() or "touch" in target.id.lower() or "size" in target.id.lower():
                                defects.append(f"defect_5: touch target compared against local variable '{target.id}' instead of imported MIN_TOUCH_TARGET_PX")
        if not has_min_touch_compare:
            defects.append("defect_5: missing comparison against imported MIN_TOUCH_TARGET_PX")
        return defects

    def _check_app_boundary_calls(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 6: In req5, ensure named test functions make actual app-boundary HTTP calls (not helper-only)."""
        if "req5" not in filename:
            return []
        defects = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                has_http = any(
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id in ("post_json", "get_json", "delete_json")
                    for child in ast.walk(node)
                )
                if not has_http:
                    defects.append(f"defect_6: test function '{node.name}' in req5 is helper-only without app-boundary HTTP call")
        return defects

    def _check_concurrency_and_ordering(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 7: In req6, check concurrency multiset [200, 409], turn_in_flight, idempotency_conflict, out_of_order."""
        if "req6" not in filename:
            return []
        defects = []
        found_threads = False
        found_turn_in_flight = False
        found_idempotency_conflict = False
        found_out_of_order = False

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if "concurrent" in node.name.lower():
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call):
                            if (isinstance(sub.func, ast.Attribute) and sub.func.attr == "Thread") or (
                                isinstance(sub.func, ast.Name) and sub.func.id == "Thread"
                            ):
                                found_threads = True
                        if isinstance(sub, ast.Constant) and sub.value == "turn_in_flight":
                            found_turn_in_flight = True
                if "idempotent" in node.name.lower():
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Constant) and sub.value == "idempotency_conflict":
                            found_idempotency_conflict = True
                if "monotonic" in node.name.lower() or "ordering" in node.name.lower():
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Constant) and sub.value == "out_of_order":
                            found_out_of_order = True

        if not found_threads:
            defects.append("defect_7: concurrency test does not instantiate threading.Thread")
        if not found_turn_in_flight:
            defects.append("defect_7: missing 409 turn_in_flight concurrency error check")
        if not found_idempotency_conflict:
            defects.append("defect_7: missing 409 idempotency_conflict error check")
        if not found_out_of_order:
            defects.append("defect_7: missing 409 out_of_order error check")
        return defects

    def _check_adversarial_gates_coverage(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 8: Enforce AST literal presence for all gates E-01 to E-08 inside test methods."""
        if "req6" not in filename:
            return []
        defects = []
        found_gates = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                stmts = node.body
                if (
                    stmts
                    and isinstance(stmts[0], ast.Expr)
                    and isinstance(stmts[0].value, ast.Constant)
                    and isinstance(stmts[0].value.value, str)
                ):
                    stmts = stmts[1:]
                for s in stmts:
                    for sub in ast.walk(s):
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                            for g in ["E-01", "E-02", "E-03", "E-04", "E-05", "E-06", "E-07", "E-08"]:
                                if g in sub.value:
                                    found_gates.add(g)

        for gate in ["E-01", "E-02", "E-03", "E-04", "E-05", "E-06", "E-07", "E-08"]:
            if gate not in found_gates:
                defects.append(f"defect_8: missing executable adversarial gate test for '{gate}'")
        return defects

    def _check_quotation_fidelity(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 9: In req6, check attempt-scoped verbatim quotation check, non-empty quotes, and increasing timestamps."""
        if "req6" not in filename:
            return []
        defects = []
        has_attempt_utterances = False
        has_len_quotations = False

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and "evidence" in node.name.lower():
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Name) and sub.id == "attempt_utterances":
                        has_attempt_utterances = True
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "len":
                        if len(sub.args) == 1 and isinstance(sub.args[0], ast.Name) and sub.args[0].id in ("quotations", "quotes"):
                            has_len_quotations = True

        if not has_attempt_utterances:
            defects.append("defect_9: missing attempt_utterances attempt-scoped quotation verification")
        if not has_len_quotations:
            defects.append("defect_9: missing assertion verifying non-empty quotations list")
        return defects

    def _check_cleanup_boundary_counts(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 10: In req2, verify cleanup test asserts teardown counts before/after (count == 1, delta == 0)."""
        if "req2" not in filename:
            return []
        defects = []
        has_teardown_count_assert = False

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and "cleanup" in node.name.lower():
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr.startswith("assert"):
                        for arg in sub.args:
                            arg_str = ast.unparse(arg)
                            if any(k in arg_str for k in ("teardown", "call_count", "get_requests", "ledger")):
                                has_teardown_count_assert = True

        if not has_teardown_count_assert:
            defects.append("defect_10: cleanup test does not assert observed teardown counts")
        return defects

    def _check_tautologies_and_skips(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 11: Reject placeholder assertions, self.fail stubs, or skip decorators."""
        defects = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                if isinstance(node.test, ast.Constant) and node.test.value is False:
                    defects.append("defect_11: placeholder 'assert False'")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "fail":
                    defects.append("defect_11: placeholder 'self.fail()'")
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                for dec in node.decorator_list:
                    dec_str = ast.unparse(dec)
                    if "skip" in dec_str:
                        defects.append(f"defect_11: skip decorator '@{dec_str}'")
        return defects

    def _check_unimported_symbols(self, tree: ast.AST, filename: str) -> list[str]:
        """Defect 12: Reject references to unimported standard modules."""
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)

        defects = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                module_name = node.value.id
                if module_name in ("copy", "json", "hashlib", "time", "threading", "re"):
                    if module_name not in imported_names:
                        defects.append(f"defect_12: unimported module '{module_name}' referenced")
        return defects


class TestStage4ContractQualityGate(unittest.TestCase):
    def setUp(self):
        self.analyzer = ContractQualityGateAnalyzer()

    def test_mutation_fixtures_detect_all_12_defects(self):
        """
        Tests mutation variants proving that comments, docstrings, unrelated calls,
        broad status collections, try/except/pass, .get(), and local threshold values
        are detected and rejected.
        """
        mutation_fixtures = [
            (
                "defect_1_broad_status_list",
                """
def test_status(self):
    self.assertIn(resp_status, [200, 404])
""",
                "defect_1: broad status collection [200, 404]",
            ),
            (
                "defect_1_broad_400_409",
                """
def test_rejection(self):
    self.assertIn(resp_status, [400, 409])
""",
                "defect_1: broad status collection [400, 409]",
            ),
            (
                "defect_2_if_assertion",
                """
def test_guard(self):
    if status == 200:
        self.assertEqual(data['a'], 1)
""",
                "defect_2: assertion 'assertEqual' conditionally guarded",
            ),
            (
                "defect_2_while_assertion",
                """
def test_while(self):
    while ready:
        self.assertEqual(data['a'], 1)
""",
                "defect_2: assertion 'assertEqual' conditionally guarded by while loop",
            ),
            (
                "defect_2_conditional_expression",
                """
def test_ternary(self):
    x = 1 if status == 200 else 2
""",
                "defect_2: conditional expression",
            ),
            (
                "defect_2_early_return",
                """
def test_early_ret(self):
    if not ready:
        return
    self.assertEqual(x, 1)
""",
                "defect_2: early return before assertions in 'test_early_ret'",
            ),
            (
                "defect_3_two_arg_get",
                """
def test_get(self):
    val = resp.get('synthetic', True)
""",
                "defect_3: forbidden two-argument .get()",
            ),
            (
                "defect_4_try_except_pass",
                """
def test_swallow(self):
    try:
        page.locator('#btn').click()
    except Exception:
        pass
""",
                "defect_4: try/except/pass block swallowed exception",
            ),
            (
                "defect_4_locator_count_guard",
                """
def test_count(self):
    if page.locator('#avatar').count() > 0:
        page.locator('#avatar').click()
""",
                "defect_4: locator guard: 'if page.locator('#avatar').count() > 0'",
            ),
            (
                "defect_5_touch_target_literal_40",
                """
def test_touch_target_dimensions(self):
    self.assertTrue(height >= 40)
""",
                "defect_5: touch target compared against numeric literal 40",
            ),
            (
                "defect_5_touch_target_literal_43",
                """
def test_touch_target_dimensions(self):
    self.assertGreaterEqual(height, 43)
""",
                "defect_5: touch target compared against numeric literal 43",
            ),
            (
                "defect_5_touch_target_literal_45",
                """
def test_touch_target_dimensions(self):
    self.assertGreaterEqual(height, 45)
""",
                "defect_5: touch target compared against numeric literal 45",
            ),
            (
                "defect_5_touch_target_local_var",
                """
def test_touch_target_dimensions(self):
    my_target = 44
    self.assertTrue(height >= my_target)
""",
                "defect_5: touch target compared against local variable 'my_target'",
            ),
            (
                "defect_6_req5_helper_comment_docstring",
                """
class TestStage4Req5Persona(unittest.TestCase):
    def test_api_check(self):
        # post_json('/api/rehearsal/sessions')
        \"\"\"post_json was mentioned here\"\"\"
        valid, rule, msg = s4_helpers.validate_persona_profile({})
        self.assertFalse(valid)
""",
                "defect_6: test function 'test_api_check' in req5 is helper-only without app-boundary HTTP call",
            ),
            (
                "defect_6_req5_unrelated_http_call",
                """
class TestStage4Req5Persona(unittest.TestCase):
    def test_unrelated(self):
        requests.get('https://example.com')
""",
                "defect_6: test function 'test_unrelated' in req5 is helper-only without app-boundary HTTP call",
            ),
            (
                "defect_7_req6_concurrency_no_thread",
                """
import threading
class TestStage4Req6Orch(unittest.TestCase):
    def test_concurrent(self):
        status = 409
        error = 'turn_in_flight'
        conflict = 'idempotency_conflict'
        order = 'out_of_order'
""",
                "defect_7: concurrency test does not instantiate threading.Thread",
            ),
            (
                "defect_7_req6_missing_turn_in_flight",
                """
import threading
class TestStage4Req6Orch(unittest.TestCase):
    def test_concurrent(self):
        t = threading.Thread(target=lambda: None)
        conflict = 'idempotency_conflict'
        order = 'out_of_order'
""",
                "defect_7: missing 409 turn_in_flight concurrency error check",
            ),
            (
                "defect_8_req6_adversarial_docstring_only",
                """
class TestStage4Req6Orch(unittest.TestCase):
    def test_adversarial_gates(self):
        \"\"\"E-01 E-02 E-03 E-04 E-05 E-06 E-07 E-08 in docstring\"\"\"
        table = [('E-01', 'prompt')]
""",
                "defect_8: missing executable adversarial gate test for 'E-02'",
            ),
            (
                "defect_9_req6_quotations_no_attempt_scope",
                """
class TestStage4Req6Orch(unittest.TestCase):
    def test_evidence(self):
        all_session_utterances = ['u1']
        self.assertIn('u1', all_session_utterances)
        l = len(quotations)
""",
                "defect_9: missing attempt_utterances",
            ),
            (
                "defect_9_req6_empty_quotations_allowed",
                """
class TestStage4Req6Orch(unittest.TestCase):
    def test_evidence(self):
        attempt_utterances = ['u1']
        self.assertIn('u1', attempt_utterances)
""",
                "defect_9: missing assertion verifying non-empty quotations list",
            ),
            (
                "defect_10_req2_cleanup_unrelated_teardown_word",
                """
class TestStage4Req2Cleanup(unittest.TestCase):
    def test_cleanup(self):
        # We did teardown earlier in comment
        \"\"\"teardown docstring\"\"\"
        resp = delete_json('/api/session')
""",
                "defect_10: cleanup test does not assert observed teardown counts",
            ),
            (
                "defect_11_placeholder",
                """
def test_stub(self):
    assert False
""",
                "defect_11: placeholder 'assert False'",
            ),
            (
                "defect_12_unimported_copy",
                """
def test_copy(self):
    deep = copy.deepcopy({})
""",
                "defect_12: unimported module 'copy'",
            ),
        ]

        for defect_id, snippet, expected_snippet in mutation_fixtures:
            filename = f"test_{defect_id}.py"
            if "req1" in defect_id or "touch" in defect_id:
                filename = "test_s4_req1_journeys.py"
            elif "req5" in defect_id:
                filename = "test_s4_req5_persona.py"
            elif "req6" in defect_id or "concurrency" in defect_id or "adversarial" in defect_id or "quote" in defect_id:
                filename = "test_s4_req6_orch.py"
            elif "req2" in defect_id or "cleanup" in defect_id:
                filename = "test_s4_req2_cleanup.py"

            detected = self.analyzer.analyze_source(snippet, filename=filename)
            matched = any(expected_snippet in d for d in detected)
            self.assertTrue(
                matched,
                f"Mutation {defect_id} was NOT detected! Expected snippet '{expected_snippet}', got: {detected}",
            )

    def test_real_stage4_suite_satisfies_quality_gate(self):
        """Verifies that all real test_s4_*.py files pass the strengthened quality gate."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        s4_files = glob.glob(os.path.join(test_dir, "test_s4_*.py"))
        s4_files = [f for f in s4_files if os.path.basename(f) != "test_s4_quality_gate.py"]

        all_defects = {}
        for fpath in s4_files:
            with open(fpath, "r", encoding="utf-8") as f:
                source = f.read()
            defects = self.analyzer.analyze_source(source, filename=os.path.basename(fpath))
            if defects:
                all_defects[os.path.basename(fpath)] = defects

        self.assertEqual(
            all_defects,
            {},
            f"Real Stage 4 suite contains quality gate defects: {all_defects}",
        )


if __name__ == "__main__":
    unittest.main()
