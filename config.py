"""
Environment configuration and validation.
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


class Config:
    """Centralized configuration with strict validation."""

    def __init__(self):
        """Initialize and validate all required configuration."""
        self._validate_all()

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
        required_vars = [
            "GOOGLE_API_KEY",
            "NEO4J_URI",
            "NEO4J_RW_USER",
            "NEO4J_RW_PASSWORD",
            "NEO4J_RO_USER",
            "NEO4J_RO_PASSWORD"
        ]

        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please create a .env file with all required variables."
            )

    @property
    def google_api_key(self) -> str:
        """Google API key for Gemini LLM operations."""
        return self._get_required_env("GOOGLE_API_KEY")

    @property
    def neo4j_uri(self) -> str:
        """Neo4j database URI."""
        return self._get_required_env("NEO4J_URI")

    @property
    def neo4j_rw_user(self) -> str:
        """Neo4j read-write user (for ingestion)."""
        return self._get_required_env("NEO4J_RW_USER")

    @property
    def neo4j_rw_password(self) -> str:
        """Neo4j read-write password."""
        return self._get_required_env("NEO4J_RW_PASSWORD")

    @property
    def neo4j_ro_user(self) -> str:
        """Neo4j read-only user (for retrieval)."""
        return self._get_required_env("NEO4J_RO_USER")

    @property
    def neo4j_ro_password(self) -> str:
        """Neo4j read-only password."""
        return self._get_required_env("NEO4J_RO_PASSWORD")

    @property
    def chroma_persist_directory(self) -> str:
        """ChromaDB persistence directory."""
        return self._get_optional_env("CHROMA_PERSIST_DIR", "./chroma_db")

    @property
    def chunk_size(self) -> int:
        """Text chunk size for splitting."""
        return int(self._get_optional_env("CHUNK_SIZE", "1000"))

    @property
    def chunk_overlap(self) -> int:
        """Text chunk overlap."""
        return int(self._get_optional_env("CHUNK_OVERLAP", "200"))

    @property
    def embedding_model(self) -> str:
        """Google embedding model."""
        return self._get_optional_env("EMBEDDING_MODEL", "models/text-embedding-004")

    @property
    def llm_model(self) -> str:
        """Google Gemini LLM model."""
        return self._get_optional_env("LLM_MODEL", "gemini-2.5-flash")

    @property
    def llm_temperature(self) -> float:
        """LLM temperature setting."""
        return float(self._get_optional_env("LLM_TEMPERATURE", "0.0"))

    @property
    def max_retries(self) -> int:
        """Maximum retry attempts for API calls."""
        return int(self._get_optional_env("MAX_RETRIES", "3"))

    @property
    def retry_min_wait(self) -> int:
        """Minimum wait time between retries (seconds)."""
        return int(self._get_optional_env("RETRY_MIN_WAIT", "1"))

    @property
    def retry_max_wait(self) -> int:
        """Maximum wait time between retries (seconds)."""
        return int(self._get_optional_env("RETRY_MAX_WAIT", "10"))

    @property
    def max_concurrent_llm_calls(self) -> int:
        """Maximum concurrent LLM API calls."""
        return int(self._get_optional_env("MAX_CONCURRENT_LLM_CALLS", "10"))

    @property
    def vector_search_k(self) -> int:
        """Number of vector search results to retrieve."""
        return int(self._get_optional_env("VECTOR_SEARCH_K", "5"))


config = Config()
