
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

# Tenacity is now installed and needed for retry tests
# sys.modules['tenacity'] = MagicMock()

# Mock pydantic
mock_pydantic = MagicMock()
mock_pydantic.BaseModel = MagicMock
mock_pydantic.Field = MagicMock
mock_pydantic.field_validator = passthrough_decorator
sys.modules['pydantic'] = mock_pydantic

sys.modules['fastapi'] = MagicMock()

import pytest
import os

if __name__ == "__main__":
    # Add current directory to path
    sys.path.append(os.getcwd())

    # Set environment variables to disable retry wait
    os.environ["RETRY_MIN_WAIT"] = "0"
    os.environ["RETRY_MAX_WAIT"] = "0"

    # Run pytest on the modified test file
    sys.exit(pytest.main(["tests/test_retriever.py", "tests/test_retriever_synthesis.py"]))
