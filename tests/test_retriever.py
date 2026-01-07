"""
Test suite for retrieval engine (retriever.py).
Tests security, read-only access, fallback mechanisms, and Cypher injection protection.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch

from retriever import HybridRetriever, query_graphrag
from models import QueryRequest, QueryResponse


class TestReadOnlyAccess:
    """Test that retriever uses read-only database connections."""

    @pytest.fixture
    def retriever(self, mock_neo4j_driver, mock_vectorstore):
        """Create retriever with mocked dependencies."""
        with patch('retriever.get_read_graph', return_value=mock_neo4j_driver) as mock_read, \
             patch('retriever.get_vectorstore', return_value=mock_vectorstore), \
             patch('retriever.ChatGoogleGenerativeAI'):

            retriever = HybridRetriever()
            # Store the mock for verification
            retriever._read_graph_mock = mock_read
            return retriever

    def test_uses_read_only_driver(self, retriever):
        """Verify that retriever requests READ-ONLY driver."""
        # Check that get_read_graph was called (not get_write_graph)
        assert retriever._read_graph_mock.called

    def test_read_driver_in_statistics(self, retriever, mock_neo4j_driver):
        """Test that statistics query uses read-only driver."""
        # Mock session results
        session = mock_neo4j_driver.session.return_value.__enter__.return_value
        session.run.return_value.single.return_value = {"count": 10}
        session.run.return_value.values.return_value = []

        stats = retriever.get_graph_statistics()

        # Verify the read driver was used
        assert mock_neo4j_driver.session.called

    def test_read_driver_in_entity_search(self, retriever, mock_neo4j_driver):
        """Test that entity search uses read-only driver."""
        session = mock_neo4j_driver.session.return_value.__enter__.return_value
        session.run.return_value = []

        results = retriever.search_entities("test")

        # Verify read driver session was created
        assert mock_neo4j_driver.session.called


class TestCypherInjectionProtection:
    """Test protection against Cypher injection attacks."""

    @pytest.fixture
    def retriever(self, mock_neo4j_driver, mock_vectorstore, mock_neo4j_graph):
        """Create retriever with mocked dependencies."""
        with patch('retriever.get_read_graph', return_value=mock_neo4j_driver), \
             patch('retriever.get_vectorstore', return_value=mock_vectorstore), \
             patch('retriever.ChatGoogleGenerativeAI'), \
             patch('retriever.Neo4jGraph', return_value=mock_neo4j_graph):

            retriever = HybridRetriever()
            return retriever

    @pytest.mark.asyncio
    async def test_cypher_chain_has_validate_cypher(self, retriever, mock_neo4j_graph):
        """Test that GraphCypherQAChain is initialized with validate_cypher=True."""
        with patch('retriever.GraphCypherQAChain.from_llm') as mock_chain_factory:
            mock_chain = Mock()
            mock_chain.invoke.return_value = {"result": "test result"}
            mock_chain_factory.return_value = mock_chain

            # Trigger graph search which creates the chain
            result = await retriever._graph_search("test query")

            # Verify that validate_cypher was passed
            mock_chain_factory.assert_called_once()
            call_kwargs = mock_chain_factory.call_args[1]

            assert 'validate_cypher' in call_kwargs, "validate_cypher parameter missing!"
            assert call_kwargs['validate_cypher'] is True, "validate_cypher should be True!"

    @pytest.mark.asyncio
    async def test_malicious_query_sanitization(self, retriever, malicious_inputs):
        """Test that malicious queries are sanitized before processing."""
        # Mock the graph search to return safely
        with patch.object(retriever, '_graph_search_sync', return_value="Safe result"):
            request = QueryRequest(query=malicious_inputs["cypher_injection"])

            # Verify the query is sanitized in QueryRequest
            assert "DELETE" not in request.query or "(" not in request.query

    @pytest.mark.asyncio
    async def test_query_with_injection_attempts(self, retriever, malicious_inputs):
        """Test retrieval with various injection attempts."""
        with patch.object(retriever, '_vector_search', return_value=[]), \
             patch.object(retriever, '_graph_search', return_value=""):

            for name, malicious_string in malicious_inputs.items():
                request = QueryRequest(query=malicious_string)
                response = await retriever.retrieve(request)

                # Should not crash and should return a response
                assert isinstance(response, QueryResponse)


class TestVectorSearch:
    """Test vector search functionality."""

    @pytest.fixture
    def retriever(self, mock_neo4j_driver, mock_vectorstore):
        """Create retriever with mocked dependencies."""
        with patch('retriever.get_read_graph', return_value=mock_neo4j_driver), \
             patch('retriever.get_vectorstore', return_value=mock_vectorstore), \
             patch('retriever.ChatGoogleGenerativeAI'):

            retriever = HybridRetriever()
            return retriever

    def test_vector_search_success(self, retriever, mock_vectorstore):
        """Test successful vector search."""
        query = "What is OpenAI?"

        results = retriever._vector_search(query)

        assert mock_vectorstore.similarity_search.called
        assert isinstance(results, list)

    def test_vector_search_with_k_parameter(self, retriever, mock_vectorstore):
        """Test vector search with custom k."""
        query = "Test query"
        k = 10

        retriever._vector_search(query, k=k)

        # Verify k was passed
        call_args = mock_vectorstore.similarity_search.call_args
        assert call_args[1]['k'] == k

    def test_vector_search_failure_raises(self, retriever, mock_vectorstore):
        """Test that vector search failures raise exceptions."""
        mock_vectorstore.similarity_search.side_effect = Exception("Vector DB error")

        with pytest.raises(Exception):
            retriever._vector_search("test query")


class TestGraphSearch:
    """Test graph search functionality."""

    @pytest.fixture
    def retriever(self, mock_neo4j_driver, mock_vectorstore, mock_neo4j_graph):
        """Create retriever with mocked dependencies."""
        with patch('retriever.get_read_graph', return_value=mock_neo4j_driver), \
             patch('retriever.get_vectorstore', return_value=mock_vectorstore), \
             patch('retriever.ChatGoogleGenerativeAI'), \
             patch('retriever.Neo4jGraph', return_value=mock_neo4j_graph):

            retriever = HybridRetriever()
            return retriever

    @pytest.mark.asyncio
    async def test_graph_search_success(self, retriever):
        """Test successful graph search."""
        with patch('retriever.GraphCypherQAChain.from_llm') as mock_chain_factory:
            mock_chain = Mock()
            mock_chain.invoke.return_value = {"result": "Graph result"}
            mock_chain_factory.return_value = mock_chain

            result = await retriever._graph_search("test query")

            assert result == "Graph result"
            assert mock_chain.invoke.called

    @pytest.mark.asyncio
    async def test_graph_search_uses_thread_pool(self, retriever):
        """Test that graph search offloads to thread pool."""
        # This test verifies the async wrapper calls the sync method
        with patch.object(retriever, '_graph_search_sync', return_value="Sync result") as mock_sync:
            result = await retriever._graph_search("test query")

            # The sync method should have been called via executor
            assert result == "Sync result"

    @pytest.mark.asyncio
    async def test_graph_search_failure_graceful(self, retriever):
        """Test that graph search failures are handled gracefully."""
        with patch('retriever.GraphCypherQAChain.from_llm') as mock_chain_factory:
            mock_chain_factory.side_effect = Exception("Neo4j connection failed")

            result = await retriever._graph_search("test query")

            # Should return error message, not raise
            assert "unavailable" in result.lower() or "error" in result.lower()


class TestGracefulDegradation:
    """Test system degrades gracefully when components fail."""

    @pytest.fixture
    def retriever(self, mock_neo4j_driver, mock_vectorstore):
        """Create retriever with mocked dependencies."""
        with patch('retriever.get_read_graph', return_value=mock_neo4j_driver), \
             patch('retriever.get_vectorstore', return_value=mock_vectorstore), \
             patch('retriever.ChatGoogleGenerativeAI') as mock_openai:

            mock_llm = AsyncMock()
            mock_response = Mock()
            mock_response.content = "Test answer"
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_llm

            retriever = HybridRetriever()
            return retriever

    @pytest.mark.asyncio
    async def test_vector_failure_returns_graph_only(self, retriever):
        """Test that if vector search fails, graph results are still returned."""
        request = QueryRequest(query="test query", use_vector_search=True, use_graph_search=True)

        # Mock vector failure, graph success
        with patch.object(retriever, '_vector_search', side_effect=Exception("Vector DB down")), \
             patch.object(retriever, '_graph_search', return_value="Graph data"):

            response = await retriever.retrieve(request)

            # Should still return answer with graph context only
            assert response.answer
            assert response.graph_context == "Graph data"
            assert response.vector_context == []

    @pytest.mark.asyncio
    async def test_graph_failure_returns_vector_only(self, retriever):
        """Test that if graph search fails, vector results are still returned."""
        request = QueryRequest(query="test query", use_vector_search=True, use_graph_search=True)

        # Mock graph failure, vector success
        with patch.object(retriever, '_vector_search', return_value=["Vector context"]), \
             patch.object(retriever, '_graph_search', side_effect=Exception("Graph DB down")):

            response = await retriever.retrieve(request)

            # Should still return answer with vector context only
            assert response.answer
            assert len(response.vector_context) == 1
            # Graph context should be empty or error message
            assert response.graph_context != "Graph data"

    @pytest.mark.asyncio
    async def test_both_sources_fail_returns_error(self, retriever):
        """Test that if both sources fail, appropriate error is returned."""
        request = QueryRequest(query="test query", use_vector_search=True, use_graph_search=True)

        # Mock both failures
        with patch.object(retriever, '_vector_search', side_effect=Exception("Vector DB down")), \
             patch.object(retriever, '_graph_search', side_effect=Exception("Graph DB down")):

            response = await retriever.retrieve(request)

            # Should return "no information" message
            assert "couldn't find" in response.answer.lower() or "no" in response.answer.lower()

    @pytest.mark.asyncio
    async def test_vector_only_mode(self, retriever):
        """Test retrieval with only vector search enabled."""
        request = QueryRequest(query="test query", use_vector_search=True, use_graph_search=False)

        with patch.object(retriever, '_vector_search', return_value=["Context"]), \
             patch.object(retriever, '_graph_search', side_effect=Exception("Should not be called")):

            response = await retriever.retrieve(request)

            # Should succeed with vector only
            assert response.answer
            assert len(response.vector_context) > 0
            assert response.graph_context == ""

    @pytest.mark.asyncio
    async def test_graph_only_mode(self, retriever):
        """Test retrieval with only graph search enabled."""
        request = QueryRequest(query="test query", use_vector_search=False, use_graph_search=True)

        with patch.object(retriever, '_vector_search', side_effect=Exception("Should not be called")), \
             patch.object(retriever, '_graph_search', return_value="Graph context"):

            response = await retriever.retrieve(request)

            # Should succeed with graph only
            assert response.answer
            assert response.vector_context == []
            assert response.graph_context == "Graph context"


class TestGraphStatistics:
    """Test graph statistics retrieval."""

    @pytest.fixture
    def retriever(self, mock_neo4j_driver, mock_vectorstore):
        """Create retriever with mocked dependencies."""
        with patch('retriever.get_read_graph', return_value=mock_neo4j_driver), \
             patch('retriever.get_vectorstore', return_value=mock_vectorstore), \
             patch('retriever.ChatGoogleGenerativeAI'):

            retriever = HybridRetriever()
            return retriever

    def test_get_statistics_success(self, retriever, mock_neo4j_driver):
        """Test successful statistics retrieval."""
        session = mock_neo4j_driver.session.return_value.__enter__.return_value

        # Mock entity count
        entity_result = Mock()
        entity_result.single.return_value = {"count": 100}

        # Mock relationship count
        rel_result = Mock()
        rel_result.single.return_value = {"count": 50}

        # Mock type queries
        type_result = Mock()
        type_result.values.return_value = [("PERSON", 30), ("ORGANIZATION", 20)]

        session.run.side_effect = [entity_result, rel_result, type_result, type_result]

        stats = retriever.get_graph_statistics()

        assert stats["total_entities"] == 100
        assert stats["total_relationships"] == 50
        assert "entity_types" in stats
        assert "relationship_types" in stats

    def test_get_statistics_failure(self, retriever, mock_neo4j_driver):
        """Test that statistics failures are handled gracefully."""
        session = mock_neo4j_driver.session.return_value.__enter__.return_value
        session.run.side_effect = Exception("Database connection failed")

        stats = retriever.get_graph_statistics()

        # Should return error stats instead of crashing
        assert "error" in stats
        assert stats["total_entities"] == 0
        assert stats["total_relationships"] == 0


class TestEntitySearch:
    """Test entity search functionality."""

    @pytest.fixture
    def retriever(self, mock_neo4j_driver, mock_vectorstore):
        """Create retriever with mocked dependencies."""
        with patch('retriever.get_read_graph', return_value=mock_neo4j_driver), \
             patch('retriever.get_vectorstore', return_value=mock_vectorstore), \
             patch('retriever.ChatGoogleGenerativeAI'):

            retriever = HybridRetriever()
            return retriever

    def test_search_entities_success(self, retriever, mock_neo4j_driver):
        """Test successful entity search."""
        session = mock_neo4j_driver.session.return_value.__enter__.return_value

        # Mock search results
        mock_record = {"name": "OpenAI", "type": "ORGANIZATION", "description": "AI company"}
        session.run.return_value = [mock_record]

        results = retriever.search_entities("OpenAI")

        assert len(results) == 1
        assert results[0]["name"] == "OpenAI"

    def test_search_entities_with_limit(self, retriever, mock_neo4j_driver):
        """Test entity search with custom limit."""
        session = mock_neo4j_driver.session.return_value.__enter__.return_value
        session.run.return_value = []

        retriever.search_entities("test", limit=20)

        # Verify limit parameter was passed
        call_args = session.run.call_args
        assert call_args[1]["limit"] == 20

    def test_search_entities_failure(self, retriever, mock_neo4j_driver):
        """Test that entity search failures are handled."""
        session = mock_neo4j_driver.session.return_value.__enter__.return_value
        session.run.side_effect = Exception("Query failed")

        results = retriever.search_entities("test")

        # Should return empty list instead of crashing
        assert results == []


class TestConvenienceFunction:
    """Test the convenience query_graphrag function."""

    @pytest.mark.asyncio
    async def test_query_graphrag_function(self, mock_neo4j_driver, mock_vectorstore):
        """Test the convenience query function."""
        with patch('retriever.get_read_graph', return_value=mock_neo4j_driver), \
             patch('retriever.get_vectorstore', return_value=mock_vectorstore), \
             patch('retriever.ChatGoogleGenerativeAI') as mock_openai, \
             patch('retriever.HybridRetriever.retrieve') as mock_retrieve:

            mock_response = QueryResponse(
                answer="Test answer",
                vector_context=[],
                graph_context="",
                sources=[]
            )
            mock_retrieve.return_value = mock_response

            result = await query_graphrag("What is AI?")

            assert isinstance(result, QueryResponse)
            assert result.answer == "Test answer"
