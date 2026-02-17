import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Mock dotenv before importing config to prevent loading actual .env
mock_dotenv = MagicMock()
sys.modules["dotenv"] = mock_dotenv

# Set required environment variables before import to ensure Config() instantiation succeeds at module level
os.environ["GOOGLE_API_KEY"] = "test-key"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_RW_USER"] = "neo4j"
os.environ["NEO4J_RW_PASSWORD"] = "password"
os.environ["NEO4J_RO_USER"] = "reader"
os.environ["NEO4J_RO_PASSWORD"] = "reader_pass"

from config import Config, ConfigurationError, config as global_config

class TestConfig(unittest.TestCase):
    """Test suite for configuration management."""

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

    def test_init_happy_path(self):
        """Test successful initialization with all required variables."""
        with patch.dict(os.environ, self.required_env, clear=True):
            config = Config()
            self.assertEqual(config.google_api_key, "test-key")
            self.assertEqual(config.neo4j_uri, "bolt://localhost:7687")

    def test_missing_required_vars(self):
        """Test that ConfigurationError is raised when required variables are missing."""
        # Test missing all variables
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError) as cm:
                Config()
            self.assertIn("Missing required environment variables", str(cm.exception))

        # Test missing one variable
        incomplete_env = self.required_env.copy()
        del incomplete_env["GOOGLE_API_KEY"]
        with patch.dict(os.environ, incomplete_env, clear=True):
            with self.assertRaises(ConfigurationError) as cm:
                Config()
            self.assertIn("GOOGLE_API_KEY", str(cm.exception))

    def test_optional_vars_defaults(self):
        """Test that optional variables use default values."""
        with patch.dict(os.environ, self.required_env, clear=True):
            config = Config()
            # Check defaults
            self.assertEqual(config.chunk_size, 1000)
            self.assertEqual(config.chunk_overlap, 200)
            self.assertEqual(config.llm_temperature, 0.0)
            self.assertEqual(config.max_retries, 3)

    def test_type_conversion(self):
        """Test that environment variables are correctly converted to types."""
        custom_env = self.required_env.copy()
        custom_env.update({
            "CHUNK_SIZE": "500",
            "LLM_TEMPERATURE": "0.7",
            "MAX_RETRIES": "5"
        })

        with patch.dict(os.environ, custom_env, clear=True):
            config = Config()
            self.assertEqual(config.chunk_size, 500)
            self.assertIsInstance(config.chunk_size, int)
            self.assertEqual(config.llm_temperature, 0.7)
            self.assertIsInstance(config.llm_temperature, float)
            self.assertEqual(config.max_retries, 5)
            self.assertIsInstance(config.max_retries, int)

    def test_get_required_env_helper(self):
        """Test the internal helper for required env vars."""
        with patch.dict(os.environ, self.required_env, clear=True):
            config = Config()

        # Now patch os.environ for the method call
        with patch.dict(os.environ, {"TEST_VAR": "value"}, clear=True):
            self.assertEqual(config._get_required_env("TEST_VAR"), "value")

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                config._get_required_env("MISSING_VAR")

    def test_get_optional_env_helper(self):
        """Test the internal helper for optional env vars."""
        with patch.dict(os.environ, self.required_env, clear=True):
            config = Config()

        with patch.dict(os.environ, {"TEST_VAR": "value"}, clear=True):
            self.assertEqual(config._get_optional_env("TEST_VAR", "default"), "value")

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(config._get_optional_env("MISSING_VAR", "default"), "default")

    def test_allowed_origins_default(self):
        """Test default allowed origins when environment variable is not set."""
        # Ensure ALLOWED_ORIGINS is not set
        if "ALLOWED_ORIGINS" in os.environ:
            del os.environ["ALLOWED_ORIGINS"]

        # allowed_origins property reads env var dynamically
        origins = global_config.allowed_origins
        self.assertIn("http://localhost:5173", origins)
        self.assertEqual(len(origins), 4)

    def test_allowed_origins_override(self):
        """Test allowed origins override via environment variable."""
        # Set env var
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "http://foo.com,http://bar.com"}):
            origins = global_config.allowed_origins
            self.assertEqual(origins, ["http://foo.com", "http://bar.com"])

if __name__ == "__main__":
    unittest.main()
