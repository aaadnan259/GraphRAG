
"""
Benchmark script for graph statistics retrieval.
Measures the latency and number of database calls.
"""

import time
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment variables before importing config/retriever
os.environ['GOOGLE_API_KEY'] = 'dummy'
os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
os.environ['NEO4J_RW_USER'] = 'neo4j'
os.environ['NEO4J_RW_PASSWORD'] = 'password'
os.environ['NEO4J_RO_USER'] = 'reader'
os.environ['NEO4J_RO_PASSWORD'] = 'password'

# Mock missing dependencies to allow import in restricted environments
# This block is only needed if running without full dependencies installed
try:
    import langchain_google_genai
except ImportError:
    sys.modules['langchain_google_genai'] = MagicMock()
    sys.modules['langchain.prompts'] = MagicMock()
    sys.modules['langchain_community.graphs'] = MagicMock()
    sys.modules['langchain.chains'] = MagicMock()
    sys.modules['tenacity'] = MagicMock()
    sys.modules['neo4j'] = MagicMock()
    sys.modules['dotenv'] = MagicMock()
    sys.modules['langchain_chroma'] = MagicMock()

    # Mock tenacity decorators to be pass-through
    mock_tenacity = MagicMock()
    def passthrough_decorator(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    mock_tenacity.retry = passthrough_decorator
    sys.modules['tenacity'] = mock_tenacity

from retriever import HybridRetriever

# Mock payload to simulate network latency
DELAY = 0.1  # 100ms simulated latency per call

class MockSession:
    def __init__(self):
        self.call_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def run(self, query, **kwargs):
        time.sleep(DELAY)  # Simulate network latency
        self.call_count += 1

        mock_result = MagicMock()

        # Determine what to return based on the query content
        query_strip = query.strip()

        if query_strip.startswith("CALL {"):
             # New optimized query (starts with CALL)
             mock_result.single.return_value = {
                 "entity_count": 100,
                 "rel_count": 50,
                 "entity_types": {"PERSON": 10, "ORG": 5},
                 "rel_types": {"KNOWS": 20}
             }
        elif "MATCH (e:Entity) RETURN count(e)" in query:
            # Old query style (simple match)
            mock_result.single.return_value = {"count": 100}
        else:
            # Fallback for other old queries
             mock_result.single.return_value = {"count": 50} # rel count etc
             mock_result.values.return_value = [] # types

        return mock_result

def benchmark():
    print("Initializing benchmark...")

    # Mock the driver
    mock_driver = MagicMock()
    mock_session = MockSession()
    mock_driver.session.return_value = mock_session

    # Patch the get_read_graph to return our mock
    with patch('retriever.get_read_graph', return_value=mock_driver), \
         patch('retriever.get_vectorstore'), \
         patch('retriever.ChatGoogleGenerativeAI'):

        try:
            retriever = HybridRetriever()
            # Ensure the read_driver is our mock
            retriever._read_driver = mock_driver

            print("Running retrieval...")
            start_time = time.time()
            # calling the sync method directly to avoid thread pool overhead in benchmark
            stats = retriever._get_graph_statistics_sync()
            end_time = time.time()

            duration = end_time - start_time
            print(f"Time taken: {duration:.4f} seconds")
            print(f"Calls made: {mock_session.call_count}")

            # Validation
            if mock_session.call_count == 1:
                print("SUCCESS: Optimized (1 call)")
            elif mock_session.call_count >= 4:
                print("BASELINE: Unoptimized (4+ calls)")
            else:
                print(f"WARNING: Unexpected call count ({mock_session.call_count})")

        except Exception as e:
            print(f"Error during benchmark: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    benchmark()
