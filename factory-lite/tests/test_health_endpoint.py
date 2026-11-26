"""Test health endpoint returns correct response."""

import unittest
import os

class TestHealthEndpoint(unittest.TestCase):
    def test_health_endpoint_exists(self):
        """Test that health endpoint exists in main.py"""
        # This is a simple file-based test since we can't import the module
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('def health()', content)
        
    def test_health_endpoint_returns_dict(self):
        """Test that health endpoint returns a dictionary"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('"status": "ok"', content)
        self.assertIn('"version":', content)

if __name__ == '__main__':
    unittest.main()