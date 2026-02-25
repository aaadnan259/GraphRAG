"""
Environment configuration and validation.
"""

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


class Config:
    """Centralized configuration with strict validation."""

    # Required Environment Variables
    ENV_GOOGLE_API_KEY = "GOOGLE_API_KEY"
    ENV_NEO4J_URI = "NEO4J_URI"
    ENV_NEO4J_RW_USER = "NEO4J_RW_USER"
    ENV_NEO4J_RW_PASSWORD = "NEO4J_RW_PASSWORD"
    ENV_NEO4J_RO_USER = "NEO4J_RO_USER"
    ENV_NEO4J_RO_PASSWORD = "NEO4J_RO_PASSWORD"

    REQUIRED_VARS = [
        ENV_GOOGLE_API_KEY,
        ENV_NEO4J_URI,
        ENV_NEO4J_RW_USER,
        ENV_NEO4J_RW_PASSWORD,
        ENV_NEO4J_RO_USER,
        ENV_NEO4J_RO_PASSWORD,
    ]

    def __init__(self):
        """Initialize and validate all required configuration."""
        self._validate_all()

        # Required
        self.google_api_key: str = self._get_required_env(self.ENV_GOOGLE_API_KEY)
        self.neo4j_uri: str = self._get_required_env(self.ENV_NEO4J_URI)
        self.neo4j_rw_user: str = self._get_required_env(self.ENV_NEO4J_RW_USER)
        self.neo4j_rw_password: str = self._get_required_env(self.ENV_NEO4J_RW_PASSWORD)
        self.neo4j_ro_user: str = self._get_required_env(self.ENV_NEO4J_RO_USER)
        self.neo4j_ro_password: str = self._get_required_env(self.ENV_NEO4J_RO_PASSWORD)

        # Optional
        self.chroma_persist_directory: str = self._get_optional_env("CHROMA_PERSIST_DIR", "./chroma_db")
        self.chunk_size: int = int(self._get_optional_env("CHUNK_SIZE", "1000"))
        self.chunk_overlap: int = int(self._get_optional_env("CHUNK_OVERLAP", "200"))
        self.embedding_model: str = self._get_optional_env("EMBEDDING_MODEL", "models/text-embedding-004")
        self.llm_model: str = self._get_optional_env("LLM_MODEL", "gemini-2.5-flash")
        self.llm_temperature: float = float(self._get_optional_env("LLM_TEMPERATURE", "0.0"))
        self.max_retries: int = int(self._get_optional_env("MAX_RETRIES", "3"))
        self.retry_min_wait: int = int(self._get_optional_env("RETRY_MIN_WAIT", "1"))
        self.retry_max_wait: int = int(self._get_optional_env("RETRY_MAX_WAIT", "10"))
        self.max_concurrent_llm_calls: int = int(self._get_optional_env("MAX_CONCURRENT_LLM_CALLS", "10"))
        self.vector_search_k: int = int(self._get_optional_env("VECTOR_SEARCH_K", "5"))
        self.max_file_size: int = int(self._get_optional_env("MAX_FILE_SIZE", str(10 * 1024 * 1024)))

        # Allowed origins
        origins = self._get_optional_env("ALLOWED_ORIGINS", "")
        if origins:
            self.allowed_origins: List[str] = [origin.strip() for origin in origins.split(",")]
        else:
            # Default to localhost origins if not set
            self.allowed_origins: List[str] = [
                "http://localhost:5173",  # Vite Dev Server
                "http://localhost:3000",  # Fallback React port
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000",
            ]

    def _get_required_env(self, key: str) -> str:
        """Fetch required environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise ConfigurationError(
                f"Missing required environment variable: {key}. "
                f"Please set it in your .env file or environment."
            )
        return value

    def _get_optional_env(self, key: str, default: str) -> str:
        """Fetch optional environment variable with default."""
        return os.getenv(key, default)

    def _validate_all(self):
        """Validate all required configuration on startup."""
        missing = []
        for var in self.REQUIRED_VARS:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please create a .env file with all required variables."
            )

config = Config()
