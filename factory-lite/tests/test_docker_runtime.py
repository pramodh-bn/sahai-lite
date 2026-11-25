"""Test Docker runtime characteristics."""

import unittest

class TestDockerRuntime(unittest.TestCase):
    def test_dockerfile_exposes_port(self):
        """Test that Dockerfile exposes port 8080"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('EXPOSE 8080', content)
        
    def test_dockerfile_sets_environment_variables(self):
        """Test that Dockerfile sets environment variables"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('ENV ', content)
        self.assertIn('PYTHONUNBUFFERED', content)
        
    def test_dockerfile_sets_working_directory(self):
        """Test that Dockerfile sets working directory"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('WORKDIR', content)
        self.assertIn('/app', content)

if __name__ == '__main__':
    unittest.main()