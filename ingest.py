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



ENTITY_EXTRACTION_PROMPT = """Extract entities and relationships from the text.

Text:
{text}

JSON Format:
{{
  "entities": [{{"name": "...", "type": "...", "description": "..."}}],
  "relationships": [{{"source": "...", "relation_type": "...", "target": "...", "description": "..."}}]
}}

Rules:
- Types: PERSON, ORGANIZATION, LOCATION, CONCEPT, PRODUCT, EVENT
- Rel Types: WORKS_AT, LOCATED_IN, PART_OF, RELATED_TO (etc)
- Exact name matching
"""


class Ingestor:
    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
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

        self.prompt = ChatPromptTemplate.from_template(ENTITY_EXTRACTION_PROMPT)
        self.driver = get_write_graph()
        self.chroma = get_vectorstore()
        self.sem = asyncio.Semaphore(config.max_concurrent_llm_calls)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=config.retry_min_wait, max=config.retry_max_wait),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _process_chunk(self, chunk: str, idx: int) -> Optional[KnowledgeGraph]:
        async with self.sem:
            logger.info(f"Processing chunk {idx}")
            # LLM call outside try/except for retry mechanism
            res = await self.llm.ainvoke(self.prompt.format_messages(text=chunk))

            try:
                # clean up json
                content = res.content.strip().lstrip("```json").rstrip("```").strip()
                
                data = json.loads(content)
                
                ents = [Entity(**e) for e in data.get("entities", [])]
                rels = [Relationship(**r) for r in data.get("relationships", [])]
                
                kg = KnowledgeGraph(entities=ents, relationships=rels)
                logger.info(f"Chunk {idx}: {len(kg.entities)} ents, {len(kg.relationships)} rels")
                return kg

            except Exception as e:
                logger.error(f"Failed chunk {idx}: {e}")
                return None

    async def _run_parallel(self, chunks: List[str]) -> List[KnowledgeGraph]:
        tasks = [self._process_chunk(chunk, i) for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if r and not isinstance(r, Exception)]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=config.retry_min_wait, max=config.retry_max_wait),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _save_graph(self, kgs: List[KnowledgeGraph]) -> None:
        logger.info("Writing to Neo4j...")
        
        ents = []
        for kg in kgs:
            for e in kg.entities:
                ents.append({
                    "name": e.name, 
                    "type": e.type, 
                    "description": e.description or ""
                })

        rels = []
        for kg in kgs:
            for r in kg.relationships:
                rels.append({
                    "source": r.source,
                    "target": r.target,
                    "relation_type": r.relation_type,
                    "description": r.description or ""
                })

        with self.driver.session() as session:
            if ents:
                session.run(
                    """
                    UNWIND $entities AS entity
                    MERGE (e:Entity {name: entity.name})
                    SET e.type = entity.type,
                        e.description = entity.description,
                        e.last_updated = datetime()
                    """,
                    entities=ents,
                )
                logger.info(f"Wrote {len(ents)} entities")

            if rels:
                from collections import defaultdict
                by_type = defaultdict(list)
                for r in rels:
                    by_type[r['relation_type']].append(r)

                total = 0
                for rtype, batch in by_type.items():
                    session.run(
                        f"""
                        UNWIND $rels AS rel
                        MATCH (source:Entity {{name: rel.source}})
                        MATCH (target:Entity {{name: rel.target}})
                        MERGE (source)-[r:{rtype}]->(target)
                        SET r.description = rel.description,
                            r.last_updated = datetime()
                        """,
                        rels=batch,
                    )
                    total += len(batch)
                logger.info(f"Wrote {total} rels")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=config.retry_min_wait, max=config.retry_max_wait),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _save_vectors(self, chunks: List[str], doc_id: str, fname: str) -> None:
        logger.info(f"Writing {len(chunks)} chunks to Chroma...")
        
        docs = []
        for i, chunk in enumerate(chunks):
            meta = {
                "document_id": doc_id,
                "filename": fname,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "timestamp": datetime.now().isoformat(),
            }
            docs.append(Document(page_content=chunk, metadata=meta))

        self.chroma.add_documents(docs, batch_size=100)

    async def ingest(self, text: str, filename: str) -> Dict[str, Any]:
        """Run the ingestion flow."""
        logger.info(f"Starting: {filename}")
        doc_id = str(uuid.uuid4())

        chunks = self.splitter.split_text(text)
        if not chunks:
            return {"success": False, "error": "No chunks", "document_id": doc_id}

        try:
            # Parallel extraction
            kgs = await self._run_parallel(chunks)
            
            ent_count = sum(len(kg.entities) for kg in kgs)
            rel_count = sum(len(kg.relationships) for kg in kgs)
            
            # Write DBs
            self._save_graph(kgs)
            self._save_vectors(chunks, doc_id, filename)
            
            return {
                "success": True,
                "document_id": doc_id,
                "filename": filename,
                "num_chunks": len(chunks),
                "num_entities": ent_count,
                "num_relationships": rel_count
            }

        except Exception as e:
            logger.error(f"Ingest failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": doc_id,
                "filename": filename
            }

    def init_schema(self) -> None:
        initialize_neo4j_schema(self.driver)


async def ingest_document_async(text: str, filename: str) -> Dict[str, Any]:
    # Wrapper for external calls
    return await Ingestor().ingest(text, filename)
