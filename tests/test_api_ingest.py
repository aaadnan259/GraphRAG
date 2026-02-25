import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from api import app

client = TestClient(app)

def test_ingest_txt_file_success():
    """Test successful ingestion of a .txt file."""
    with patch("api.Ingestor") as mock_ingestor_class:
        mock_ingestor = mock_ingestor_class.return_value
        mock_ingestor.ingest = AsyncMock(return_value={
            "success": True,
            "num_entities": 1,
            "num_relationships": 1,
            "filename": "test.txt",
            "document_id": "123"
        })

        file_content = b"This is a test content."
        files = {"file": ("test.txt", file_content, "text/plain")}

        response = client.post("/ingest", files=files)

        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_ingestor.ingest.assert_called_once()

def test_ingest_md_file_success():
    """Test successful ingestion of a .md file."""
    with patch("api.Ingestor") as mock_ingestor_class:
        mock_ingestor = mock_ingestor_class.return_value
        mock_ingestor.ingest = AsyncMock(return_value={
            "success": True,
            "num_entities": 1,
            "num_relationships": 1,
            "filename": "test.md",
            "document_id": "456"
        })

        file_content = b"# This is a markdown test"
        files = {"file": ("test.md", file_content, "text/markdown")}

        response = client.post("/ingest", files=files)

        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_ingestor.ingest.assert_called_once()

def test_ingest_invalid_extension():
    """Test ingestion with an unsupported file extension."""
    file_content = b"Some content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    response = client.post("/ingest", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only .txt and .md files are supported"

def test_ingest_no_init_schema_call():
    """Test that init_schema is NOT called during ingestion (optimization)."""
    with patch("api.Ingestor") as mock_ingestor_class:
        mock_ingestor = mock_ingestor_class.return_value
        mock_ingestor.ingest = AsyncMock(return_value={
            "success": True,
            "num_entities": 1,
            "num_relationships": 1,
            "filename": "test.txt",
            "document_id": "123"
        })
        # We need to ensure init_schema is mocked to track calls
        mock_ingestor.init_schema = MagicMock()

        file_content = b"This is a test content."
        files = {"file": ("test.txt", file_content, "text/plain")}

        response = client.post("/ingest", files=files)

        assert response.status_code == 200
        # Assert init_schema was NOT called
        mock_ingestor.init_schema.assert_not_called()

def test_ingest_no_extension():
    """Test ingestion with a file having no extension."""
    file_content = b"Some content"
    files = {"file": ("test", file_content, "text/plain")}

    response = client.post("/ingest", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only .txt and .md files are supported"

def test_ingest_nested_invalid_extension():
    """Test ingestion with a double extension where the last one is invalid."""
    file_content = b"Some content"
    files = {"file": ("test.txt.exe", file_content, "application/octet-stream")}

    response = client.post("/ingest", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only .txt and .md files are supported"
