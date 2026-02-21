import sys
import unittest
from unittest.mock import patch
import os

# We no longer mock fastapi and other dependencies globally here
# to avoid polluting sys.modules for other tests in the suite.

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
            # Force reload of config and api to pick up env vars for testing purposes.
            # We must restore the original modules afterwards to avoid leakage.
            original_config = sys.modules.get("config")
            original_api = sys.modules.get("api")
            
            if "api" in sys.modules:
                del sys.modules["api"]
            if "config" in sys.modules:
                del sys.modules["config"]

            try:
                import api
                from fastapi.middleware.cors import CORSMiddleware
                
                # Verify CORSMiddleware is in user_middleware and has correct origins
                cors_middleware = next(
                    (m for m in api.app.user_middleware if m.cls == CORSMiddleware),
                    None
                )
                self.assertIsNotNone(cors_middleware, "CORSMiddleware should be added to the app")
                self.assertEqual(cors_middleware.kwargs['allow_origins'], ['http://mock-origin.com'])
            finally:
                # Restore original modules
                if original_config:
                    sys.modules["config"] = original_config
                if original_api:
                    sys.modules["api"] = original_api

if __name__ == "__main__":
    unittest.main()
