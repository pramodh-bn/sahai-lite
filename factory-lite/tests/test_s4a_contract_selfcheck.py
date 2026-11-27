"""Stage 4A contract self-check (not product evidence).

This module only proves the contract suite is present, importable, non-empty
and free of unconditional skips or passing-default assertions. It is a
quality gate on the tests themselves; every product claim is proved by the
black-box ``test_s4a_req*`` modules against the running application.
"""
import importlib
import re
import unittest
from pathlib import Path

from s4_helpers import BD_MARKER, CP_MARKER, base_profile, compute_profile_hash, mutate, reseal

TESTS_DIR = Path(__file__).resolve().parent
PRODUCT_MODULES = [
    "test_s4a_req1_persona_compiler",
    "test_s4a_req2_two_role_projection",
    "test_s4a_req3_turns",
    "test_s4a_req4_authority_adversarial",
    "test_s4a_req5_retry_pivot",
    "test_s4a_req6_evidence_feedback",
    "test_s4a_req7_fidelity",
]
PLACEHOLDER_PATTERNS = [
    re.compile(r"raise unittest\.SkipTest"),
    re.compile(r"self\.skipTest\("),
    re.compile(r"assertTrue\(\s*True\s*\)"),
    re.compile(r"#\s*(?:TODO|TBD|FIXME)"),
]


class TestStage4AContractSelfCheck(unittest.TestCase):
    def test_every_product_module_exists_imports_and_contains_tests(self):
        total = 0
        for name in PRODUCT_MODULES:
            path = TESTS_DIR / f"{name}.py"
            self.assertTrue(path.is_file(), f"missing Stage 4A contract module: {path.name}")
            module = importlib.import_module(name)
            cases = [
                case for case in dir(module)
                if case.startswith("Test")
            ]
            self.assertTrue(cases, f"{name} defines no Test* case class")
            for case in cases:
                cls = getattr(module, case)
                methods = [m for m in dir(cls) if m.startswith("test_")]
                total += len(methods)
        self.assertGreaterEqual(total, 45,
                                f"Stage 4A product suite is too small: {total} tests")

    def test_suite_has_no_skips_or_placeholder_assertions(self):
        offenders = []
        for name in PRODUCT_MODULES + ["test_s4a_contract_selfcheck"]:
            path = TESTS_DIR / f"{name}.py"
            text = path.read_text(encoding="utf-8")
            for pattern in PLACEHOLDER_PATTERNS:
                if pattern.search(text):
                    offenders.append(f"{path.name}: {pattern.pattern}")
        self.assertEqual(offenders, [],
                         f"Stage 4A contract contains skips/placeholders: {offenders}")

    def test_canonical_profile_hash_is_deterministic_and_role_specific(self):
        first = base_profile("counterpart")
        second = base_profile("counterpart")
        self.assertEqual(compute_profile_hash(first), compute_profile_hash(second))
        self.assertEqual(first["provenance"]["profile_hash"], compute_profile_hash(first))
        self.assertNotEqual(
            compute_profile_hash(base_profile("body_double")),
            compute_profile_hash(first),
        )
        altered = reseal(mutate(first, "goals", ["a changed goal"]))
        self.assertNotEqual(compute_profile_hash(altered), compute_profile_hash(first))
        self.assertIn(CP_MARKER, second["knowledge"]["hidden_needs"][0]["summary"])
        self.assertIn(BD_MARKER, base_profile("body_double")["goals"][0])


if __name__ == "__main__":
    unittest.main()
