"""Req 5 (stage-1.md): "no secrets in repo."

Scans every git-tracked file for common secret patterns and for untracked-env
leakage. Static, offline, read-only check -- no network calls.
"""
import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style secret key
    re.compile(r"sk_live_[0-9a-zA-Z]{16,}"),  # Stripe live key
    re.compile(r"(?i)\bsecret\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"),
    re.compile(r"(?i)\bpassword\b\s*[:=]\s*['\"][^'\"\s]{4,}['\"]"),
    re.compile(r"(?i)\bapi[_-]?key\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"),
]

ALLOWED_ENV_SUFFIXES = (".env.example", ".env.sample", ".env.template")


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def tracked_text_files():
    for rel in tracked_files():
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        try:
            yield rel, path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue


class TestNoRepositorySecrets(unittest.TestCase):
    def test_no_tracked_file_matches_secret_patterns(self):
        findings = []
        for rel, text in tracked_text_files():
            if rel.endswith(ALLOWED_ENV_SUFFIXES):
                continue
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    findings.append((rel, pattern.pattern))
        self.assertEqual(findings, [], f"possible secret(s) found in tracked files: {findings}")

    def test_no_env_file_with_real_values_is_tracked(self):
        tracked = tracked_files()
        bad = [
            f
            for f in tracked
            if (f.endswith(".env") or ".env." in f) and not f.endswith(ALLOWED_ENV_SUFFIXES)
        ]
        self.assertEqual(bad, [], f"tracked .env-like file(s) with potential real values: {bad}")


if __name__ == "__main__":
    unittest.main()
