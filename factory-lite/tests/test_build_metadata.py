"""Test build metadata."""

import unittest

class TestBuildMetadata(unittest.TestCase):
    def test_main_py_has_git_sha(self):
        """Test that main.py has GIT_SHA variable"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('GIT_SHA', content)
        
    def test_main_py_has_app_version(self):
        """Test that main.py has APP_VERSION variable"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('APP_VERSION', content)
        
    def test_main_py_has_service_name(self):
        """Test that main.py has SERVICE_NAME variable"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('SERVICE_NAME', content)
        
    def test_main_py_has_mode(self):
        """Test that main.py has MODE variable"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('MODE', content)

if __name__ == '__main__':
    unittest.main()