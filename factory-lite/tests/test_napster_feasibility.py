"""Test napster feasibility document."""

import unittest

class TestNapsterFeasibility(unittest.TestCase):
    def test_napster_feasibility_exists(self):
        """Test that napster-feasibility.md exists"""
        import os
        self.assertTrue(os.path.exists('factory-lite/docs/napster-feasibility.md'))
        
    def test_napster_feasibility_has_capabilities(self):
        """Test that napster-feasibility.md has capabilities section"""
        with open('factory-lite/docs/napster-feasibility.md', 'r') as f:
            content = f.read()
        self.assertIn('Capabilities', content)
        self.assertIn('## Capabilities', content)
        
    def test_napster_feasibility_has_unknowns(self):
        """Test that napster-feasibility.md has unknowns section"""
        with open('factory-lite/docs/napster-feasibility.md', 'r') as f:
            content = f.read()
        self.assertIn('Unknowns', content)
        self.assertIn('## Unknowns', content)
        
    def test_napster_feasibility_has_evidence(self):
        """Test that napster-feasibility.md has evidence section"""
        with open('factory-lite/docs/napster-feasibility.md', 'r') as f:
            content = f.read()
        self.assertIn('Evidence', content)
        self.assertIn('## Evidence', content)

if __name__ == '__main__':
    unittest.main()