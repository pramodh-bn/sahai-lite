"""Req 3 (stage-1.md): "container non-root."

Contract convention: app/Dockerfile exists, builds, and the resulting
container runs as a non-root UID. This is verified by actually building the
image and running `id -u` inside it (true black-box check of the running
container, not just static inspection of the Dockerfile source).
"""
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = REPO_ROOT / "app" / "Dockerfile"
IMAGE_TAG = "sahai-lite-stage1-nonroot-check:verifier-test"


class TestContainerRunsNonRoot(unittest.TestCase):
    def test_dockerfile_exists(self):
        self.assertTrue(DOCKERFILE.is_file(), f"missing {DOCKERFILE}")

    def test_container_runs_as_non_root_uid(self):
        self.assertTrue(DOCKERFILE.is_file(), f"missing {DOCKERFILE}; cannot build image")

        build = subprocess.run(
            ["docker", "build", "-f", str(DOCKERFILE), "-t", IMAGE_TAG, str(DOCKERFILE.parent)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(build.returncode, 0, f"docker build failed:\n{build.stdout}\n{build.stderr}")

        try:
            run = subprocess.run(
                ["docker", "run", "--rm", IMAGE_TAG, "id", "-u"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(run.returncode, 0, f"docker run failed:\n{run.stdout}\n{run.stderr}")
            uid = run.stdout.strip()
            self.assertTrue(uid.isdigit(), f"unexpected `id -u` output: {uid!r}")
            self.assertNotEqual(uid, "0", "container runs as root (uid 0)")
        finally:
            subprocess.run(["docker", "rmi", "-f", IMAGE_TAG], capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
