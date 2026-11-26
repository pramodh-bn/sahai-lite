"""Test requirements files."""

import unittest

class TestRequirements(unittest.TestCase):
    def test_requirements_txt_exists(self):
        """Test that requirements.txt exists"""
        import os
        self.assertTrue(os.path.exists('app/requirements.txt'))
        
    def test_requirements_lock_exists(self):
        """Test that requirements.lock exists"""
        import os
        self.assertTrue(os.path.exists('app/requirements.lock'))
        
    def test_requirements_txt_has_fastapi(self):
        """Test that requirements.txt has fastapi"""
        with open('app/requirements.txt', 'r') as f:
            content = f.read()
        self.assertIn('fastapi', content)
        
    def test_requirements_txt_has_uvicorn(self):
        """Test that requirements.txt has uvicorn"""
        with open('app/requirements.txt', 'r') as f:
            content = f.read()
        self.assertIn('uvicorn', content)

if __name__ == '__main__':
    unittest.main()