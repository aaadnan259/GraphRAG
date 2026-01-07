"""
Test suite for data models (models.py).
Tests schema validation, sanitization, and edge cases.
"""

import pytest
from pydantic import ValidationError
from models import (
    Entity,
    Relationship,
    KnowledgeGraph,
    DocumentMetadata,
    QueryRequest,
    QueryResponse,
    sanitize_text,
    normalize_relation_type,
    ALLOWED_RELATION_TYPES,
)


class TestSanitizeText:
    """Test text sanitization function."""

    def test_sanitize_normal_text(self):
        """Test sanitization of normal text."""
        result = sanitize_text("Hello World")
        assert result == "Hello World"

    def test_sanitize_sql_injection(self, malicious_inputs):
        """Test that SQL injection characters are removed."""
        result = sanitize_text(malicious_inputs["sql_injection"])
        # Should remove special SQL characters
        assert "DROP" in result  # Words remain
        assert ";" not in result  # Semicolon removed
        assert "--" not in result  # Comment removed

    def test_sanitize_cypher_injection(self, malicious_inputs):
        """Test that Cypher injection characters are handled."""
        result = sanitize_text(malicious_inputs["cypher_injection"])
        assert "MATCH" in result
        assert "DELETE" in result
        # Special characters should be removed
        assert "(" not in result
        assert ")" not in result

    def test_sanitize_xss_attack(self, malicious_inputs):
        """Test XSS payload sanitization."""
        result = sanitize_text(malicious_inputs["xss"])
        assert "<script>" not in result
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_command_injection(self, malicious_inputs):
        """Test command injection sanitization."""
        result = sanitize_text(malicious_inputs["command_injection"])
        assert ";" not in result
        assert "/" not in result

    def test_sanitize_null_bytes(self, malicious_inputs):
        """Test null byte sanitization."""
        result = sanitize_text(malicious_inputs["null_bytes"])
        assert "\x00" not in result

    def test_sanitize_long_string(self, malicious_inputs):
        """Test that long strings are truncated."""
        result = sanitize_text(malicious_inputs["long_string"])
        assert len(result) <= 500

    def test_sanitize_empty_string(self):
        """Test sanitization of empty string."""
        result = sanitize_text("")
        assert result == ""

    def test_sanitize_none(self):
        """Test sanitization of None."""
        result = sanitize_text(None)
        assert result == ""

    def test_sanitize_whitespace(self):
        """Test that whitespace is preserved."""
        result = sanitize_text("  Hello   World  ")
        assert result.strip() == "Hello   World"


class TestNormalizeRelationType:
    """Test relationship type normalization."""

    def test_normalize_valid_type(self):
        """Test normalization of valid relationship type."""
        assert normalize_relation_type("WORKS_AT") == "WORKS_AT"
        assert normalize_relation_type("works_at") == "WORKS_AT"
        assert normalize_relation_type("  WORKS_AT  ") == "WORKS_AT"

    def test_normalize_mapped_type(self):
        """Test normalization of mapped relationship types."""
        assert normalize_relation_type("CEO_OF") == "MANAGES"
        assert normalize_relation_type("WORKS_FOR") == "WORKS_AT"
        assert normalize_relation_type("LOCATED_AT") == "LOCATED_IN"

    def test_normalize_invalid_type(self):
        """Test that invalid types default to RELATED_TO."""
        assert normalize_relation_type("IS_BOSS_OF") == "RELATED_TO"
        assert normalize_relation_type("RANDOM_TYPE") == "RELATED_TO"
        assert normalize_relation_type("UNKNOWN") == "RELATED_TO"

    def test_normalize_special_characters(self):
        """Test normalization with special characters."""
        assert normalize_relation_type("WORKS-AT") == "WORKS_AT"
        assert normalize_relation_type("WORKS AT") == "WORKS_AT"
        assert normalize_relation_type("WORKS__AT") == "WORKS_AT"

    def test_normalize_malicious_input(self, malicious_inputs):
        """Test normalization with malicious input."""
        # Should always return a valid relationship type
        result = normalize_relation_type(malicious_inputs["sql_injection"])
        assert result in ALLOWED_RELATION_TYPES or result == "RELATED_TO"


