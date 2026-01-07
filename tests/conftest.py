"""
Pytest configuration and fixtures for GraphRAG tests.
Provides mocks for OpenAI API, Neo4j driver, and ChromaDB to enable testing without live credentials.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import List, Dict, Any
import json


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for entity extraction."""
    def _create_response(entities: List[Dict], relationships: List[Dict]):
        response_data = {
            "entities": entities,
            "relationships": relationships
        }

        mock_response = Mock()
        mock_response.content = json.dumps(response_data)
        return mock_response

    return _create_response


@pytest.fixture
def mock_openai_ainvoke(mock_openai_response):
    """Mock async OpenAI invoke method."""
    async def _ainvoke(messages):
        # Default response with sample data
        entities = [
            {"name": "OpenAI", "type": "ORGANIZATION", "description": "AI company"},
            {"name": "GPT-4", "type": "PRODUCT", "description": "Language model"}
        ]
        relationships = [
            {"source": "OpenAI", "relation_type": "CREATED", "target": "GPT-4", "description": "developed the model"}
        ]
        return mock_openai_response(entities, relationships)

    return _ainvoke


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver with session context manager."""
    driver = MagicMock()
    session = MagicMock()

    # Mock session.run to track calls
    session.run = MagicMock(return_value=MagicMock())

    # Mock the session context manager
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=None)

    driver.session = MagicMock(return_value=session)
    driver.verify_connectivity = MagicMock()

    return driver


@pytest.fixture
def mock_neo4j_session():
    """Mock Neo4j session for direct testing."""
    session = MagicMock()

    # Mock query results
    result = MagicMock()
    result.single.return_value = {"count": 10}
    result.values.return_value = [("PERSON", 5), ("ORGANIZATION", 3)]

    session.run.return_value = result

    return session


@pytest.fixture
def mock_vectorstore():
    """Mock ChromaDB vector store."""
    vectorstore = MagicMock()

    # Mock similarity search
    mock_doc = Mock()
    mock_doc.page_content = "Sample document content"
    mock_doc.metadata = {"document_id": "test-doc", "chunk_index": 0}

    vectorstore.similarity_search.return_value = [mock_doc]
    vectorstore.add_documents = MagicMock()

    return vectorstore


@pytest.fixture
def mock_neo4j_graph():
    """Mock LangChain Neo4jGraph wrapper."""
    graph = MagicMock()
    graph.query = MagicMock(return_value=[])
    return graph


@pytest.fixture
def mock_cypher_chain():
    """Mock GraphCypherQAChain for retrieval testing."""
    chain = MagicMock()
    chain.invoke.return_value = {
        "result": "Mock graph result",
        "intermediate_steps": []
    }
    return chain


@pytest.fixture
def sample_entities():
    """Sample entities for testing."""
    return [
        {"name": "Alice", "type": "PERSON", "description": "Software engineer"},
        {"name": "TechCorp", "type": "ORGANIZATION", "description": "Technology company"},
        {"name": "San Francisco", "type": "LOCATION", "description": "City in California"}
    ]


@pytest.fixture
def sample_relationships():
    """Sample relationships for testing."""
    return [
        {"source": "Alice", "relation_type": "WORKS_AT", "target": "TechCorp", "description": "employee"},
        {"source": "TechCorp", "relation_type": "LOCATED_IN", "target": "San Francisco", "description": "headquarters"}
    ]


@pytest.fixture
def malicious_inputs():
    """Collection of malicious/injection attack strings."""
    return {
        "sql_injection": "'; DROP TABLE entities; --",
        "cypher_injection": "MATCH (n) DELETE n",
        "xss": "<script>alert('xss')</script>",
        "command_injection": "; rm -rf /",
        "unicode_attack": "А́LICE",  # Cyrillic A with combining accent
        "null_bytes": "Alice\x00Admin",
        "long_string": "A" * 10000,
        "special_chars": "!@#$%^&*(){}[]|\\:;\"'<>?/",
    }


@pytest.fixture
def edge_case_texts():
    """Edge case text inputs for chunking tests."""
    return {
        "empty": "",
        "whitespace_only": "   \n\n\t\t  ",
        "single_char": "a",
        "no_spaces": "a" * 1000,
        "massive_line": "word " * 10000,
        "markdown_headers": "# Header 1\n## Header 2\n### Header 3\nContent here.",
        "special_unicode": "Hello 世界 🌍 Привет مرحبا",
        "multiple_newlines": "\n\n\n\n\n",
    }


@pytest.fixture(autouse=True)
def mock_config():
    """Mock configuration to avoid loading .env file."""
    with patch('config.config') as mock_cfg:
        mock_cfg.openai_api_key = "test-key"
        mock_cfg.neo4j_uri = "bolt://localhost:7687"
        mock_cfg.neo4j_rw_user = "neo4j"
        mock_cfg.neo4j_rw_password = "password"
        mock_cfg.neo4j_ro_user = "reader"
        mock_cfg.neo4j_ro_password = "reader_pass"
        mock_cfg.llm_model = "gpt-4"
        mock_cfg.llm_temperature = 0.0
        mock_cfg.embedding_model = "text-embedding-3-small"
        mock_cfg.chunk_size = 1000
        mock_cfg.chunk_overlap = 200
        mock_cfg.vector_search_k = 5
        mock_cfg.max_concurrent_llm_calls = 5
        mock_cfg.retry_min_wait = 1
        mock_cfg.retry_max_wait = 10
        mock_cfg.chroma_persist_directory = "./test_chroma"
        yield mock_cfg
