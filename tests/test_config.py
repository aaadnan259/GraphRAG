
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
    def setUp(self):
        """Set up test environment with minimal required variables."""
        self.required_env = {
            "GOOGLE_API_KEY": "test-key",
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_RW_USER": "neo4j",
            "NEO4J_RW_PASSWORD": "password",
            "NEO4J_RO_USER": "reader",
            "NEO4J_RO_PASSWORD": "reader_pass"
        }

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

    def test_max_file_size_default(self):
        """Test default max file size."""
        with patch.dict(os.environ, self.required_env, clear=True):
            config = Config()
            self.assertEqual(config.max_file_size, 10 * 1024 * 1024)

    def test_max_file_size_override(self):
        """Test max file size override via environment variable."""
        with patch.dict(os.environ, {"MAX_FILE_SIZE": "5242880"}, clear=True):
             # We need to re-instantiate or patch because Config() reads env during init/property access
             # The property reads env var dynamically, so patch.dict is enough if we use a new instance or if logic supports it.
             # In this case, creating a new instance is safer given the test setup.
             with patch.dict(os.environ, self.required_env, clear=True): # Ensure required vars exist
                 with patch.dict(os.environ, {"MAX_FILE_SIZE": "5242880"}):
                    config = Config()
                    self.assertEqual(config.max_file_size, 5242880)

if __name__ == "__main__":
    unittest.main()
