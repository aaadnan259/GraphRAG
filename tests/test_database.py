"""
Test suite for database connection management (database.py).
Tests Neo4j and ChromaDB connection handling, singleton patterns, and helper functions.
"""

import sys
from unittest.mock import MagicMock, patch

# Mock external dependencies that might not be installed in the test environment
sys.modules["neo4j"] = MagicMock()
sys.modules["langchain_chroma"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()
sys.modules["dotenv"] = MagicMock()

import pytest
import logging
import os

# Ensure config is loaded with dummy values if needed, although conftest handles this.
# But for unit testing the database module in isolation, it's safe to rely on mocked config or env vars.

from database import (
    Neo4jConnectionManager,
    ChromaDBManager,
    get_write_graph,
    get_read_graph,
    get_vectorstore,
    close_all_connections,
    initialize_neo4j_schema,
    verify_read_only_permissions
)
from config import config

class TestNeo4jConnectionManager:
    """Tests for Neo4jConnectionManager."""

    @pytest.fixture(autouse=True)
    def reset_drivers(self):
        """Reset singleton drivers before each test."""
        # Reset the drivers to None to ensure clean state
        Neo4jConnectionManager._write_driver = None
        Neo4jConnectionManager._read_driver = None
        yield
        # Cleanup after test
        Neo4jConnectionManager.close_all()

    def test_get_write_driver_creates_new(self):
        """Test that get_write_driver creates a new driver with RW credentials."""
        # Use the mocked GraphDatabase from sys.modules
        mock_graph_database = sys.modules["neo4j"].GraphDatabase
        # Reset the mock to ensure clean state
        mock_graph_database.reset_mock()

        mock_driver = MagicMock()
        mock_graph_database.driver.return_value = mock_driver

        driver = Neo4jConnectionManager.get_write_driver()

        # Verify driver creation with RW credentials
        mock_graph_database.driver.assert_called_once_with(
            config.neo4j_uri,
            auth=(config.neo4j_rw_user, config.neo4j_rw_password),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_timeout=30,
        )
        # Verify connectivity check
        mock_driver.verify_connectivity.assert_called_once()
        assert driver == mock_driver

    def test_get_write_driver_singleton(self):
        """Test that get_write_driver returns the existing driver if already created."""
        mock_graph_database = sys.modules["neo4j"].GraphDatabase
        mock_graph_database.reset_mock()

        mock_driver = MagicMock()
        mock_graph_database.driver.return_value = mock_driver

        # First call creates the driver
        driver1 = Neo4jConnectionManager.get_write_driver()
        # Second call returns the same instance
        driver2 = Neo4jConnectionManager.get_write_driver()

        assert driver1 is driver2
        # Should only be called once
        assert mock_graph_database.driver.call_count == 1

    def test_get_read_driver_creates_new(self):
        """Test that get_read_driver creates a new driver with RO credentials."""
        mock_graph_database = sys.modules["neo4j"].GraphDatabase
        mock_graph_database.reset_mock()

        mock_driver = MagicMock()
        mock_graph_database.driver.return_value = mock_driver

        driver = Neo4jConnectionManager.get_read_driver()

        # Verify driver creation with RO credentials
        mock_graph_database.driver.assert_called_once_with(
            config.neo4j_uri,
            auth=(config.neo4j_ro_user, config.neo4j_ro_password),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_timeout=30,
        )
        mock_driver.verify_connectivity.assert_called_once()
        assert driver == mock_driver

    def test_get_read_driver_singleton(self):
        """Test that get_read_driver returns the existing driver if already created."""
        mock_graph_database = sys.modules["neo4j"].GraphDatabase
        mock_graph_database.reset_mock()

        mock_driver = MagicMock()
        mock_graph_database.driver.return_value = mock_driver

        driver1 = Neo4jConnectionManager.get_read_driver()
        driver2 = Neo4jConnectionManager.get_read_driver()

        assert driver1 is driver2
        assert mock_graph_database.driver.call_count == 1

    def test_verify_connectivity_failure(self):
        """Test that connectivity failure raises an exception."""
        mock_graph_database = sys.modules["neo4j"].GraphDatabase
        mock_graph_database.reset_mock()

        mock_driver = MagicMock()
        mock_driver.verify_connectivity.side_effect = Exception("Connection failed")
        mock_graph_database.driver.return_value = mock_driver

        with pytest.raises(Exception) as excinfo:
            Neo4jConnectionManager.get_write_driver()

        assert "Connection failed" in str(excinfo.value)

    def test_close_all(self):
        """Test that close_all closes both drivers and resets them."""
        # Setup mocks manually to simulate active connections
        mock_write = MagicMock()
        mock_read = MagicMock()
        Neo4jConnectionManager._write_driver = mock_write
        Neo4jConnectionManager._read_driver = mock_read

        Neo4jConnectionManager.close_all()

        mock_write.close.assert_called_once()
        mock_read.close.assert_called_once()
        assert Neo4jConnectionManager._write_driver is None
        assert Neo4jConnectionManager._read_driver is None


class TestChromaDBManager:
    """Tests for ChromaDBManager."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self):
        """Reset singleton instances before each test."""
        ChromaDBManager._vectorstore = None
        ChromaDBManager._embeddings = None
        yield
        ChromaDBManager._vectorstore = None
        ChromaDBManager._embeddings = None

    def test_get_embeddings_creates_new(self):
        """Test that get_embeddings creates a new embeddings instance."""
        mock_google_genai = sys.modules["langchain_google_genai"].GoogleGenerativeAIEmbeddings
        mock_google_genai.reset_mock()
        mock_instance = MagicMock()
        mock_google_genai.return_value = mock_instance

        embeddings = ChromaDBManager.get_embeddings()

        mock_google_genai.assert_called_once_with(
            model=config.embedding_model,
            google_api_key=config.google_api_key,
        )
        assert embeddings == mock_instance

    def test_get_embeddings_singleton(self):
        """Test that get_embeddings returns the existing instance."""
        mock_google_genai = sys.modules["langchain_google_genai"].GoogleGenerativeAIEmbeddings
        mock_google_genai.reset_mock()

        emb1 = ChromaDBManager.get_embeddings()
        emb2 = ChromaDBManager.get_embeddings()

        assert emb1 is emb2
        assert mock_google_genai.call_count == 1

    def test_get_vectorstore_creates_new(self):
        """Test that get_vectorstore creates a new Chroma instance."""
        mock_chroma = sys.modules["langchain_chroma"].Chroma
        mock_chroma.reset_mock()
        mock_instance = MagicMock()
        mock_chroma.return_value = mock_instance

        # Mock embeddings to avoid dependency
        with patch.object(ChromaDBManager, 'get_embeddings') as mock_get_embeddings:
            mock_emb = MagicMock()
            mock_get_embeddings.return_value = mock_emb

            vectorstore = ChromaDBManager.get_vectorstore()

            mock_chroma.assert_called_once_with(
                collection_name="graphrag_documents",
                embedding_function=mock_emb,
                persist_directory=config.chroma_persist_directory,
            )
            assert vectorstore == mock_instance

    def test_get_vectorstore_singleton(self):
        """Test that get_vectorstore returns the existing instance."""
        mock_chroma = sys.modules["langchain_chroma"].Chroma
        mock_chroma.reset_mock()

        with patch.object(ChromaDBManager, 'get_embeddings'):
            vs1 = ChromaDBManager.get_vectorstore()
            vs2 = ChromaDBManager.get_vectorstore()

            assert vs1 is vs2
            assert mock_chroma.call_count == 1

    def test_reset_vectorstore(self):
        """Test that reset_vectorstore clears the singleton."""
        # Set a dummy value
        ChromaDBManager._vectorstore = MagicMock()

        ChromaDBManager.reset_vectorstore()

        assert ChromaDBManager._vectorstore is None


class TestHelperFunctions:
    """Tests for helper functions in database.py."""

    def test_get_write_graph(self):
        """Test get_write_graph delegates to Neo4jConnectionManager."""
        with patch.object(Neo4jConnectionManager, 'get_write_driver') as mock_method:
            mock_driver = MagicMock()
            mock_method.return_value = mock_driver

            result = get_write_graph()

            assert result == mock_driver
            mock_method.assert_called_once()

    def test_get_read_graph(self):
        """Test get_read_graph delegates to Neo4jConnectionManager."""
        with patch.object(Neo4jConnectionManager, 'get_read_driver') as mock_method:
            mock_driver = MagicMock()
            mock_method.return_value = mock_driver

            result = get_read_graph()

            assert result == mock_driver
            mock_method.assert_called_once()

    def test_get_vectorstore(self):
        """Test get_vectorstore delegates to ChromaDBManager."""
        with patch.object(ChromaDBManager, 'get_vectorstore') as mock_method:
            mock_vs = MagicMock()
            mock_method.return_value = mock_vs

            result = get_vectorstore()

            assert result == mock_vs
            mock_method.assert_called_once()

    def test_close_all_connections(self):
        """Test close_all_connections delegates to Neo4jConnectionManager."""
        with patch.object(Neo4jConnectionManager, 'close_all') as mock_method:
            close_all_connections()
            mock_method.assert_called_once()

    def test_initialize_neo4j_schema(self):
        """Test initialization of Neo4j schema."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        initialize_neo4j_schema(mock_driver)

        # Should execute CREATE INDEX and CREATE CONSTRAINT
        assert mock_session.run.call_count == 2

        calls = mock_session.run.call_args_list
        assert "CREATE INDEX" in calls[0][0][0]
        assert "CREATE CONSTRAINT" in calls[1][0][0]

    def test_initialize_neo4j_schema_handles_errors(self):
        """Test that schema initialization handles errors gracefully."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Simulate exception on first call
        mock_session.run.side_effect = Exception("DB Error")

        # Should not raise exception
        initialize_neo4j_schema(mock_driver)

        assert mock_session.run.called

    def test_verify_read_only_permissions_success(self):
        """Test verification when permission is denied (successful RO check)."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Simulate exception when trying to write (Good behavior for RO user)
        mock_session.run.side_effect = Exception("ClientError: Permission denied")

        result = verify_read_only_permissions(mock_driver)

        assert result is True

    def test_verify_read_only_permissions_failure(self):
        """Test verification when write succeeds (failure of RO check)."""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Simulate successful write (Bad behavior for RO user)
        mock_session.run.return_value = None

        result = verify_read_only_permissions(mock_driver)

        assert result is False
