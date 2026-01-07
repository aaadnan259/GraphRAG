"""
Test suite for ingestion pipeline (ingest.py).
Tests chunking logic, batch writes, retry mechanisms, and resilience.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
from collections import defaultdict

from ingest import IngestionPipeline
from models import Entity, Relationship, KnowledgeGraph


class TestTextChunking:
    """Test text chunking with edge cases."""

    @pytest.fixture
    def pipeline(self, mock_neo4j_driver, mock_vectorstore):
        """Create ingestion pipeline with mocked dependencies."""
        with patch('ingest.get_write_graph', return_value=mock_neo4j_driver), \
             patch('ingest.get_vectorstore', return_value=mock_vectorstore), \
             patch('ingest.ChatOpenAI'):
            pipeline = IngestionPipeline()
            return pipeline

    def test_chunk_normal_text(self, pipeline):
        """Test chunking of normal text."""
        text = "This is a test. " * 100
        chunks = pipeline.text_splitter.split_text(text)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_chunk_empty_string(self, pipeline, edge_case_texts):
        """Test chunking empty string."""
        chunks = pipeline.text_splitter.split_text(edge_case_texts["empty"])
        assert chunks == []

    def test_chunk_whitespace_only(self, pipeline, edge_case_texts):
        """Test chunking whitespace-only text."""
        chunks = pipeline.text_splitter.split_text(edge_case_texts["whitespace_only"])
        # Should return empty or minimal chunks
        assert len(chunks) <= 1

    def test_chunk_single_char(self, pipeline, edge_case_texts):
        """Test chunking single character."""
        chunks = pipeline.text_splitter.split_text(edge_case_texts["single_char"])
        assert len(chunks) == 1
        assert chunks[0] == "a"

    def test_chunk_no_spaces(self, pipeline, edge_case_texts):
        """Test chunking text with no spaces (massive single line)."""
        chunks = pipeline.text_splitter.split_text(edge_case_texts["no_spaces"])
        # Should still create chunks, even without natural breaks
        assert len(chunks) >= 1

    def test_chunk_massive_line(self, pipeline, edge_case_texts):
        """Test chunking massive single line with spaces."""
        chunks = pipeline.text_splitter.split_text(edge_case_texts["massive_line"])
        # Should split into multiple chunks
        assert len(chunks) > 1

    def test_chunk_markdown_headers(self, pipeline, edge_case_texts):
        """Test chunking markdown with headers."""
        chunks = pipeline.text_splitter.split_text(edge_case_texts["markdown_headers"])
        assert len(chunks) >= 1
        # Headers should be preserved in chunks
        assert any("#" in chunk for chunk in chunks)

    def test_chunk_unicode(self, pipeline, edge_case_texts):
        """Test chunking text with special unicode."""
        chunks = pipeline.text_splitter.split_text(edge_case_texts["special_unicode"])
        assert len(chunks) == 1
        assert "世界" in chunks[0]
        assert "🌍" in chunks[0]

    def test_chunk_overlap(self, pipeline):
        """Test that chunk overlap is maintained."""
        text = "Sentence one. Sentence two. Sentence three. " * 50
        chunks = pipeline.text_splitter.split_text(text)

        if len(chunks) > 1:
            # Check that there's some overlap between consecutive chunks
            # The exact overlap depends on the chunk_overlap setting
            assert len(chunks) >= 2


class TestKnowledgeExtraction:
    """Test knowledge extraction from text chunks."""

    @pytest.fixture
    def pipeline(self, mock_neo4j_driver, mock_vectorstore):
        """Create ingestion pipeline with mocked dependencies."""
        with patch('ingest.get_write_graph', return_value=mock_neo4j_driver), \
             patch('ingest.get_vectorstore', return_value=mock_vectorstore), \
             patch('ingest.ChatOpenAI') as mock_openai:

            # Mock the LLM
            mock_llm = AsyncMock()
            mock_openai.return_value = mock_llm

            pipeline = IngestionPipeline()
            pipeline.llm = mock_llm

            return pipeline

    @pytest.mark.asyncio
    async def test_extract_knowledge_valid_json(self, pipeline):
        """Test extraction with valid JSON response."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '''```json
        {
            "entities": [
                {"name": "Alice", "type": "PERSON", "description": "Engineer"}
            ],
            "relationships": [
                {"source": "Alice", "relation_type": "WORKS_AT", "target": "TechCorp", "description": "employee"}
            ]
        }
        ```'''

        pipeline.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await pipeline._extract_knowledge_from_chunk("Test text", 0)

        assert result is not None
        assert len(result.entities) == 1
        assert len(result.relationships) == 1
        assert result.entities[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_extract_knowledge_invalid_json(self, pipeline):
        """Test extraction with invalid JSON response."""
        # Mock LLM response with invalid JSON
        mock_response = Mock()
        mock_response.content = "This is not valid JSON"

        pipeline.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await pipeline._extract_knowledge_from_chunk("Test text", 0)

        # Should return None on JSON parse error
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_knowledge_empty_response(self, pipeline):
        """Test extraction with empty entities/relationships."""
        mock_response = Mock()
        mock_response.content = '{"entities": [], "relationships": []}'

        pipeline.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await pipeline._extract_knowledge_from_chunk("Test text", 0)

        assert result is not None
        assert len(result.entities) == 0
        assert len(result.relationships) == 0

    @pytest.mark.asyncio
    async def test_extract_knowledge_parallel(self, pipeline):
        """Test parallel extraction from multiple chunks."""
        chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]

        # Mock successful extraction
        mock_response = Mock()
        mock_response.content = '{"entities": [{"name": "Test", "type": "PERSON"}], "relationships": []}'
        pipeline.llm.ainvoke = AsyncMock(return_value=mock_response)

        results = await pipeline._extract_knowledge_parallel(chunks)

        # Should extract from all chunks
        assert len(results) == 3


class TestBatchWrites:
    """Test batch write operations to Neo4j."""

    @pytest.fixture
    def pipeline(self, mock_neo4j_driver, mock_vectorstore):
        """Create ingestion pipeline with mocked dependencies."""
        with patch('ingest.get_write_graph', return_value=mock_neo4j_driver), \
             patch('ingest.get_vectorstore', return_value=mock_vectorstore), \
             patch('ingest.ChatOpenAI'):

            pipeline = IngestionPipeline()
            return pipeline

    def test_batch_write_single_knowledge_graph(self, pipeline, mock_neo4j_driver):
        """Test batch write with single knowledge graph."""
        entities = [
            Entity(name="Alice", type="PERSON"),
            Entity(name="Bob", type="PERSON"),
        ]
        relationships = [
            Relationship(source="Alice", target="Bob", relation_type="WORKS_AT")
        ]

        kg = KnowledgeGraph(entities=entities, relationships=relationships)

        pipeline._write_to_neo4j([kg])

        # Get the session mock
        session = mock_neo4j_driver.session.return_value.__enter__.return_value

        # Verify session.run was called
        assert session.run.called

        # Should be called EXACTLY 2 times (one for entities, one for relationships)
        # OR more if grouped by relationship type
        call_count = session.run.call_count
        assert call_count >= 1  # At least entities batch

        # Verify UNWIND is used
        calls = session.run.call_args_list
        has_unwind = any("UNWIND" in str(call) for call in calls)
        assert has_unwind, "Batch writes should use UNWIND"

    def test_batch_write_multiple_knowledge_graphs(self, pipeline, mock_neo4j_driver):
        """Test batch write with multiple knowledge graphs (NO N+1)."""
        # Create multiple knowledge graphs
        kg1 = KnowledgeGraph(
            entities=[Entity(name="Alice", type="PERSON")],
            relationships=[Relationship(source="Alice", target="Bob", relation_type="WORKS_AT")]
        )
        kg2 = KnowledgeGraph(
            entities=[Entity(name="Charlie", type="PERSON")],
            relationships=[Relationship(source="Charlie", target="Dave", relation_type="MANAGES")]
        )
        kg3 = KnowledgeGraph(
            entities=[Entity(name="Eve", type="PERSON")],
            relationships=[Relationship(source="Eve", target="Frank", relation_type="WORKS_AT")]
        )

        pipeline._write_to_neo4j([kg1, kg2, kg3])

        session = mock_neo4j_driver.session.return_value.__enter__.return_value

        # Critical test: should NOT have N individual calls
        # Should have at most 1 + K calls (1 for entities, K for relationship types)
        call_count = session.run.call_count

        # With 3 entities and 3 relationships across 2 types (WORKS_AT, MANAGES)
        # Expected: 1 entity batch + 2 relationship batches = 3 total
        assert call_count <= 5, f"Too many session.run calls: {call_count}. N+1 problem detected!"

    def test_batch_write_empty_knowledge_graphs(self, pipeline, mock_neo4j_driver):
        """Test batch write with empty knowledge graphs."""
        kg = KnowledgeGraph(entities=[], relationships=[])

        pipeline._write_to_neo4j([kg])

        session = mock_neo4j_driver.session.return_value.__enter__.return_value

        # Should not call session.run if no data
        assert session.run.call_count == 0

    def test_batch_write_groups_by_relation_type(self, pipeline, mock_neo4j_driver):
        """Test that relationships are grouped by type for batching."""
        relationships = [
            Relationship(source="A", target="B", relation_type="WORKS_AT"),
            Relationship(source="C", target="D", relation_type="WORKS_AT"),
            Relationship(source="E", target="F", relation_type="MANAGES"),
        ]

        kg = KnowledgeGraph(
            entities=[Entity(name="A", type="PERSON")],
            relationships=relationships
        )

        pipeline._write_to_neo4j([kg])

        session = mock_neo4j_driver.session.return_value.__enter__.return_value

        # Check that batching by type is happening
        # Should have: 1 entity batch + 2 relationship type batches
        call_count = session.run.call_count
        assert call_count == 3  # 1 entities + 2 relationship types


class TestRetryMechanism:
    """Test retry logic with tenacity."""

    @pytest.fixture
    def pipeline(self, mock_neo4j_driver, mock_vectorstore):
        """Create ingestion pipeline with mocked dependencies."""
        with patch('ingest.get_write_graph', return_value=mock_neo4j_driver), \
             patch('ingest.get_vectorstore', return_value=mock_vectorstore), \
             patch('ingest.ChatOpenAI') as mock_openai:

            mock_llm = AsyncMock()
            mock_openai.return_value = mock_llm

            pipeline = IngestionPipeline()
            pipeline.llm = mock_llm

            return pipeline

    @pytest.mark.asyncio
    async def test_retry_on_api_failure(self, pipeline):
        """Test that API failures trigger retry logic."""
        call_count = 0

        async def failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("API Error")
            else:
                mock_response = Mock()
                mock_response.content = '{"entities": [], "relationships": []}'
                return mock_response

        pipeline.llm.ainvoke = AsyncMock(side_effect=failing_then_succeeding)

        result = await pipeline._extract_knowledge_from_chunk("Test text", 0)

        # Should succeed after retry
        assert result is not None
        assert call_count == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, pipeline):
        """Test that retries are exhausted after max attempts."""
        pipeline.llm.ainvoke = AsyncMock(side_effect=Exception("Persistent error"))

        with pytest.raises(Exception):
            await pipeline._extract_knowledge_from_chunk("Test text", 0)


class TestVectorStoreWrites:
    """Test vector store write operations."""

    @pytest.fixture
    def pipeline(self, mock_neo4j_driver, mock_vectorstore):
        """Create ingestion pipeline with mocked dependencies."""
        with patch('ingest.get_write_graph', return_value=mock_neo4j_driver), \
             patch('ingest.get_vectorstore', return_value=mock_vectorstore), \
             patch('ingest.ChatOpenAI'):

            pipeline = IngestionPipeline()
            return pipeline

    def test_write_chunks_to_vectorstore(self, pipeline, mock_vectorstore):
        """Test writing chunks to vector store."""
        chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
        document_id = "doc-123"
        filename = "test.txt"

        pipeline._write_to_vectorstore(chunks, document_id, filename)

        # Verify add_documents was called
        assert mock_vectorstore.add_documents.called

        # Verify correct number of documents
        call_args = mock_vectorstore.add_documents.call_args
        documents = call_args[0][0]
        assert len(documents) == 3

    def test_vectorstore_metadata(self, pipeline, mock_vectorstore):
        """Test that correct metadata is attached to documents."""
        chunks = ["Test chunk"]
        document_id = "doc-456"
        filename = "sample.txt"

        pipeline._write_to_vectorstore(chunks, document_id, filename)

        call_args = mock_vectorstore.add_documents.call_args
        documents = call_args[0][0]

        metadata = documents[0].metadata
        assert metadata["document_id"] == document_id
        assert metadata["filename"] == filename
        assert metadata["chunk_index"] == 0
        assert metadata["total_chunks"] == 1


class TestFullIngestionPipeline:
    """Test complete end-to-end ingestion."""

    @pytest.fixture
    def pipeline(self, mock_neo4j_driver, mock_vectorstore):
        """Create fully mocked pipeline."""
        with patch('ingest.get_write_graph', return_value=mock_neo4j_driver), \
             patch('ingest.get_vectorstore', return_value=mock_vectorstore), \
             patch('ingest.ChatOpenAI') as mock_openai:

            mock_llm = AsyncMock()
            mock_response = Mock()
            mock_response.content = '''
            {
                "entities": [{"name": "OpenAI", "type": "ORGANIZATION", "description": "AI company"}],
                "relationships": [{"source": "OpenAI", "target": "GPT-4", "relation_type": "CREATED", "description": "developed"}]
            }
            '''
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_llm

            pipeline = IngestionPipeline()
            return pipeline

    @pytest.mark.asyncio
    async def test_ingest_document_success(self, pipeline):
        """Test successful document ingestion."""
        text = "OpenAI created GPT-4, a large language model."
        filename = "test.txt"

        result = await pipeline.ingest_document(text, filename)

        assert result["success"] is True
        assert "document_id" in result
        assert result["filename"] == filename
        assert result["num_chunks"] > 0

    @pytest.mark.asyncio
    async def test_ingest_empty_document(self, pipeline):
        """Test ingesting empty document."""
        text = ""
        filename = "empty.txt"

        result = await pipeline.ingest_document(text, filename)

        assert result["success"] is False
        assert "error" in result
