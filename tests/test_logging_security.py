
import sys
import asyncio
from unittest.mock import MagicMock, patch

# Mock tenacity correctly to be transparent
mock_tenacity = MagicMock()
def passthrough_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

mock_tenacity.retry = passthrough_decorator
mock_tenacity.stop_after_attempt = MagicMock()
mock_tenacity.wait_exponential = MagicMock()
mock_tenacity.retry_if_exception_type = MagicMock()
sys.modules['tenacity'] = mock_tenacity

# Mock other dependencies
sys.modules['langchain_google_genai'] = MagicMock()
sys.modules['langchain.prompts'] = MagicMock()
sys.modules['langchain_community.graphs'] = MagicMock()
sys.modules['langchain.chains'] = MagicMock()
sys.modules['neo4j'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['langchain_chroma'] = MagicMock()
sys.modules['pydantic'] = MagicMock()
sys.modules['database'] = MagicMock()
sys.modules['config'] = MagicMock()
sys.modules['models'] = MagicMock()

import logging
from retriever import HybridRetriever

def test_logging_levels():
    # Setup mock logger
    with patch('retriever.logger') as mock_logger:
        retriever = HybridRetriever()

        # 1. Test _vector_search_sync
        try:
            retriever._vector_search_sync("vector query")
        except:
            pass

        debug_calls = [str(call.args[0]) for call in mock_logger.debug.call_args_list]
        info_calls = [str(call.args[0]) for call in mock_logger.info.call_args_list]
        assert any("Performing vector search for: vector query" in call for call in debug_calls)
        assert not any("Performing vector search for: vector query" in call for call in info_calls)

        mock_logger.reset_mock()

        # 2. Test _graph_search (async)
        async def run_graph_search():
            try:
                await retriever._graph_search("graph query")
            except Exception as e:
                # print(f"Caught exception in graph search: {e}")
                pass

        asyncio.run(run_graph_search())
        debug_calls = [str(call.args[0]) for call in mock_logger.debug.call_args_list]
        info_calls = [str(call.args[0]) for call in mock_logger.info.call_args_list]
        assert any("Performing graph search for: graph query" in call for call in debug_calls)
        assert not any("Performing graph search for: graph query" in call for call in info_calls)

        mock_logger.reset_mock()

        # 3. Test retrieve
        mock_request = MagicMock()
        mock_request.query = "retrieve query"

        async def run_retrieve():
             try:
                 await retriever.retrieve(mock_request)
             except Exception as e:
                 # print(f"Caught exception in retrieve: {e}")
                 pass

        asyncio.run(run_retrieve())

        debug_calls = [str(call.args[0]) for call in mock_logger.debug.call_args_list]
        info_calls = [str(call.args[0]) for call in mock_logger.info.call_args_list]
        assert any("Processing query: retrieve query" in call for call in debug_calls)
        assert not any("Processing query: retrieve query" in call for call in info_calls)

        mock_logger.reset_mock()

        # 4. Test search_entities
        async def run_search_entities():
            try:
                await retriever.search_entities("entity pattern")
            except Exception as e:
                # print(f"Caught exception in search entities: {e}")
                pass

        asyncio.run(run_search_entities())
        debug_calls = [str(call.args[0]) for call in mock_logger.debug.call_args_list]
        info_calls = [str(call.args[0]) for call in mock_logger.info.call_args_list]
        assert any("Searching entities matching: entity pattern" in call for call in debug_calls)
        assert not any("Searching entities matching: entity pattern" in call for call in info_calls)

        print("Logging level verification PASSED for all methods")

if __name__ == "__main__":
    test_logging_levels()
