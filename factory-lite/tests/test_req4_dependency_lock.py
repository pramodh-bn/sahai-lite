"""Req 4 (stage-1.md): "dependency lock."

Contract convention: app/ contains at least one recognized, non-empty
dependency lock file.
"""
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "app"
LOCK_CANDIDATES = [
    "requirements.lock",
    "poetry.lock",
    "Pipfile.lock",
    "uv.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
]


class TestDependencyLockExists(unittest.TestCase):
    def test_app_dir_exists(self):
        self.assertTrue(APP_DIR.is_dir(), f"missing {APP_DIR}")

    def test_dependency_lock_file_present(self):
        self.assertTrue(APP_DIR.is_dir(), f"missing {APP_DIR}; cannot verify a lock file")
        found = [c for c in LOCK_CANDIDATES if (APP_DIR / c).is_file()]
        self.assertTrue(found, f"no recognized dependency lock file in {APP_DIR} (looked for {LOCK_CANDIDATES})")

    def test_dependency_lock_file_nonempty(self):
        self.assertTrue(APP_DIR.is_dir(), f"missing {APP_DIR}")
        found = [c for c in LOCK_CANDIDATES if (APP_DIR / c).is_file()]
        self.assertTrue(found, "no lock file found (see test_dependency_lock_file_present)")
        for name in found:
            path = APP_DIR / name
            self.assertGreater(path.stat().st_size, 0, f"lock file {path} is empty")


if __name__ == "__main__":
    unittest.main()
