"""
Hybrid retrieval logic (Vector + Graph).
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_community.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import config
from models import QueryRequest, QueryResponse
from database import get_read_graph, get_vectorstore, get_async_read_graph, get_neo4j_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GRAPH_SEARCH_ERROR_MSG = "Graph search unavailable due to an internal error."


SYNTHESIS_PROMPT = """You are a helpful AI assistant that answers questions based on provided context.

Question: {question}

Vector Context (from similar documents):
{vector_context}

Graph Context (from knowledge graph):
{graph_context}

Instructions:
- Answer the question using the provided context
- If the context doesn't contain relevant information, say so honestly
- Be concise and accurate
- Cite specific entities or facts when possible

Answer:"""


class HybridRetriever:
    """Hybrid retrieval engine using vector search and graph traversal."""

    def __init__(self):
        """Initialize retriever with READ-ONLY database connections."""
        self._read_driver = None

        self.vectorstore = get_vectorstore()

        self.llm = ChatGoogleGenerativeAI(
            model=config.llm_model,
            temperature=config.llm_temperature,
            google_api_key=config.google_api_key,
        )

        self.synthesis_prompt = ChatPromptTemplate.from_template(SYNTHESIS_PROMPT)

        self._neo4j_graph: Optional[Neo4jGraph] = None

    @property
    def read_driver(self):
        """Lazy load the read driver."""
        if self._read_driver is None:
            self._read_driver = get_read_graph()
        return self._read_driver

    def _get_neo4j_graph(self) -> Neo4jGraph:
        """Get or create Neo4j graph wrapper with READ-ONLY credentials."""
        if self._neo4j_graph is None:
            self._neo4j_graph = get_neo4j_graph()
        return self._neo4j_graph

    def _vector_search_sync(self, query: str, k: int = None) -> List[str]:
        """
        Synchronous implementation of vector similarity search.

        Args:
            query: User query
            k: Number of results to retrieve

        Returns:
            List of relevant text chunks
        """
        if k is None:
            k = config.vector_search_k

        logger.info(f"Performing vector search for: {query[:50]}...")

        try:
            results = self.vectorstore.similarity_search(query, k=k)

            contexts = [doc.page_content for doc in results]

            logger.info(f"Vector search returned {len(contexts)} results")

            return contexts

        except Exception as e:
            logger.exception("Vector search error")
            raise

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
    async def _vector_search(self, query: str, k: int = None) -> List[str]:
        """
        Perform vector similarity search (async wrapper).
        Offloads blocking DB operations to thread pool executor.

        Args:
            query: User query
            k: Number of results to retrieve

        Returns:
            List of relevant text chunks
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._vector_search_sync, query, k)

    def _graph_search_sync(self, query: str) -> str:
        """
        Synchronous graph search operation (runs in thread pool).

        Args:
            query: User query

        Returns:
            Graph context as string
        """
        graph = self._get_neo4j_graph()

        chain = GraphCypherQAChain.from_llm(
            llm=self.llm,
            graph=graph,
            verbose=True,
            return_intermediate_steps=True,
            allow_dangerous_requests=False,
            validate_cypher=True,
        )

        result = chain.invoke({"query": query})

        graph_context = result.get("result", "")

        logger.info(f"Graph search completed")

        return graph_context

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
    async def _graph_search(self, query: str) -> str:
        """
        Perform graph-based search using READ-ONLY connection.
        Offloads blocking DB operations to thread pool executor.

        Args:
            query: User query

        Returns:
            Graph context as string
        """
        logger.info(f"Performing graph search for: {query[:50]}...")

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._graph_search_sync, query)

        return result

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
    async def _synthesize_answer(
        self, query: str, vector_context: List[str], graph_context: str
    ) -> str:
        """
        Synthesize final answer from vector and graph context.

        Args:
            query: User query
            vector_context: Results from vector search
            graph_context: Results from graph search

        Returns:
            Final answer
        """
        logger.info("Synthesizing final answer...")

        vector_text = "\n\n".join(vector_context) if vector_context else "No vector context available."

        messages = self.synthesis_prompt.format_messages(
            question=query,
            vector_context=vector_text,
            graph_context=graph_context or "No graph context available.",
        )

        response = await self.llm.ainvoke(messages)

        answer = response.content.strip()

        logger.info("Answer synthesis complete")

        return answer

    async def retrieve(self, request: QueryRequest) -> QueryResponse:
        """
        Perform hybrid retrieval and generate answer.

        Args:
            request: Query request with search preferences

        Returns:
            Query response with answer and context
        """
        logger.info(f"Processing query: {request.query[:50]}...")

        async def _safe_vector_search() -> List[str]:
            if request.use_vector_search:
                try:
                    return await self._vector_search(request.query)
                except Exception:
                    logger.exception("Vector search failed")
            return []

        async def _safe_graph_search() -> str:
            if request.use_graph_search:
                try:
                    return await self._graph_search(request.query)
                except Exception:
                    logger.exception("Graph search failed")
                    return GRAPH_SEARCH_ERROR_MSG
            return ""

        vector_context, graph_context = await asyncio.gather(
            _safe_vector_search(),
            _safe_graph_search()
        )

        if not vector_context and (not graph_context or graph_context == GRAPH_SEARCH_ERROR_MSG):
            return QueryResponse(
                answer="I couldn't find any relevant information to answer your question.",
                vector_context=[],
                graph_context="",
                sources=[],
            )

        answer = await self._synthesize_answer(
            request.query, vector_context, graph_context
        )

        sources = []
        if vector_context:
            sources.append("Vector Search")
        if graph_context:
            sources.append("Knowledge Graph")

        return QueryResponse(
            answer=answer,
            vector_context=vector_context,
            graph_context=graph_context,
            sources=sources,
        )

    def _get_graph_statistics_sync(self) -> Dict[str, Any]:
        """Synchronous implementation of graph statistics retrieval."""
        logger.info("Fetching graph statistics...")

        try:
            with self.read_driver.session() as session:
                result = session.run(
                    """
                    CALL {
                        MATCH (e:Entity)
                        RETURN count(e) as entity_count
                    }
                    CALL {
                        MATCH ()-[r]->()
                        RETURN count(r) as rel_count
                    }
                    CALL {
                        MATCH (e:Entity)
                        WITH e.type as type, count(e) as count
                        ORDER BY count DESC
                        RETURN collect([type, count]) as entity_types
                    }
                    CALL {
                        MATCH ()-[r]->()
                        WITH type(r) as type, count(r) as count
                        ORDER BY count DESC
                        RETURN collect([type, count]) as rel_types
                    }
                    RETURN entity_count, rel_count, entity_types, rel_types
                    """
                ).single()

                return {
                    "total_entities": result["entity_count"],
                    "total_relationships": result["rel_count"],
                    "entity_types": dict(result["entity_types"]),
                    "relationship_types": dict(result["rel_types"]),
                }

        except Exception as e:
            logger.exception("Error fetching graph statistics")
            return {
                "error": "An internal error occurred while fetching graph statistics.",
                "total_entities": 0,
                "total_relationships": 0,
                "entity_types": {},
                "relationship_types": {},
            }

    async def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph (READ-ONLY operation).
        Offloads blocking DB operations to thread pool executor.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_graph_statistics_sync)

    async def search_entities(self, name_pattern: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for entities by name pattern (READ-ONLY operation).
        Uses native async Neo4j driver for non-blocking IO.

        Args:
            name_pattern: Pattern to match entity names
            limit: Maximum number of results

        Returns:
            List of matching entities
        """
        logger.info(f"Searching entities matching: {name_pattern} (Async)")

        try:
            driver = await get_async_read_graph()

            async with driver.session() as session:
                result = await session.run(
                    """
                    MATCH (e:Entity)
                    WHERE toLower(e.name) CONTAINS toLower($pattern)
                    RETURN e.name as name, e.type as type, e.description as description
                    LIMIT $limit
                    """,
                    pattern=name_pattern,
                    limit=limit,
                )

                entities = await result.data()

                logger.info(f"Found {len(entities)} matching entities")

                return entities

        except Exception as e:
            logger.exception("Error searching entities (Async)")
            return []


async def query_graphrag(query: str, use_vector: bool = True, use_graph: bool = True) -> QueryResponse:
    """
    Convenience function to query the GraphRAG system.

    Args:
        query: User question
        use_vector: Enable vector search
        use_graph: Enable graph search

    Returns:
        Query response
    """
    retriever = HybridRetriever()
    request = QueryRequest(
        query=query,
        use_vector_search=use_vector,
        use_graph_search=use_graph,
    )
    return await retriever.retrieve(request)
