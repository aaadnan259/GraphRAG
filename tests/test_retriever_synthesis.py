"""
Test suite for answer synthesis retry mechanism (retriever.py).
"""

import sys
from unittest.mock import Mock, MagicMock, AsyncMock, patch

# Mock external dependencies if not present (defensive)
# Note: run_tests.py might have already mocked these
if "langchain_google_genai" not in sys.modules:
    sys.modules["langchain_google_genai"] = MagicMock()
if "langchain_community.graphs" not in sys.modules:
    sys.modules["langchain_community.graphs"] = MagicMock()
if "langchain.chains" not in sys.modules:
    sys.modules["langchain.chains"] = MagicMock()
if "langchain.prompts" not in sys.modules:
    sys.modules["langchain.prompts"] = MagicMock()
if "neo4j" not in sys.modules:
    sys.modules["neo4j"] = MagicMock()
if "langchain_chroma" not in sys.modules:
    sys.modules["langchain_chroma"] = MagicMock()

import pytest
import asyncio
from retriever import HybridRetriever

class TestSynthesisRetry:
    """Test retry mechanism for answer synthesis."""

    @pytest.fixture
    def retriever(self):
        """Create retriever with mocked dependencies."""
        with patch('retriever.get_read_graph', return_value=MagicMock()), \
             patch('retriever.get_async_read_graph', new_callable=AsyncMock, return_value=MagicMock()), \
             patch('retriever.get_vectorstore', return_value=MagicMock()), \
             patch('retriever.ChatGoogleGenerativeAI') as mock_llm_class:

            mock_llm = AsyncMock()
            mock_llm_class.return_value = mock_llm

            retriever = HybridRetriever()
            retriever.llm = mock_llm  # Explicitly set the instance mock
            return retriever

    @pytest.mark.asyncio
    async def test_synthesize_answer_retries(self, retriever):
        """Test that answer synthesis retries on failure."""

        # Setup the mock to fail first, then succeed
        mock_response = Mock()
        mock_response.content = "Final Answer"

        # First call raises Exception, second returns response
        retriever.llm.ainvoke.side_effect = [Exception("Temporary LLM error"), mock_response]

        # Call the method
        answer = await retriever._synthesize_answer(
            query="test query",
            vector_context=["ctx1"],
            graph_context="ctx2"
        )

        # Assertions
        assert answer == "Final Answer"
        assert retriever.llm.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_synthesize_answer_exhaustion(self, retriever):
        """Test that answer synthesis raises exception after max retries."""

        # Setup the mock to always fail
        retriever.llm.ainvoke.side_effect = Exception("Persistent LLM error")

        # Call the method and expect exception
        with pytest.raises(Exception, match="Persistent LLM error"):
            await retriever._synthesize_answer(
                query="test query",
                vector_context=["ctx1"],
                graph_context="ctx2"
            )

        # Should have retried 3 times (stop_after_attempt(3))
        # Note: Since tenacity wraps the function, if it fails 3 times, it re-raises the last exception.
        assert retriever.llm.ainvoke.call_count == 3
