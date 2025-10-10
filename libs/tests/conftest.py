"""Global test configuration for all tests.

This conftest.py is at the root of the tests directory and applies to all test modules.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def disable_usage_tracking():
    """Disable CLI usage tracking for all tests.

    This prevents test runs from sending analytics events to PostHog.
    The fixture is autouse=True so it applies automatically to every test.
    """
    original_value = os.environ.get("ARCADE_USAGE_TRACKING")

    # Disable tracking
    os.environ["ARCADE_USAGE_TRACKING"] = "0"

    yield

    # Restore original value after test
    if original_value is None:
        os.environ.pop("ARCADE_USAGE_TRACKING", None)
    else:
        os.environ["ARCADE_USAGE_TRACKING"] = original_value
