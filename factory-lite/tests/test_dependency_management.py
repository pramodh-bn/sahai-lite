"""Test dependency management."""

import unittest

class TestDependencyManagement(unittest.TestCase):
    def test_requirements_lock_not_empty(self):
        """Test that requirements.lock is not empty"""
        with open('app/requirements.lock', 'r') as f:
            content = f.read()
        self.assertGreater(len(content.strip()), 0)
        
    def test_requirements_lock_different_from_txt(self):
        """Test that requirements.lock is different from requirements.txt"""
        with open('app/requirements.txt', 'r') as f:
            txt_content = f.read()
        with open('app/requirements.lock', 'r') as f:
            lock_content = f.read()
        # Lock file should be longer due to comments
        self.assertGreater(len(lock_content), len(txt_content))
        
    def test_requirements_lock_has_comments(self):
        """Test that requirements.lock has comments"""
        with open('app/requirements.lock', 'r') as f:
            content = f.read()
        self.assertIn('#', content)

if __name__ == '__main__':
    unittest.main()