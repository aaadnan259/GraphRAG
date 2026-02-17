from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from api import app
from models import QueryRequest, QueryResponse

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "GraphRAG API"}

@patch("api.HybridRetriever")
def test_query_knowledge_graph(mock_hybrid_retriever):
    # Mock retrieve method
    mock_instance = mock_hybrid_retriever.return_value
    mock_instance.retrieve = AsyncMock(return_value=QueryResponse(
        answer="This is a test answer.",
        vector_context=["Context 1"],
        graph_context="Graph Context",
        sources=["Vector Search", "Knowledge Graph"]
    ))

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

@patch("api.Ingestor")
def test_ingest_document(mock_ingestor):
    # Mock Ingestor methods
    mock_instance = mock_ingestor.return_value
    mock_instance.init_schema = MagicMock()
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

    mock_instance.init_schema.assert_called_once()
    mock_instance.ingest.assert_awaited_once()

@patch("api.Ingestor")
def test_ingest_document_invalid_extension(mock_ingestor):
    files = {"file": ("test.pdf", b"PDF content", "application/pdf")}
    response = client.post("/ingest", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Only .txt and .md files are supported"

@patch("api.Ingestor")
def test_ingest_document_failure(mock_ingestor):
    mock_instance = mock_ingestor.return_value
    mock_instance.init_schema = MagicMock()
    mock_instance.ingest = AsyncMock(return_value={
        "success": False,
        "error": "Ingestion failed"
    })

    files = {"file": ("test.txt", b"This is a test document.", "text/plain")}
    response = client.post("/ingest", files=files)

    assert response.status_code == 500
    assert response.json()["detail"] == "Ingestion failed"

@patch("api.HybridRetriever")
def test_get_graph_stats(mock_hybrid_retriever):
    mock_instance = mock_hybrid_retriever.return_value
    mock_instance.get_graph_statistics = AsyncMock(return_value={
        "total_entities": 100,
        "total_relationships": 200,
        "entity_types": {"PERSON": 50},
        "relationship_types": {"WORKS_AT": 100}
    })

    response = client.get("/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total_entities"] == 100
    assert data["total_relationships"] == 200

@patch("api.HybridRetriever")
def test_search_entities(mock_hybrid_retriever):
    mock_instance = mock_hybrid_retriever.return_value
    mock_instance.search_entities = AsyncMock(return_value=[
        {"name": "Alice", "type": "PERSON", "description": "Engineer"},
        {"name": "Bob", "type": "PERSON", "description": "Manager"}
    ])

    response = client.get("/search/entities?query=Alice")

    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]) == 2
    assert data["entities"][0]["name"] == "Alice"
