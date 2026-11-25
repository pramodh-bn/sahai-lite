"""Test container identity verification."""

import unittest

class TestContainerIdentity(unittest.TestCase):
    def test_run_md_verifies_container_identity(self):
        """Test that RUN.md verifies container identity"""
        with open('stage-01/RUN.md', 'r') as f:
            content = f.read()
        self.assertIn('Verify exact container identity', content)
        self.assertIn('docker inspect', content)
        
    def test_container_name_pattern(self):
        """Test that container uses specific naming pattern"""
        with open('stage-01/RUN.md', 'r') as f:
            content = f.read()
        self.assertIn('CONTAINER_NAME', content)
        self.assertIn('sah-harness', content)
        
    def test_running_state_verification(self):
        """Test that running state is verified"""
        with open('stage-01/RUN.md', 'r') as f:
            content = f.read()
        self.assertIn('running', content)
        self.assertIn('State.Status', content)

if __name__ == '__main__':
    unittest.main()