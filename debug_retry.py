
import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_exponential

# Simulate config
class Config:
    @property
    def retry_min_wait(self):
        return int(os.getenv("RETRY_MIN_WAIT", "1"))
    @property
    def retry_max_wait(self):
        return int(os.getenv("RETRY_MAX_WAIT", "10"))

config = Config()

class Retriever:
    def _graph_search_sync(self, query):
        raise NotImplementedError("Should be mocked")

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
    async def _graph_search(self, query):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._graph_search_sync, query)

async def test():
    r = Retriever()
    with patch.object(r, '_graph_search_sync') as mock_sync:
        mock_sync.side_effect = [Exception("Fail"), "Success"]

        try:
            print("Calling _graph_search...")
            res = await r._graph_search("test")
            print(f"Result: {res}")
            print(f"Call count: {mock_sync.call_count}")
        except Exception as e:
            print(f"Caught exception: {e}")
            print(f"Call count: {mock_sync.call_count}")

if __name__ == "__main__":
    asyncio.run(test())
