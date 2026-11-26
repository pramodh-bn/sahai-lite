"""Test file permissions."""

import unittest

class TestFilePermissions(unittest.TestCase):
    def test_main_py_readable(self):
        """Test that main.py is readable"""
        import os
        self.assertTrue(os.access('app/main.py', os.R_OK))
        
    def test_dockerfile_readable(self):
        """Test that Dockerfile is readable"""
        import os
        self.assertTrue(os.access('app/Dockerfile', os.R_OK))
        
    def test_requirements_txt_readable(self):
        """Test that requirements.txt is readable"""
        import os
        self.assertTrue(os.access('app/requirements.txt', os.R_OK))
        
    def test_requirements_lock_readable(self):
        """Test that requirements.lock is readable"""
        import os
        self.assertTrue(os.access('app/requirements.lock', os.R_OK))

if __name__ == '__main__':
    unittest.main()