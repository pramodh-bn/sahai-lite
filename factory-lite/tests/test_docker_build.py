"""Test Docker build process."""

import unittest

class TestDockerBuild(unittest.TestCase):
    def test_dockerfile_has_from_instruction(self):
        """Test that Dockerfile has FROM instruction"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('FROM ', content)
        
    def test_dockerfile_has_workdir_instruction(self):
        """Test that Dockerfile has WORKDIR instruction"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('WORKDIR ', content)
        
    def test_dockerfile_has_copy_instructions(self):
        """Test that Dockerfile has COPY instructions"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('COPY ', content)
        
    def test_dockerfile_has_cmd_instruction(self):
        """Test that Dockerfile has CMD instruction"""
        with open('app/Dockerfile', 'r') as f:
            content = f.read()
        self.assertIn('CMD ', content)

if __name__ == '__main__':
    unittest.main()