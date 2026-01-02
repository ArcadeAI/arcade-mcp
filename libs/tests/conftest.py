"""Global test configuration for all tests.

This conftest.py is at the root of the tests directory and applies to all test modules.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def isolate_environment():
    """Isolate environment variables for each test.

    This fixture captures the entire environment before a test and restores it
    after. This ensures that environment variables set by load_dotenv() or any
    other mechanism during tests don't leak into subsequent tests.

    This also disables CLI usage tracking to prevent test runs from sending
    analytics events to PostHog.
    """
    original_env = os.environ.copy()

    # Disable tracking
    os.environ["ARCADE_USAGE_TRACKING"] = "0"

    yield

    # Restore the original environment
    os.environ.clear()
    os.environ.update(original_env)