class TestEntityModel:
    """Test Entity model validation."""

    def test_create_valid_entity(self, sample_entities):
        """Test creating a valid entity."""
        entity = Entity(**sample_entities[0])
        assert entity.name == "Alice"
        assert entity.type == "PERSON"
        assert entity.description == "Software engineer"

    def test_entity_name_required(self):
        """Test that entity name is required."""
        with pytest.raises(ValidationError) as exc_info:
            Entity(name="", type="PERSON")
        assert "name" in str(exc_info.value).lower()

    def test_entity_type_required(self):
        """Test that entity type is required."""
        with pytest.raises(ValidationError) as exc_info:
            Entity(name="Alice", type="")
        assert "type" in str(exc_info.value).lower()

    def test_entity_sanitization(self, malicious_inputs):
        """Test that entity fields are sanitized."""
        entity = Entity(
            name=malicious_inputs["sql_injection"],
            type="PERSON",
            description=malicious_inputs["xss"]
        )
        # Check that dangerous characters are removed
        assert ";" not in entity.name
        assert "<" not in entity.description

    def test_entity_type_normalization(self):
        """Test that entity type is normalized to uppercase."""
        entity = Entity(name="Alice", type="person", description="Test")
        assert entity.type == "PERSON"

    def test_entity_description_optional(self):
        """Test that description is optional."""
        entity = Entity(name="Alice", type="PERSON")
        assert entity.description is None

    def test_entity_max_length(self):
        """Test field length limits."""
        long_name = "A" * 600
        entity = Entity(name=long_name, type="PERSON")
        # Should be truncated to 500 characters
        assert len(entity.name) <= 500


class TestRelationshipModel:
    """Test Relationship model validation."""

    def test_create_valid_relationship(self, sample_relationships):
        """Test creating a valid relationship."""
        rel = Relationship(**sample_relationships[0])
        assert rel.source == "Alice"
        assert rel.target == "TechCorp"
        assert rel.relation_type == "WORKS_AT"

    def test_relationship_normalization(self):
        """Test relationship type normalization."""
        rel = Relationship(
            source="Alice",
            target="TechCorp",
            relation_type="WORKS_FOR"
        )
        assert rel.relation_type == "WORKS_AT"

    def test_relationship_invalid_type_defaults(self):
        """Test that invalid relationship types default to RELATED_TO."""
        rel = Relationship(
            source="Alice",
            target="Bob",
            relation_type="IS_BOSS_OF"
        )
        assert rel.relation_type == "RELATED_TO"

    def test_relationship_sanitization(self, malicious_inputs):
        """Test that relationship fields are sanitized."""
        rel = Relationship(
            source=malicious_inputs["sql_injection"],
            target=malicious_inputs["cypher_injection"],
            relation_type="WORKS_AT",
            description=malicious_inputs["command_injection"]
        )
        # Dangerous characters should be removed
        assert ";" not in rel.source
        assert "(" not in rel.target
        assert "/" not in rel.description

    def test_relationship_required_fields(self):
        """Test that all required fields are validated."""
        with pytest.raises(ValidationError):
            Relationship(source="", target="Bob", relation_type="WORKS_AT")

        with pytest.raises(ValidationError):
            Relationship(source="Alice", target="", relation_type="WORKS_AT")

        with pytest.raises(ValidationError):
            Relationship(source="Alice", target="Bob", relation_type="")


