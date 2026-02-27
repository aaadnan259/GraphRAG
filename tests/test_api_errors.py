
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock dependencies before importing api
sys.modules["langchain"] = MagicMock()
sys.modules["langchain.text_splitter"] = MagicMock()
sys.modules["langchain.schema"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()
sys.modules["langchain.prompts"] = MagicMock()
sys.modules["langchain_community.graphs"] = MagicMock()
sys.modules["langchain.chains"] = MagicMock()
sys.modules["neo4j"] = MagicMock()
sys.modules["dotenv"] = MagicMock()
sys.modules["langchain_chroma"] = MagicMock()
sys.modules["tenacity"] = MagicMock()

# Mock Config to avoid environment variable errors
mock_config = MagicMock()
mock_config.allowed_origins = ["*"]
mock_config.max_file_size = 10 * 1024 * 1024
sys.modules["config"] = MagicMock()
sys.modules["config"].config = mock_config

# Now import api
from api import app
from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=False)

def test_query_exception_handling():
    """Test that unexpected exceptions in /query are handled gracefully."""
    with patch("api.HybridRetriever") as MockRetriever:
        instance = MockRetriever.return_value
        instance.retrieve = AsyncMock(side_effect=Exception("Database connection failed"))

        response = client.post("/query", json={"query": "test query"})

        # Verify it returns 500 (internal server error)
        assert response.status_code == 500
        assert response.json()["detail"] == "An internal server error occurred."

def test_ingest_exception_handling():
    """Test that unexpected exceptions in /ingest are handled gracefully."""
    with patch("api.Ingestor") as MockIngestor:
        instance = MockIngestor.return_value
        # Mocking ingest to fail
        instance.ingest = AsyncMock(side_effect=Exception("Ingestion crashed"))
        instance.init_schema = MagicMock()

        files = {"file": ("test.txt", b"content", "text/plain")}
        response = client.post("/ingest", files=files)

        assert response.status_code == 500
        assert response.json()["detail"] == "An internal server error occurred."

def test_stats_exception_handling():
    """Test that unexpected exceptions in /stats are handled gracefully."""
    with patch("api.HybridRetriever") as MockRetriever:
        instance = MockRetriever.return_value
        instance.get_graph_statistics = AsyncMock(side_effect=Exception("Stats failed"))

        response = client.get("/stats")

        assert response.status_code == 500
        assert response.json()["detail"] == "An internal server error occurred."

def test_search_entities_exception_handling():
    """Test that unexpected exceptions in /search/entities are handled gracefully."""
    with patch("api.HybridRetriever") as MockRetriever:
        instance = MockRetriever.return_value
        instance.search_entities = AsyncMock(side_effect=Exception("Search failed"))

        response = client.get("/search/entities?query=test")

        assert response.status_code == 500
        assert response.json()["detail"] == "An internal server error occurred."

def test_http_exception_preservation():
    """Test that HTTPExceptions (e.g. 400) are preserved."""
    # This specifically tests that existing validation logic in /ingest works
    # We pass a PDF file which should trigger a 400
    files = {"file": ("test.pdf", b"content", "application/pdf")}
    response = client.post("/ingest", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only .txt and .md files are supported"
