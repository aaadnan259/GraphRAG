"""
Neo4j and ChromaDB connection management.
"""

import logging
from typing import Optional
from neo4j import GraphDatabase, Driver
from langchain_chroma import Chroma
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


def get_read_graph() -> Driver:
    """
    Get Neo4j driver with READ-ONLY privileges for retrieval.
    This connection uses NEO4J_RO_USER credentials.
    CRITICAL: This user must be configured with READ-ONLY permissions at the database level.
    """
    return Neo4jConnectionManager.get_read_driver()


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


def verify_read_only_permissions(driver: Driver) -> bool:
    """
    Verify that the read-only user cannot perform write operations.
    Returns True if properly restricted, False otherwise.
    """
    logger.info("Verifying read-only permissions...")

    with driver.session() as session:
        try:
            session.run("CREATE (test:TestNode {name: 'security_check'})")
            session.run("MATCH (test:TestNode {name: 'security_check'}) DELETE test")
            logger.error("SECURITY VIOLATION: Read-only user can perform write operations!")
            return False
        except Exception as e:
            logger.info(f"Read-only verification passed: {e}")
            return True
