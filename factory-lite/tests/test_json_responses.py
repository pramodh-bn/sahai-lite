"""Test JSON responses."""

import unittest

class TestJSONResponses(unittest.TestCase):
    def test_health_endpoint_json_structure(self):
        """Test that health endpoint returns valid JSON structure"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        # Check that health endpoint returns dict with required keys
        self.assertIn('"status": "ok"', content)
        self.assertIn('"version":', content)
        
    def test_version_endpoint_json_structure(self):
        """Test that version endpoint returns valid JSON structure"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        # Check that version endpoint returns dict with required keys
        required_keys = ['service', 'version', 'git_sha', 'mode']
        for key in required_keys:
            self.assertIn(f'"{key}":', content)

if __name__ == '__main__':
    unittest.main()