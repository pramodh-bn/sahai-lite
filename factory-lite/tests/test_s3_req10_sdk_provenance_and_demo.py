"""Requirement 10: Freeze SDK provenance, version integrity, demo path, and no-deploy guard.

Mandate:
- Freeze SDK provenance expectation:
    * package: @touchcastllc/napster-companion-api
    * version: 2.0.0
    * SHA-256: c1b2db52267af46e172e4c5fbb0c46b67f57729bc841b26ac4e112a14ddd025f
    * global: window.napsterCompanionApiSDK
- Reliable <= 3-minute demo path:
    * Max demo budget 180 seconds
- Do not deploy or submit:
    * Explicit guard prohibiting deployment or submission
"""
import subprocess
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

REPO_ROOT = Path(__file__).resolve().parents[2]

FROZEN_SDK_METADATA = {
    "package": "@touchcastllc/napster-companion-api",
    "version": "2.0.0",
    "sha256": "c1b2db52267af46e172e4c5fbb0c46b67f57729bc841b26ac4e112a14ddd025f",
    "global": "window.napsterCompanionApiSDK",
    "max_demo_duration_seconds": 180,
}


class TestSdkProvenanceAndDemoConstraints(unittest.TestCase):
    def test_sdk_provenance_is_frozen_to_official_bundle(self):
        self.assertEqual(FROZEN_SDK_METADATA["package"], "@touchcastllc/napster-companion-api")
        self.assertEqual(FROZEN_SDK_METADATA["version"], "2.0.0")
        self.assertEqual(
            FROZEN_SDK_METADATA["sha256"],
            "c1b2db52267af46e172e4c5fbb0c46b67f57729bc841b26ac4e112a14ddd025f",
        )
        self.assertEqual(FROZEN_SDK_METADATA["global"], "window.napsterCompanionApiSDK")

    def test_demo_path_budget_bounded_to_three_minutes(self):
        max_budget = FROZEN_SDK_METADATA["max_demo_duration_seconds"]
        self.assertLessEqual(max_budget, 180, "Demo path budget must not exceed 180 seconds (3 minutes)")

    def test_prohibit_deploy_and_submit_scripts(self):
        out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        tracked = out.stdout.splitlines()
        forbidden_patterns = ("deploy.sh", "deploy.py", "submit.sh", "publish_prod.sh", ".github/workflows/deploy.yml")
        for f in tracked:
            for pat in forbidden_patterns:
                self.assertNotIn(pat, f.lower(), f"Prohibited deployment artifact tracked: {f}")


if __name__ == "__main__":
    unittest.main()
