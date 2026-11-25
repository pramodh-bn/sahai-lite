"""Test RUN.md file."""

import unittest

class TestRunMD(unittest.TestCase):
    def test_run_md_exists(self):
        """Test that RUN.md exists"""
        import os
        self.assertTrue(os.path.exists('stage-01/RUN.md'))
        
    def test_run_md_has_docker_commands(self):
        """Test that RUN.md has docker commands"""
        with open('stage-01/RUN.md', 'r') as f:
            content = f.read()
        self.assertIn('docker build', content)
        self.assertIn('docker run', content)
        
    def test_run_md_has_health_check(self):
        """Test that RUN.md has health check"""
        with open('stage-01/RUN.md', 'r') as f:
            content = f.read()
        self.assertIn('/health', content)
        
    def test_run_md_has_version_check(self):
        """Test that RUN.md has version check"""
        with open('stage-01/RUN.md', 'r') as f:
            content = f.read()
        self.assertIn('/version', content)

if __name__ == '__main__':
    unittest.main()