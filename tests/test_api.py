import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from api import app, get_retriever
from models import QueryRequest, QueryResponse

# Use raise_server_exceptions=False so that the global exception handler runs and returns JSON responses for 500s.
client = TestClient(app, raise_server_exceptions=False)

def test_root():
    """Test health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "GraphRAG API"}

def test_query_knowledge_graph():
    """Test knowledge graph query endpoint."""
    # Mock retrieve method
    mock_instance = MagicMock()
    mock_instance.retrieve = AsyncMock(return_value=QueryResponse(
        answer="This is a test answer.",
        vector_context=["Context 1"],
        graph_context="Graph Context",
        sources=["Vector Search", "Knowledge Graph"]
    ))

    # Override dependency
    app.dependency_overrides[get_retriever] = lambda: mock_instance

    try:
        request_data = {
            "query": "What is GraphRAG?",
            "use_vector_search": True,
            "use_graph_search": True
        }

        response = client.post("/query", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "This is a test answer."
        assert data["vector_context"] == ["Context 1"]
        assert data["graph_context"] == "Graph Context"
        assert data["sources"] == ["Vector Search", "Knowledge Graph"]

        mock_instance.retrieve.assert_awaited_once()

    finally:
        app.dependency_overrides = {}

def test_query_knowledge_graph_failure():
    """Test knowledge graph query endpoint failure."""
    # Mock retrieve method to raise an exception
    mock_instance = MagicMock()
    mock_instance.retrieve = AsyncMock(side_effect=Exception("Retriever error"))

    app.dependency_overrides[get_retriever] = lambda: mock_instance

    try:
        request_data = {
            "query": "What is GraphRAG?",
            "use_vector_search": True,
            "use_graph_search": True
        }

        response = client.post("/query", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "An internal server error occurred."
    finally:
        app.dependency_overrides = {}

@patch("api.Ingestor")
def test_ingest_document(mock_ingestor):
    """Test document ingestion endpoint."""
    # Mock Ingestor methods
    mock_instance = mock_ingestor.return_value
    mock_instance.ingest = AsyncMock(return_value={
        "success": True,
        "document_id": "test-doc-id",
        "filename": "test.txt",
        "num_chunks": 5,
        "num_entities": 10,
        "num_relationships": 15
    })

    # Create a dummy file
    files = {"file": ("test.txt", b"This is a test document.", "text/plain")}

    response = client.post("/ingest", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["document_id"] == "test-doc-id"

    mock_instance.ingest.assert_awaited_once()

@patch("api.Ingestor")
def test_ingest_document_invalid_extension(mock_ingestor):
    """Test ingestion with invalid file extension."""
    files = {"file": ("test.pdf", b"PDF content", "application/pdf")}
    response = client.post("/ingest", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Only .txt and .md files are supported"

@patch("api.Ingestor")
def test_ingest_document_failure(mock_ingestor):
    """Test ingestion failure handling."""
    mock_instance = mock_ingestor.return_value
    mock_instance.ingest = AsyncMock(return_value={
        "success": False,
        "error": "Ingestion failed"
    })

    files = {"file": ("test.txt", b"This is a test document.", "text/plain")}
    response = client.post("/ingest", files=files)

    assert response.status_code == 500
    assert response.json()["detail"] == "Ingestion failed"

def test_get_graph_stats():
    """Test graph statistics endpoint."""
    mock_instance = MagicMock()
    mock_instance.get_graph_statistics = AsyncMock(return_value={
        "total_entities": 100,
        "total_relationships": 200,
        "entity_types": {"PERSON": 50},
        "relationship_types": {"WORKS_AT": 100}
    })

    app.dependency_overrides[get_retriever] = lambda: mock_instance

    try:
        response = client.get("/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_entities"] == 100
        assert data["total_relationships"] == 200
    finally:
        app.dependency_overrides = {}

def test_get_graph_stats_failure():
    """Test graph statistics endpoint failure."""
    mock_instance = MagicMock()
    mock_instance.get_graph_statistics = AsyncMock(side_effect=Exception("Database error"))

    app.dependency_overrides[get_retriever] = lambda: mock_instance

    try:
        response = client.get("/stats")

        assert response.status_code == 500
        assert response.json()["detail"] == "An internal server error occurred."
    finally:
        app.dependency_overrides = {}

@patch("api.HybridRetriever")
def test_get_graph_stats_failure(mock_hybrid_retriever):
    """Test graph statistics failure handling."""
    mock_instance = mock_hybrid_retriever.return_value
    mock_instance.get_graph_statistics = AsyncMock(side_effect=Exception("Database error"))

    response = client.get("/stats")

    assert response.status_code == 500
    assert response.json()["detail"] == "An internal server error occurred while fetching graph statistics."

def test_search_entities_success():
    """Test successful entity search."""
    mock_entities = [
        {"name": "Entity1", "type": "Type1", "description": "Desc1"},
        {"name": "Entity2", "type": "Type2", "description": "Desc2"}
    ]

    mock_instance = MagicMock()
    mock_instance.search_entities = AsyncMock(return_value=mock_entities)

    app.dependency_overrides[get_retriever] = lambda: mock_instance

    try:
        response = client.get("/search/entities?query=test")

        assert response.status_code == 200
        assert response.json() == {"entities": mock_entities}
        # Verify the method was called with expected arguments
        mock_instance.search_entities.assert_called_once_with("test", 10)
    finally:
        app.dependency_overrides = {}

def test_search_entities_limit():
    """Test entity search with custom limit."""
    mock_entities = [{"name": "Entity1"}]

    mock_instance = MagicMock()
    mock_instance.search_entities = AsyncMock(return_value=mock_entities)

    app.dependency_overrides[get_retriever] = lambda: mock_instance

    try:
        response = client.get("/search/entities?query=test&limit=5")

        assert response.status_code == 200
        # Check that the limit was passed correctly
        mock_instance.search_entities.assert_called_once_with("test", 5)
    finally:
        app.dependency_overrides = {}

def test_search_entities_failure():
    """Test entity search failure handling."""
    mock_instance = MagicMock()
    mock_instance.search_entities = AsyncMock(side_effect=Exception("Database error"))

    app.dependency_overrides[get_retriever] = lambda: mock_instance

    try:
        response = client.get("/search/entities?query=test")

        assert response.status_code == 500
        assert "An internal server error occurred" in response.json()["detail"]
    finally:
        app.dependency_overrides = {}
