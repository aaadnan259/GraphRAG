
import asyncio
import tracemalloc
import os
import sys
import time
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Mock modules that might be missing or not needed for this specific benchmark
sys.modules["neo4j"] = MagicMock()
sys.modules["langchain_chroma"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()

# Set environment variables for config
os.environ.setdefault("GOOGLE_API_KEY", "dummy")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_RW_USER", "neo4j")
os.environ.setdefault("NEO4J_RW_PASSWORD", "password")
os.environ.setdefault("NEO4J_RO_USER", "neo4j")
os.environ.setdefault("NEO4J_RO_PASSWORD", "password")

from fastapi import UploadFile
from api import ingest_document

async def benchmark_api_memory():
    # Create a large dummy file (in memory for the test, but treated as stream by FastAPI)
    file_size = 50 * 1024 * 1024  # 50MB
    content = b"a" * file_size

    # Mock UploadFile
    class MockUploadFile(UploadFile):
        def __init__(self, data):
            self.data = data
            self.pos = 0
            self.filename = "test.txt"
            self.size = len(data)

        async def read(self, size=-1):
            if size == -1:
                res = self.data[self.pos:]
                self.pos = self.size
                return res

            # Simulate reading logic
            if self.pos >= self.size:
                return b""

            res = self.data[self.pos:self.pos+size]
            self.pos += size
            return res

    mock_file = MockUploadFile(content)

    # Mock Ingestor
    # We patch os.environ to allow large files
    with patch("api.Ingestor") as MockIngestor, \
         patch.dict(os.environ, {"MAX_FILE_SIZE": str(100 * 1024 * 1024)}):

        instance = MockIngestor.return_value
        instance.ingest = MagicMock()

        async def mock_ingest(input_data, filename):
            # Consume the generator if it is one
            # To measure memory usage during consumption
            chunk_count = 0
            total_len = 0
            if hasattr(input_data, "__aiter__"):
                async for chunk in input_data:
                    chunk_count += 1
                    total_len += len(chunk)
            else:
                total_len = len(input_data)

            return {"success": True, "processed_len": total_len}

        instance.ingest.side_effect = mock_ingest
        instance.init_schema = MagicMock()

        print(f"Starting benchmark with {file_size/1024/1024:.2f}MB file...")

        tracemalloc.start()
        start_time = time.time()

        try:
            await ingest_document(mock_file)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        print(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")
        print(f"Time taken: {time.time() - start_time:.2f} s")

if __name__ == "__main__":
    asyncio.run(benchmark_api_memory())