class TestKnowledgeGraphModel:
    """Test KnowledgeGraph model validation."""

    def test_create_empty_knowledge_graph(self):
        """Test creating an empty knowledge graph."""
        kg = KnowledgeGraph()
        assert kg.entities == []
        assert kg.relationships == []

    def test_create_knowledge_graph_with_data(self, sample_entities, sample_relationships):
        """Test creating a knowledge graph with data."""
        entities = [Entity(**e) for e in sample_entities]
        relationships = [Relationship(**r) for r in sample_relationships]

        kg = KnowledgeGraph(entities=entities, relationships=relationships)
        assert len(kg.entities) == 3
        assert len(kg.relationships) == 2

    def test_deduplicate_entities(self):
        """Test that duplicate entities are removed."""
        entities = [
            Entity(name="Alice", type="PERSON"),
            Entity(name="alice", type="PERSON"),  # Duplicate (case-insensitive)
            Entity(name="Bob", type="PERSON"),
        ]

        kg = KnowledgeGraph(entities=entities)
        assert len(kg.entities) == 2  # Only Alice and Bob

    def test_deduplicate_relationships(self):
        """Test that duplicate relationships are removed."""
        relationships = [
            Relationship(source="Alice", target="Bob", relation_type="WORKS_AT"),
            Relationship(source="alice", target="bob", relation_type="WORKS_AT"),  # Duplicate
            Relationship(source="Alice", target="Charlie", relation_type="WORKS_AT"),
        ]

        kg = KnowledgeGraph(relationships=relationships)
        assert len(kg.relationships) == 2  # Only unique relationships


class TestDocumentMetadata:
    """Test DocumentMetadata model."""

    def test_create_valid_metadata(self):
        """Test creating valid document metadata."""
        metadata = DocumentMetadata(
            filename="test.txt",
            document_id="doc-123",
            chunk_index=0,
            total_chunks=5
        )
        assert metadata.filename == "test.txt"
        assert metadata.chunk_index == 0
        assert metadata.total_chunks == 5

    def test_chunk_index_non_negative(self):
        """Test that chunk_index must be non-negative."""
        with pytest.raises(ValidationError):
            DocumentMetadata(
                filename="test.txt",
                document_id="doc-123",
                chunk_index=-1,
                total_chunks=5
            )

    def test_total_chunks_minimum(self):
        """Test that total_chunks must be at least 1."""
        with pytest.raises(ValidationError):
            DocumentMetadata(
                filename="test.txt",
                document_id="doc-123",
                chunk_index=0,
                total_chunks=0
            )


class TestQueryRequest:
    """Test QueryRequest model."""

    def test_create_valid_query(self):
        """Test creating a valid query request."""
        query = QueryRequest(query="What is OpenAI?")
        assert query.query == "What is OpenAI?"
        assert query.use_vector_search is True
        assert query.use_graph_search is True

    def test_query_sanitization(self, malicious_inputs):
        """Test that query is sanitized."""
        query = QueryRequest(query=malicious_inputs["sql_injection"])
        assert ";" not in query.query
        assert "--" not in query.query

    def test_query_max_length(self):
        """Test query length limit."""
        long_query = "What is " * 500
        query = QueryRequest(query=long_query)
        # Should be truncated in sanitization
        assert len(query.query) <= 500

    def test_query_empty_string(self):
        """Test that empty query is rejected."""
        with pytest.raises(ValidationError):
            QueryRequest(query="")


class TestQueryResponse:
    """Test QueryResponse model."""

    def test_create_valid_response(self):
        """Test creating a valid response."""
        response = QueryResponse(
            answer="OpenAI is an AI company.",
            vector_context=["Context 1", "Context 2"],
            graph_context="Graph info",
            sources=["Vector Search", "Knowledge Graph"]
        )
        assert response.answer == "OpenAI is an AI company."
        assert len(response.vector_context) == 2
        assert len(response.sources) == 2

    def test_response_with_defaults(self):
        """Test response with default values."""
        response = QueryResponse(answer="Test answer")
        assert response.answer == "Test answer"
        assert response.vector_context == []
        assert response.graph_context == ""
        assert response.sources == []
