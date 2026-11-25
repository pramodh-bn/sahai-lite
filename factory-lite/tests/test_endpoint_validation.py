"""Test endpoint validation."""

import unittest

class TestEndpointValidation(unittest.TestCase):
    def test_health_endpoint_method(self):
        """Test that health endpoint uses GET method"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('@app.get("/health")', content)
        
    def test_version_endpoint_method(self):
        """Test that version endpoint uses GET method"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('@app.get("/version")', content)
        
    def test_endpoints_have_documentation(self):
        """Test that endpoints have documentation"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        # Check that both endpoints have docstrings
        self.assertIn('"""Health endpoint', content)
        self.assertIn('"""Version endpoint', content)

if __name__ == '__main__':
    unittest.main()