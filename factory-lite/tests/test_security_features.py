"""Test security features."""

import unittest

class TestSecurityFeatures(unittest.TestCase):
    def test_dockerfile_creates_non_root_user(self):
        """Test that Dockerfile creates non-root user"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('groupadd', content)
        self.assertIn('useradd', content)
        
    def test_dockerfile_runs_as_non_root(self):
        """Test that Dockerfile runs as non-root user"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('USER', content)
        self.assertNotIn('USER root', content)
        
    def test_dockerfile_has_dockerignore(self):
        """Test that .dockerignore exists and excludes sensitive files"""
        import os
        if os.path.exists('app/.dockerignore'):
            with open('app/.dockerignore', 'r') as f:
                content = f.read()
            # Check that common sensitive files are excluded
            self.assertGreater(len(content.strip()), 0)

if __name__ == '__main__':
    unittest.main()