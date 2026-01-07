"""
Data models and validation schemas.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ValidationError
import re


ALLOWED_RELATION_TYPES = {
    "WORKS_AT",
    "LOCATED_IN",
    "PART_OF",
    "RELATED_TO",
    "MANAGES",
    "REPORTS_TO",
    "OWNS",
    "FOUNDED",
    "ACQUIRED",
    "INVESTED_IN",
    "COLLABORATED_WITH",
    "EMPLOYED_BY",
    "BASED_IN",
    "MEMBER_OF",
    "SUBSIDIARY_OF",
    "PARTNER_OF",
    "COMPETES_WITH",
    "SUPPLIES_TO",
    "INTERACTS_WITH",
}


RELATION_MAPPING = {
    "CEO_OF": "MANAGES",
    "IS_CEO": "MANAGES",
    "CEO": "MANAGES",
    "WORKS_FOR": "WORKS_AT",
    "EMPLOYED_AT": "WORKS_AT",
    "EMPLOYEE_OF": "WORKS_AT",
    "LOCATED_AT": "LOCATED_IN",
    "IN_LOCATION": "LOCATED_IN",
    "HAS_LOCATION": "LOCATED_IN",
    "IS_PART_OF": "PART_OF",
    "BELONGS_TO": "PART_OF",
    "COMPONENT_OF": "PART_OF",
    "RELATED": "RELATED_TO",
    "ASSOCIATED_WITH": "RELATED_TO",
    "CONNECTED_TO": "RELATED_TO",
}


def sanitize_text(text: str) -> str:
    """Sanitize text input to prevent injection attacks."""
    if not text:
        return ""
    text = text.strip()
    # Remove dangerous characters including SQL/Cypher comment operators
    text = re.sub(r'[^\w\s\-.,!?]', '', text)
    # Remove double-dash SQL comment operator
    text = re.sub(r'--+', '', text)
    text = text[:500]
    return text


def normalize_relation_type(relation: str) -> str:
    """Normalize relation type to canonical form."""
    relation = relation.strip().upper()
    relation = re.sub(r'[^\w_]', '_', relation)
    relation = re.sub(r'_+', '_', relation)
    relation = relation.strip('_')

    if relation in ALLOWED_RELATION_TYPES:
        return relation

    if relation in RELATION_MAPPING:
        return RELATION_MAPPING[relation]

    return "RELATED_TO"


class Entity(BaseModel):
    """Represents a knowledge graph entity."""

    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    description: Optional[str] = Field(None)

    @field_validator('name', 'type', 'description')
    @classmethod
    def sanitize_fields(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize all text fields (includes length truncation)."""
        if v is None:
            return None
        sanitized = sanitize_text(v)
        # Enforce max lengths after sanitization
        if cls.model_fields.get('name') and v == sanitized:
            return sanitized[:500]
        return sanitized

    @field_validator('type')
    @classmethod
    def normalize_type(cls, v: str) -> str:
        """Normalize entity type."""
        normalized = v.strip().upper()
        return normalized[:100]  # Enforce max length


class Relationship(BaseModel):
    """Represents a knowledge graph relationship between entities."""

    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    relation_type: str = Field(..., min_length=1)
    description: Optional[str] = Field(None)

    @field_validator('source', 'target', 'description')
    @classmethod
    def sanitize_fields(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize all text fields (includes length truncation)."""
        if v is None:
            return None
        sanitized = sanitize_text(v)
        return sanitized[:500]  # Enforce max length

    @field_validator('relation_type')
    @classmethod
    def validate_and_normalize_relation(cls, v: str) -> str:
        """Validate and normalize relationship type to canonical schema."""
        normalized = normalize_relation_type(v)
        return normalized[:100]  # Enforce max length


class KnowledgeGraph(BaseModel):
    """Complete knowledge graph extracted from text."""

    entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)

    @field_validator('entities')
    @classmethod
    def deduplicate_entities(cls, v: List[Entity]) -> List[Entity]:
        """Remove duplicate entities based on name."""
        seen = set()
        unique = []
        for entity in v:
            key = entity.name.lower()
            if key not in seen:
                seen.add(key)
                unique.append(entity)
        return unique

    @field_validator('relationships')
    @classmethod
    def deduplicate_relationships(cls, v: List[Relationship]) -> List[Relationship]:
        """Remove duplicate relationships."""
        seen = set()
        unique = []
        for rel in v:
            key = (rel.source.lower(), rel.relation_type, rel.target.lower())
            if key not in seen:
                seen.add(key)
                unique.append(rel)
        return unique


class DocumentMetadata(BaseModel):
    """Metadata for ingested documents."""

    filename: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    chunk_index: int = Field(..., ge=0)
    total_chunks: int = Field(..., ge=1)

    @field_validator('filename', 'document_id')
    @classmethod
    def sanitize_metadata(cls, v: str) -> str:
        """Sanitize metadata fields (includes length truncation)."""
        sanitized = sanitize_text(v)
        return sanitized[:500]  # Enforce max length


class QueryRequest(BaseModel):
    """User query request."""

    query: str = Field(..., min_length=1)
    use_vector_search: bool = Field(default=True)
    use_graph_search: bool = Field(default=True)

    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Sanitize user query (includes length truncation)."""
        sanitized = sanitize_text(v)
        # Allow longer queries but still enforce reasonable limit
        return sanitized[:2000]  # Enforce max length


class QueryResponse(BaseModel):
    """Response to user query."""

    answer: str
    vector_context: List[str] = Field(default_factory=list)
    graph_context: str = Field(default="")
    sources: List[str] = Field(default_factory=list)
