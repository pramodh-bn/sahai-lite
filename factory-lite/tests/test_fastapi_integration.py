"""Test FastAPI integration."""

import unittest

class TestFastAPIIntegration(unittest.TestCase):
    def test_fastapi_app_instance(self):
        """Test that FastAPI app instance is created"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('FastAPI(', content)
        
    def test_fastapi_app_title(self):
        """Test that FastAPI app has title"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('title=', content)
        self.assertIn('SERVICE_NAME', content)
        
    def test_fastapi_app_version(self):
        """Test that FastAPI app has version"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('version=', content)
        self.assertIn('APP_VERSION', content)
        
    def test_fastapi_route_decorators(self):
        """Test that FastAPI route decorators are used"""
        with open('app/main.py', 'r') as f:
            content = f.read()
        self.assertIn('@app.get', content)

if __name__ == '__main__':
    unittest.main()