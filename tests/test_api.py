
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_search_entities_success():
    """Test successful entity search."""
    mock_entities = [
        {"name": "Entity1", "type": "Type1", "description": "Desc1"},
        {"name": "Entity2", "type": "Type2", "description": "Desc2"}
    ]

    with patch("api.HybridRetriever") as MockRetriever:
        mock_instance = MockRetriever.return_value
        # Configure the async method on the mock instance
        mock_instance.search_entities = AsyncMock(return_value=mock_entities)

        response = client.get("/search/entities?query=test")

        assert response.status_code == 200
        assert response.json() == {"entities": mock_entities}
        # Verify the method was called with expected arguments
        mock_instance.search_entities.assert_called_once_with("test", 10)

def test_search_entities_limit():
    """Test entity search with custom limit."""
    mock_entities = [{"name": "Entity1"}]

    with patch("api.HybridRetriever") as MockRetriever:
        mock_instance = MockRetriever.return_value
        mock_instance.search_entities = AsyncMock(return_value=mock_entities)

        response = client.get("/search/entities?query=test&limit=5")

        assert response.status_code == 200
        # Check that the limit was passed correctly
        mock_instance.search_entities.assert_called_once_with("test", 5)

def test_search_entities_failure():
    """Test entity search failure handling."""
    with patch("api.HybridRetriever") as MockRetriever:
        mock_instance = MockRetriever.return_value
        mock_instance.search_entities = AsyncMock(side_effect=Exception("Database error"))

        response = client.get("/search/entities?query=test")

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]
