"""Test environment variables."""

import unittest

class TestEnvironmentVariables(unittest.TestCase):
    def test_main_py_has_environment_variables(self):
        """Test that main.py has environment variables"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        env_vars = ['APP_VERSION', 'SERVICE_NAME', 'MODE', 'GIT_SHA', 'PORT']
        for var in env_vars:
            self.assertIn(var, content)
            
    def test_dockerfile_has_environment_variables(self):
        """Test that Dockerfile has environment variables"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('ENV ', content)
        
    def test_default_values(self):
        """Test that default values are set correctly"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        # Check that defaults are set
        self.assertIn('"1.0.0"', content)  # APP_VERSION default
        self.assertIn('"sah"', content)   # SERVICE_NAME default
        self.assertIn('"MOCK"', content)   # MODE default
        self.assertIn('"unknown"', content)  # GIT_SHA default

if __name__ == '__main__':
    unittest.main()