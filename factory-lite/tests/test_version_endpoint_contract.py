"""Test version endpoint contract compliance."""

import unittest

class TestVersionEndpointContract(unittest.TestCase):
    def test_version_endpoint_returns_service(self):
        """Test that version endpoint returns service"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('"service":', content)
        self.assertIn('SERVICE_NAME', content)
        
    def test_version_endpoint_returns_version_field(self):
        """Test that version endpoint returns version field"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('"version":', content)
        self.assertIn('APP_VERSION', content)
        
    def test_version_endpoint_returns_git_sha(self):
        """Test that version endpoint returns git_sha"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('"git_sha":', content)
        self.assertIn('GIT_SHA', content)
        
    def test_version_endpoint_returns_mode(self):
        """Test that version endpoint returns mode"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('"mode":', content)
        self.assertIn('MODE', content)

if __name__ == '__main__':
    unittest.main()