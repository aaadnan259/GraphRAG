"""
Neo4j and ChromaDB connection management.
"""

import logging
from typing import Optional
from langchain_chroma import Chroma
from neo4j import GraphDatabase, Driver, AsyncGraphDatabase, AsyncDriver
from langchain_community.graphs import Neo4jGraph
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jConnectionManager:
    """Singleton manager for Neo4j connections with separate RW/RO credentials."""

    _write_driver: Optional[Driver] = None
    _read_driver: Optional[Driver] = None

    @classmethod
    def get_write_driver(cls) -> Driver:
        """
        Get or create the READ-WRITE driver for ingestion operations.
        Uses NEO4J_RW_USER credentials.
        """
        if cls._write_driver is None:
            logger.info("Initializing Neo4j WRITE driver with RW credentials")
            cls._write_driver = GraphDatabase.driver(
                config.neo4j_uri,
                auth=(config.neo4j_rw_user, config.neo4j_rw_password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_timeout=30,
            )
            cls._verify_connectivity(cls._write_driver, "WRITE")
        return cls._write_driver

    @classmethod
    def get_read_driver(cls) -> Driver:
        """
        Get or create the READ-ONLY driver for retrieval operations.
        Uses NEO4J_RO_USER credentials which must have database-level READ-ONLY permissions.
        """
        if cls._read_driver is None:
            logger.info("Initializing Neo4j READ driver with RO credentials")
            cls._read_driver = GraphDatabase.driver(
                config.neo4j_uri,
                auth=(config.neo4j_ro_user, config.neo4j_ro_password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_timeout=30,
            )
            cls._verify_connectivity(cls._read_driver, "READ")
        return cls._read_driver

    @classmethod
    def _verify_connectivity(cls, driver: Driver, mode: str) -> None:
        """Verify database connectivity."""
        try:
            driver.verify_connectivity()
            logger.info(f"Neo4j {mode} driver connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect Neo4j {mode} driver: {e}")
            raise

    @classmethod
    def close_all(cls) -> None:
        """Close all database connections."""
        if cls._write_driver:
            cls._write_driver.close()
            cls._write_driver = None
            logger.info("Neo4j WRITE driver closed")

        if cls._read_driver:
            cls._read_driver.close()
            cls._read_driver = None
            logger.info("Neo4j READ driver closed")


class AsyncNeo4jConnectionManager:
    """Singleton manager for Async Neo4j connections."""

    _read_driver: Optional[AsyncDriver] = None

    @classmethod
    async def get_read_driver(cls) -> AsyncDriver:
        """
        Get or create the READ-ONLY async driver for retrieval operations.
        Uses NEO4J_RO_USER credentials.
        """
        if cls._read_driver is None:
            logger.info("Initializing Neo4j Async READ driver with RO credentials")
            cls._read_driver = AsyncGraphDatabase.driver(
                config.neo4j_uri,
                auth=(config.neo4j_ro_user, config.neo4j_ro_password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_timeout=30,
            )
            await cls._verify_connectivity(cls._read_driver, "READ")
        return cls._read_driver

    @classmethod
    async def _verify_connectivity(cls, driver: AsyncDriver, mode: str) -> None:
        """Verify database connectivity."""
        try:
            await driver.verify_connectivity()
            logger.info(f"Neo4j {mode} Async driver connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect Neo4j {mode} Async driver: {e}")
            raise

    @classmethod
    async def close_all(cls) -> None:
        """Close all async database connections."""
        if cls._read_driver:
            await cls._read_driver.close()
            cls._read_driver = None
            logger.info("Neo4j Async READ driver closed")


class Neo4jGraphManager:
    """Singleton manager for LangChain Neo4jGraph wrapper."""

    _instance: Optional[Neo4jGraph] = None

    @classmethod
    def get_graph(cls) -> Neo4jGraph:
        """Get or create the Neo4jGraph singleton."""
        if cls._instance is None:
            logger.info("Initializing Neo4jGraph wrapper with READ-ONLY credentials")
            cls._instance = Neo4jGraph(
                url=config.neo4j_uri,
                username=config.neo4j_ro_user,
                password=config.neo4j_ro_password,
            )
        return cls._instance

    @classmethod
    def close(cls) -> None:
        """Close the graph connection (if possible)."""
        # Neo4jGraph doesn't expose a public close method, but relies on driver.
        # Since we don't own the driver, we let it be collected or handled by the process.
        cls._instance = None


class ChromaDBManager:
    """Singleton manager for ChromaDB vector store."""

    _vectorstore: Optional[Chroma] = None
    _embeddings: Optional[GoogleGenerativeAIEmbeddings] = None

    @classmethod
    def get_embeddings(cls) -> GoogleGenerativeAIEmbeddings:
        """Get or create Google embeddings instance."""
        if cls._embeddings is None:
            logger.info(f"Initializing Google embeddings: {config.embedding_model}")
            cls._embeddings = GoogleGenerativeAIEmbeddings(
                model=config.embedding_model,
                google_api_key=config.google_api_key,
            )
        return cls._embeddings

    @classmethod
    def get_vectorstore(cls) -> Chroma:
        """Get or create ChromaDB vector store."""
        if cls._vectorstore is None:
            logger.info(f"Initializing ChromaDB at: {config.chroma_persist_directory}")
            cls._vectorstore = Chroma(
                collection_name="graphrag_documents",
                embedding_function=cls.get_embeddings(),
                persist_directory=config.chroma_persist_directory,
            )
        return cls._vectorstore

    @classmethod
    def reset_vectorstore(cls) -> None:
        """Reset the vector store (for testing or cleanup)."""
        cls._vectorstore = None


def get_write_graph() -> Driver:
    """
    Get Neo4j driver with WRITE privileges for ingestion.
    This connection uses NEO4J_RW_USER credentials.
    """
    return Neo4jConnectionManager.get_write_driver()


def get_neo4j_graph() -> Neo4jGraph:
    """
    Get Neo4jGraph wrapper for LangChain operations.
    Uses READ-ONLY credentials.
    """
    return Neo4jGraphManager.get_graph()


def get_read_graph() -> Driver:
    """
    Get Neo4j driver with READ-ONLY privileges for retrieval.
    This connection uses NEO4J_RO_USER credentials.
    CRITICAL: This user must be configured with READ-ONLY permissions at the database level.
    """
    return Neo4jConnectionManager.get_read_driver()


async def get_async_read_graph() -> AsyncDriver:
    """
    Get Neo4j async driver with READ-ONLY privileges for retrieval.
    This connection uses NEO4J_RO_USER credentials.
    """
    return await AsyncNeo4jConnectionManager.get_read_driver()


def get_neo4j_graph() -> Neo4jGraph:
    """
    Get or create Neo4j graph wrapper for LangChain with READ-ONLY credentials.
    """
    logger.info("Initializing Neo4j graph wrapper with READ-ONLY credentials")
    return Neo4jGraph(
        url=config.neo4j_uri,
        username=config.neo4j_ro_user,
        password=config.neo4j_ro_password,
    )


def get_vectorstore() -> Chroma:
    """Get ChromaDB vector store."""
    return ChromaDBManager.get_vectorstore()


def close_all_connections() -> None:
    """Close all database connections."""
    Neo4jConnectionManager.close_all()


def initialize_neo4j_schema(driver: Driver) -> None:
    """
    Initialize Neo4j schema with indexes and constraints.
    Only call this with the WRITE driver during setup.
    """
    logger.info("Initializing Neo4j schema...")

    with driver.session() as session:
        try:
            session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)")
            logger.info("Created index on Entity.name")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

        try:
            session.run(
                "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE e.name IS UNIQUE"
            )
            logger.info("Created unique constraint on Entity.name")
        except Exception as e:
            logger.warning(f"Constraint creation warning: {e}")

    logger.info("Neo4j schema initialization complete")



async def close_all_async_connections() -> None:
    """Close all async database connections."""
    await AsyncNeo4jConnectionManager.close_all()
