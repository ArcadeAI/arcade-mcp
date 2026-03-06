"""Global test configuration for all tests.

This conftest.py is at the root of the tests directory and applies to all test modules.
"""

import os

import pytest

# Check if eval dependencies are available
try:
    import anthropic  # noqa: F401
    import openai  # noqa: F401

    EVALS_DEPS_AVAILABLE = True
except ImportError:
    EVALS_DEPS_AVAILABLE = False


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "evals: marks tests that require eval dependencies (openai, anthropic, mcp)"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip evals tests if dependencies not available.

    Tests are detected as evals tests if they have the @pytest.mark.evals marker.

    """
    skip_evals = pytest.mark.skip(
        reason="Evals dependencies not installed. Install with: uv tool install 'arcade-mcp[evals]'"
    )

    for item in items:
        # Check if test has the @pytest.mark.evals marker
        if item.get_closest_marker("evals") and not EVALS_DEPS_AVAILABLE:
            item.add_marker(skip_evals)


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
