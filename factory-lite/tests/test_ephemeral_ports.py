"""Test ephemeral ports usage."""

import unittest

class TestEphemeralPorts(unittest.TestCase):
    def test_run_md_uses_ephemeral_ports(self):
        """Test that RUN.md uses ephemeral ports"""
        with open('stage-01/RUN.md', 'r') as f:
            content = f.read()
        self.assertIn('ephemeral', content)
        self.assertIn('127.0.0.1::8080', content)
        
    def test_docker_publish_uses_double_colon(self):
        """Test that docker run uses double colon for ephemeral ports"""
        with open('stage-01/RUN.md', 'r') as f:
            content = f.read()
        self.assertIn('127.0.0.1::8080', content)
        
    def test_port_binding_verification(self):
        """Test that port binding is verified"""
        with open('stage-01/RUN.md', 'r') as f:
            content = f.read()
        self.assertIn('docker port', content)

if __name__ == '__main__':
    unittest.main()