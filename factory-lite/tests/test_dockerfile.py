"""Test Dockerfile structure."""

import unittest

class TestDockerfile(unittest.TestCase):
    def test_dockerfile_exists(self):
        """Test that Dockerfile exists"""
        import os
        self.assertTrue(os.path.exists('app/Dockerfile'))
        
    def test_dockerfile_has_base_image(self):
        """Test that Dockerfile has base image"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('FROM python:', content)
        
    def test_dockerfile_runs_as_non_root(self):
        """Test that Dockerfile runs as non-root user"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('USER', content)
        self.assertIn('groupadd', content)
        self.assertIn('useradd', content)

if __name__ == '__main__':
    unittest.main()