
import sys
from unittest.mock import MagicMock
import pytest

# Mock missing dependencies that are not needed for API tests
# API tests need fastapi, but not the heavy backend libraries like langchain, neo4j, etc.
# Note: Ingestor is mocked inside the tests, but importing 'api' triggers imports of 'ingest', 'retriever', etc.
# So we need to mock their dependencies.

sys.modules['langchain'] = MagicMock()
sys.modules['langchain.text_splitter'] = MagicMock()
sys.modules['langchain.schema'] = MagicMock()
sys.modules['langchain_google_genai'] = MagicMock()
sys.modules['langchain.prompts'] = MagicMock()
sys.modules['langchain_community.graphs'] = MagicMock()
sys.modules['langchain.chains'] = MagicMock()
sys.modules['neo4j'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['langchain_chroma'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

# Mock tenacity to be transparent
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

# IMPORTANT: Do NOT mock fastapi here. It must be installed in the environment.

if __name__ == "__main__":
    # Add current directory to path
    import os
    sys.path.append(os.getcwd())

    # Default to running API ingest tests if no arguments provided
    args = sys.argv[1:] if len(sys.argv) > 1 else ["tests/test_api_ingest.py"]
    sys.exit(pytest.main(args))
