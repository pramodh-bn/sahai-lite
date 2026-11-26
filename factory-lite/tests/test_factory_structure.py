"""Test factory structure."""

import unittest

class TestFactoryStructure(unittest.TestCase):
    def test_factory_lite_directory_exists(self):
        """Test that factory-lite directory exists"""
        import os
        self.assertTrue(os.path.exists('factory-lite'))
        
    def test_tests_directory_exists(self):
        """Test that tests directory exists"""
        import os
        self.assertTrue(os.path.exists('factory-lite/tests'))
        
    def test_docs_directory_exists(self):
        """Test that docs directory exists"""
        import os
        self.assertTrue(os.path.exists('factory-lite/docs'))
        
    def test_napster_feasibility_file_exists(self):
        """Test that napster-feasibility.md exists"""
        import os
        self.assertTrue(os.path.exists('factory-lite/docs/napster-feasibility.md'))

if __name__ == '__main__':
    unittest.main()