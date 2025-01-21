import os

import pytest
from arcadepy import Arcade


@pytest.fixture(scope="session")
def arcade_base_url():
    """
    Retrieve the ARCADE_BASE_URL from the environment, falling back to a default
    if not found.
    """
    return os.getenv("ARCADE_BASE_URL", "http://localhost:9099")


@pytest.fixture(scope="session")
def arcade_api_key():
    """
    Retrieve the ARCADE_API_KEY from the environment, falling back to a default
    if not found.
    """
    return os.getenv("ARCADE_API_KEY", "test_api_key")


@pytest.fixture(scope="session")
def arcade_client(arcade_base_url, arcade_api_key):
    """
    Creates a single Arcade client instance for use in all tests.
    Any method calls on this client can be patched/mocked within the tests.
    """
    client = Arcade(api_key=arcade_api_key, base_url=arcade_base_url)
    yield client
    # Teardown logic would go here if necessary
