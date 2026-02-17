
import sys
import unittest
from unittest.mock import MagicMock, patch
import os

# Mock all dependencies
mock_fastapi = MagicMock()
mock_fastapi_app = MagicMock()
mock_fastapi.FastAPI.return_value = mock_fastapi_app
sys.modules["fastapi"] = mock_fastapi
sys.modules["fastapi.middleware.cors"] = MagicMock()

sys.modules["pydantic"] = MagicMock()
sys.modules["ingest"] = MagicMock()
sys.modules["retriever"] = MagicMock()
sys.modules["models"] = MagicMock()
sys.modules["dotenv"] = MagicMock()

# Set env vars at module level so config.py can be imported by conftest fixture
os.environ["GOOGLE_API_KEY"] = "dummy"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_RW_USER"] = "neo4j"
os.environ["NEO4J_RW_PASSWORD"] = "password"
os.environ["NEO4J_RO_USER"] = "neo4j_ro"
os.environ["NEO4J_RO_PASSWORD"] = "password"

class TestApiCors(unittest.TestCase):
    def test_cors_middleware_added(self):
        # Set ALLOWED_ORIGINS to verify it is passed to middleware
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY": "dummy",
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_RW_USER": "neo4j",
            "NEO4J_RW_PASSWORD": "password",
            "NEO4J_RO_USER": "neo4j_ro",
            "NEO4J_RO_PASSWORD": "password",
            "ALLOWED_ORIGINS": "http://mock-origin.com"
        }):
            # Force reload of api and config to pick up env vars
            if "api" in sys.modules:
                del sys.modules["api"]
            if "config" in sys.modules:
                del sys.modules["config"]

            import api

            # Verify add_middleware was called
            # api.app is the mock_fastapi_app
            self.assertTrue(api.app.add_middleware.called)

            # Check arguments
            # args[0] might be CORSMiddleware class
            # kwargs should contain allow_origins
            args, kwargs = api.app.add_middleware.call_args

            # Check that allow_origins is passed and correct
            self.assertIn('allow_origins', kwargs)
            self.assertEqual(kwargs['allow_origins'], ['http://mock-origin.com'])

if __name__ == "__main__":
    unittest.main()
