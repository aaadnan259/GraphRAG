
import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Mock dotenv before importing config
mock_dotenv = MagicMock()
sys.modules["dotenv"] = mock_dotenv

# Set env vars BEFORE import so Config() instantiation succeeds
os.environ["GOOGLE_API_KEY"] = "dummy"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_RW_USER"] = "neo4j"
os.environ["NEO4J_RW_PASSWORD"] = "password"
os.environ["NEO4J_RO_USER"] = "neo4j_ro"
os.environ["NEO4J_RO_PASSWORD"] = "password"

# Ensure ALLOWED_ORIGINS is NOT set initially
if "ALLOWED_ORIGINS" in os.environ:
    del os.environ["ALLOWED_ORIGINS"]

from config import Config, config as global_config

class TestConfig(unittest.TestCase):
    def test_allowed_origins_default(self):
        # Ensure ALLOWED_ORIGINS is not set
        if "ALLOWED_ORIGINS" in os.environ:
            del os.environ["ALLOWED_ORIGINS"]

        # allowed_origins property reads env var dynamically
        origins = global_config.allowed_origins
        self.assertIn("http://localhost:5173", origins)
        self.assertEqual(len(origins), 4)

    def test_allowed_origins_override(self):
        # Set env var
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "http://foo.com,http://bar.com"}):
            origins = global_config.allowed_origins
            self.assertEqual(origins, ["http://foo.com", "http://bar.com"])

if __name__ == "__main__":
    unittest.main()
