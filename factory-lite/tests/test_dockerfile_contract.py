"""Test Dockerfile contract compliance."""

import unittest

class TestDockerfileContract(unittest.TestCase):
    def test_dockerfile_base_image_pinned(self):
        """Test that Dockerfile base image is pinned by digest"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('@sha256:', content)
        
    def test_dockerfile_non_root_runtime(self):
        """Test that Dockerfile runs as non-root user"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('USER appuser', content)
        
    def test_dockerfile_locked_dependencies(self):
        """Test that Dockerfile installs locked dependencies"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('requirements.lock', content)
        
    def test_dockerfile_build_metadata(self):
        """Test that Dockerfile injects build metadata"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('GIT_SHA', content)
        self.assertIn('ARG', content)

if __name__ == '__main__':
    unittest.main()