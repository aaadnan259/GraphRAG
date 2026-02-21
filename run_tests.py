
import sys
from unittest.mock import MagicMock

# Mock missing dependencies
sys.modules['langchain_google_genai'] = MagicMock()
sys.modules['langchain.prompts'] = MagicMock()
sys.modules['langchain_community.graphs'] = MagicMock()
sys.modules['langchain.chains'] = MagicMock()
sys.modules['neo4j'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['langchain_chroma'] = MagicMock()

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

# No need to mock pydantic as it is installed
sys.modules['fastapi'] = MagicMock()

import pytest

if __name__ == "__main__":
    # Add current directory to path
    import os
    sys.path.append(os.getcwd())

    # Run pytest on the modified test file
    sys.exit(pytest.main(["tests/test_retriever.py"]))
