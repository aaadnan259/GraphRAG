import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from api import app
from httpx import AsyncClient, ASGITransport
from retriever import HybridRetriever

@pytest.mark.asyncio
async def test_search_entities_is_non_blocking():
    # Mock dependencies to avoid DB connection
    mock_async_driver = MagicMock() # Use MagicMock because driver.session() is synchronous (returns context manager)
    mock_session = AsyncMock()

    # Configure session as async context manager
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    mock_async_driver.session.return_value = mock_session

    # Define a slow async query (simulating network latency)
    async def slow_query(*args, **kwargs):
        await asyncio.sleep(1) # Yields control
        mock_result = AsyncMock()
        mock_result.data.return_value = [{"name": "Slow Entity"}]
        return mock_result

    mock_session.run.side_effect = slow_query

    with patch('retriever.get_read_graph'), \
         patch('retriever.get_async_read_graph', return_value=mock_async_driver), \
         patch('retriever.get_vectorstore'), \
         patch('retriever.ChatGoogleGenerativeAI'), \
         patch('retriever.ChatPromptTemplate'):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:

            # Launch the search request
            start_time = time.time()
            task_search = asyncio.create_task(client.get("/search/entities?query=test"))

            # Concurrently, run a fast generic task
            # If search is blocking the loop (CPU bound or sync IO), this task won't start until search finishes.
            # Since search uses await asyncio.sleep(1), it should yield, allowing this task to run.

            await asyncio.sleep(0.1)

            mid_time = time.time()

            # If loop was blocked, mid_time - start_time would be > 1s (approx).
            # If yielding, it should be around 0.1s.

            assert (mid_time - start_time) < 0.5, "Event loop was blocked!"

            response = await task_search
            assert response.status_code == 200
