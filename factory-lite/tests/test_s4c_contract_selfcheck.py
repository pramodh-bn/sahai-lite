"""Stage 4C contract self-check (not product evidence).

Proves the 4C modules are present, importable, non-empty and free of
unconditional skips or passing-default assertions. Every product claim is
proved by the browser/packaging modules.
"""
import importlib
import re
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PRODUCT_MODULES = [
    "test_s4c_req1_responsive_journeys",
    "test_s4c_req2_keyboard_mic",
    "test_s4c_req3_slow_network_cleanup",
    "test_s4c_req4_packaging",
]
PLACEHOLDER_PATTERNS = [
    re.compile(r"raise unittest\.SkipTest"),
    re.compile(r"self\.skipTest\("),
    re.compile(r"assertTrue\(\s*True\s*\)"),
    re.compile(r"#\s*(?:TODO|TBD|FIXME)"),
]


class TestStage4CContractSelfCheck(unittest.TestCase):
    def test_every_product_module_exists_imports_and_contains_tests(self):
        total = 0
        for name in PRODUCT_MODULES:
            path = TESTS_DIR / f"{name}.py"
            self.assertTrue(path.is_file(), f"missing Stage 4C contract module: {path.name}")
            module = importlib.import_module(name)
            cases = [case for case in dir(module) if case.startswith("Test")]
            self.assertTrue(cases, f"{name} defines no Test* case class")
            for case in cases:
                cls = getattr(module, case)
                total += len([m for m in dir(cls) if m.startswith("test_")])
        self.assertGreaterEqual(total, 12, f"Stage 4C product suite is too small: {total} tests")

    def test_suite_has_no_skips_or_placeholder_assertions(self):
        offenders = []
        for name in PRODUCT_MODULES + ["test_s4c_contract_selfcheck"]:
            path = TESTS_DIR / f"{name}.py"
            text = path.read_text(encoding="utf-8")
            for pattern in PLACEHOLDER_PATTERNS:
                if pattern.search(text):
                    offenders.append(f"{path.name}: {pattern.pattern}")
        self.assertEqual(offenders, [],
                         f"Stage 4C contract contains skips/placeholders: {offenders}")


if __name__ == "__main__":
    unittest.main()
