"""
Ingestion Pipeline Module
Handles async ETL operations: text chunking, entity/relationship extraction,
and writing to Neo4j (RW) and ChromaDB.
"""

import asyncio
import logging
import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import config
from models import Entity, Relationship, KnowledgeGraph, DocumentMetadata
from database import get_write_graph, get_vectorstore, initialize_neo4j_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


ENTITY_EXTRACTION_PROMPT = """You are a knowledge graph extraction expert. Extract all entities and relationships from the following text.

Text:
{text}

Extract:
1. Entities: name, type (PERSON, ORGANIZATION, LOCATION, CONCEPT, PRODUCT, EVENT), description
2. Relationships: source entity, relation type, target entity, description

Format your response as JSON:
{{
  "entities": [
    {{"name": "...", "type": "...", "description": "..."}},
    ...
  ],
  "relationships": [
    {{"source": "...", "relation_type": "...", "target": "...", "description": "..."}},
    ...
  ]
}}

Rules:
- Use canonical relationship types: WORKS_AT, LOCATED_IN, PART_OF, MANAGES, REPORTS_TO, RELATED_TO, etc.
- Be specific and accurate
- Only extract information explicitly stated in the text
- Entity names must match exactly between entities and relationships
"""


class IngestionPipeline:
    """Async ETL pipeline for document ingestion."""

    def __init__(self):
        """Initialize ingestion pipeline."""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        self.llm = ChatGoogleGenerativeAI(
            model=config.llm_model,
            temperature=config.llm_temperature,
            google_api_key=config.google_api_key,
        )

        self.extraction_prompt = ChatPromptTemplate.from_template(
            ENTITY_EXTRACTION_PROMPT
        )

        self.graph_driver = get_write_graph()
        self.vectorstore = get_vectorstore()

        self.semaphore = asyncio.Semaphore(config.max_concurrent_llm_calls)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(
            multiplier=1,
            min=config.retry_min_wait,
            max=config.retry_max_wait
        ),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _extract_knowledge_from_chunk(
        self, chunk: str, chunk_index: int
    ) -> Optional[KnowledgeGraph]:
        """Extract entities and relationships from a text chunk with retry logic."""
        async with self.semaphore:
            try:
                logger.info(f"Extracting knowledge from chunk {chunk_index}")

                messages = self.extraction_prompt.format_messages(text=chunk)

                response = await self.llm.ainvoke(messages)
                content = response.content.strip()

                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                import json
                data = json.loads(content)

                entities = [Entity(**e) for e in data.get("entities", [])]
                relationships = [
                    Relationship(**r) for r in data.get("relationships", [])
                ]

                kg = KnowledgeGraph(entities=entities, relationships=relationships)

                logger.info(
                    f"Chunk {chunk_index}: Extracted {len(kg.entities)} entities, "
                    f"{len(kg.relationships)} relationships"
                )

                return kg

            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error in chunk {chunk_index}: {e}")
                return None
            except Exception as e:
                logger.error(f"Error extracting knowledge from chunk {chunk_index}: {e}")
                raise

    async def _extract_knowledge_parallel(
        self, chunks: List[str]
    ) -> List[KnowledgeGraph]:
        """Extract knowledge from all chunks in parallel."""
        tasks = [
            self._extract_knowledge_from_chunk(chunk, i)
            for i, chunk in enumerate(chunks)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        knowledge_graphs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process chunk {i}: {result}")
            elif result is not None:
                knowledge_graphs.append(result)

        return knowledge_graphs

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(
            multiplier=1,
            min=config.retry_min_wait,
            max=config.retry_max_wait
        ),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _write_to_neo4j(self, knowledge_graphs: List[KnowledgeGraph]) -> None:
        """Write knowledge graphs to Neo4j using batched UNWIND operations."""
        logger.info("Writing knowledge graph to Neo4j...")

        # Flatten all entities from all knowledge graphs into a single list
        all_entities = []
        for kg in knowledge_graphs:
            for entity in kg.entities:
                all_entities.append({
                    "name": entity.name,
                    "type": entity.type,
                    "description": entity.description or "",
                })

        # Flatten all relationships from all knowledge graphs into a single list
        all_relationships = []
        for kg in knowledge_graphs:
            for rel in kg.relationships:
                all_relationships.append({
                    "source": rel.source,
                    "target": rel.target,
                    "relation_type": rel.relation_type,
                    "description": rel.description or "",
                })

        with self.graph_driver.session() as session:
            # Execute single batched transaction for all entities
            if all_entities:
                try:
                    session.run(
                        """
                        UNWIND $entities AS entity
                        MERGE (e:Entity {name: entity.name})
                        SET e.type = entity.type,
                            e.description = entity.description,
                            e.last_updated = datetime()
                        """,
                        entities=all_entities,
                    )
                    logger.info(f"Batch wrote {len(all_entities)} entities")
                except Exception as e:
                    logger.error(f"Error writing entities batch: {e}")
                    raise

            # Execute batched transaction for relationships grouped by type
            if all_relationships:
                # Group relationships by type for efficient batching
                from collections import defaultdict
                rels_by_type = defaultdict(list)
                for rel in all_relationships:
                    rels_by_type[rel['relation_type']].append({
                        'source': rel['source'],
                        'target': rel['target'],
                        'description': rel['description'],
                    })

                # Execute one UNWIND query per relationship type
                try:
                    total_written = 0
                    for rel_type, rels in rels_by_type.items():
                        session.run(
                            f"""
                            UNWIND $rels AS rel
                            MATCH (source:Entity {{name: rel.source}})
                            MATCH (target:Entity {{name: rel.target}})
                            MERGE (source)-[r:{rel_type}]->(target)
                            SET r.description = rel.description,
                                r.last_updated = datetime()
                            """,
                            rels=rels,
                        )
                        total_written += len(rels)
                    logger.info(f"Batch wrote {total_written} relationships across {len(rels_by_type)} types")
                except Exception as e:
                    logger.error(f"Error writing relationships batch: {e}")
                    raise

        logger.info("Neo4j write complete")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(
            multiplier=1,
            min=config.retry_min_wait,
            max=config.retry_max_wait
        ),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _write_to_vectorstore(
        self, chunks: List[str], document_id: str, filename: str
    ) -> None:
        """Write text chunks to ChromaDB with retry logic."""
        logger.info(f"Writing {len(chunks)} chunks to ChromaDB...")

        documents = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "document_id": document_id,
                "filename": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "timestamp": datetime.now().isoformat(),
            }

            doc = Document(page_content=chunk, metadata=metadata)
            documents.append(doc)

        self.vectorstore.add_documents(documents, batch_size=100)

        logger.info("ChromaDB write complete")

    async def ingest_document(
        self, text: str, filename: str
    ) -> Dict[str, Any]:
        """
        Ingest a document: split, extract knowledge, write to databases.

        Args:
            text: Raw document text
            filename: Original filename

        Returns:
            Statistics about the ingestion process
        """
        logger.info(f"Starting ingestion for: {filename}")

        document_id = str(uuid.uuid4())

        chunks = self.text_splitter.split_text(text)
        logger.info(f"Split document into {len(chunks)} chunks")

        if not chunks:
            logger.warning("No chunks created from document")
            return {
                "success": False,
                "error": "No text chunks created",
                "document_id": document_id,
            }

        try:
            knowledge_graphs = await self._extract_knowledge_parallel(chunks)

            total_entities = sum(len(kg.entities) for kg in knowledge_graphs)
            total_relationships = sum(
                len(kg.relationships) for kg in knowledge_graphs
            )

            logger.info(
                f"Extracted {total_entities} entities and "
                f"{total_relationships} relationships"
            )

            self._write_to_neo4j(knowledge_graphs)

            self._write_to_vectorstore(chunks, document_id, filename)

            logger.info(f"Ingestion complete for: {filename}")

            return {
                "success": True,
                "document_id": document_id,
                "filename": filename,
                "num_chunks": len(chunks),
                "num_entities": total_entities,
                "num_relationships": total_relationships,
            }

        except Exception as e:
            logger.error(f"Ingestion failed for {filename}: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id,
                "filename": filename,
            }

    def initialize_schema(self) -> None:
        """Initialize Neo4j schema (indexes and constraints)."""
        initialize_neo4j_schema(self.graph_driver)


async def ingest_document_async(text: str, filename: str) -> Dict[str, Any]:
    """
    Convenience function to ingest a single document.

    Args:
        text: Document text
        filename: Document filename

    Returns:
        Ingestion statistics
    """
    pipeline = IngestionPipeline()
    return await pipeline.ingest_document(text, filename)
