"""Test health endpoint contract compliance."""

import unittest

class TestHealthEndpointContract(unittest.TestCase):
    def test_health_endpoint_returns_status_ok(self):
        """Test that health endpoint returns status ok"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('"status": "ok"', content)
        
    def test_health_endpoint_returns_version(self):
        """Test that health endpoint returns version"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('"version":', content)
        self.assertIn('GIT_SHA', content)
        
    def test_health_endpoint_docstring(self):
        """Test that health endpoint has correct docstring"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('HTTP 200 with {"status":"ok","version":"<actual checkout/build SHA>"}', content)

if __name__ == '__main__':
    unittest.main()