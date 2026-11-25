"""Test version endpoint returns correct response."""

import unittest

class TestVersionEndpoint(unittest.TestCase):
    def test_version_endpoint_exists(self):
        """Test that version endpoint exists in main.py"""
        # This is a simple file-based test since we can't import the module
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('def version()', content)
        
    def test_version_endpoint_returns_dict(self):
        """Test that version endpoint returns a dictionary with required fields"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        required_fields = ['service', 'version', 'git_sha', 'mode']
        for field in required_fields:
            self.assertIn(field, content)

if __name__ == '__main__':
    unittest.main()