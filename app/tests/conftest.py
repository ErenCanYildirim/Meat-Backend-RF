import pytest
import asyncio
import os
from unittest.mock import patch


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True, scope="session")
def mock_static_directory():
    """Mock static directory existence check before app import"""
    with patch("os.path.exists") as mock_exists:
        original_exists = os.path.exists

        def side_effect(path):
            if "app/static" in str(path) or path.endswith("static"):
                return True
            return original_exists(path)

        mock_exists.side_effect = side_effect
        yield
