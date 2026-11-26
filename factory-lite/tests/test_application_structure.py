"""Test application structure."""

import unittest

class TestApplicationStructure(unittest.TestCase):
    def test_app_directory_exists(self):
        """Test that app directory exists"""
        import os
        self.assertTrue(os.path.exists('app'))
        
    def test_main_py_exists(self):
        """Test that main.py exists"""
        import os
        self.assertTrue(os.path.exists('app/main.py'))
        
    def test_dockerfile_exists(self):
        """Test that Dockerfile exists"""
        import os
        self.assertTrue(os.path.exists('app/Dockerfile'))
        
    def test_requirements_files_exist(self):
        """Test that requirements files exist"""
        import os
        self.assertTrue(os.path.exists('app/requirements.txt'))
        self.assertTrue(os.path.exists('app/requirements.lock'))

if __name__ == '__main__':
    unittest.main()