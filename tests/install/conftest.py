"""Test configuration for installation tests.

Mirrors the autouse fixtures in libs/tests/conftest.py so that
`pytest tests/install/` benefits from the same env setup as the
unit/integration test suites.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def disable_usage_tracking() -> None:
    """Disable CLI usage tracking for all installation tests.

    Prevents test runs from sending analytics events to PostHog.
    Mirrors the same fixture in libs/tests/conftest.py.
    """
    original_value = os.environ.get("ARCADE_USAGE_TRACKING")

    os.environ["ARCADE_USAGE_TRACKING"] = "0"

    yield

    if original_value is None:
        os.environ.pop("ARCADE_USAGE_TRACKING", None)
    else:
        os.environ["ARCADE_USAGE_TRACKING"] = original_value
