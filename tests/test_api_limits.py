
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

# Mock environment variables before importing api/config if possible,
# but for existing config instance, we can rely on property reading env var.
# We still need to satisfy the required env vars for Config validation during import.
os.environ.setdefault("GOOGLE_API_KEY", "dummy")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_RW_USER", "neo4j")
os.environ.setdefault("NEO4J_RW_PASSWORD", "password")
os.environ.setdefault("NEO4J_RO_USER", "neo4j_ro")
os.environ.setdefault("NEO4J_RO_PASSWORD", "password")

from api import app
from config import config

client = TestClient(app)

class TestFileUploadLimits:

    def test_file_too_large(self):
        """Test that files exceeding MAX_FILE_SIZE are rejected with 413."""
        limit = 1024  # 1KB

        # Patch the config attribute directly
        with patch.object(config, "max_file_size", limit):
            large_content = b"a" * (limit + 100)
            filename = "large_file.txt"

            with patch("api.Ingestor") as MockIngestor:
                mock_ingestor_instance = MockIngestor.return_value
                
                async def mock_ingest(data_iterator, filename):
                    try:
                        async for _ in data_iterator:
                            pass
                    except ValueError as e:
                        return {"success": False, "error": str(e), "document_id": "mock_id", "filename": filename}
                    return {"success": True}
                    
                mock_ingestor_instance.ingest = AsyncMock(side_effect=mock_ingest)

                response = client.post(
                    "/ingest",
                    files={"file": (filename, large_content, "text/plain")}
                )

                assert response.status_code == 413
                assert "File too large" in response.json()["detail"]

    def test_file_within_limit(self):
        """Test that files within MAX_FILE_SIZE are accepted."""
        limit = 1024  # 1KB

        with patch.object(config, "max_file_size", limit):
            small_content = b"a" * (limit - 100)
            filename_small = "small_file.txt"

            with patch("api.Ingestor") as MockIngestor:
                mock_ingestor_instance = MockIngestor.return_value
                mock_ingestor_instance.ingest = AsyncMock(return_value={"success": True})

                response = client.post(
                    "/ingest",
                    files={"file": (filename_small, small_content, "text/plain")}
                )

                assert response.status_code == 200
                assert response.json()["success"] is True

    def test_default_limit(self):
        """Test that the default limit is enforced (10MB)."""
        # Explicitly set to default to ensure test stability regardless of actual env
        default_limit = 10 * 1024 * 1024

        with patch.object(config, "max_file_size", default_limit):
            limit = config.max_file_size
            # Use a size that exceeds the default limit
            large_content = b"a" * (limit + 1024 * 1024) # 11MB
            filename = "large_file.txt"

            with patch("api.Ingestor") as MockIngestor:
                mock_ingestor_instance = MockIngestor.return_value
                
                async def mock_ingest(data_iterator, filename):
                    try:
                        async for _ in data_iterator:
                            pass
                    except ValueError as e:
                        return {"success": False, "error": str(e), "document_id": "mock_id", "filename": filename}
                    return {"success": True}
                    
                mock_ingestor_instance.ingest = AsyncMock(side_effect=mock_ingest)

                response = client.post(
                    "/ingest",
                    files={"file": (filename, large_content, "text/plain")}
                )

                assert response.status_code == 413
