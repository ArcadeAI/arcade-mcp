"""Global test configuration for all tests.

This conftest.py is at the root of the tests directory and applies to all test modules.
"""

import os
import socket
import tempfile
from contextvars import ContextVar
from unittest.mock import Mock

# Point the config directory at a throwaway path before anything imports
# arcade_core. ARCADE_CONFIG_PATH is bound at import, so a fixture cannot
# redirect it later -- a test that reaches for the constant would write to the
# developer's real credentials file. Covers every way the suite is started,
# including the single-test command in CLAUDE.md, not just `make test`.
_test_config_dir = tempfile.TemporaryDirectory(prefix="arcade-test-config-")
os.environ.setdefault("ARCADE_WORK_DIR", _test_config_dir.name)

import pytest  # noqa: E402

# Check if eval dependencies are available
try:
    import anthropic  # noqa: F401
    import openai  # noqa: F401

    EVALS_DEPS_AVAILABLE = True
except ImportError:
    EVALS_DEPS_AVAILABLE = False


@pytest.fixture
def offline_socket_guard(monkeypatch):
    """Reject network connections while retaining Windows asyncio socketpairs."""
    blocked = Mock(side_effect=AssertionError("Unexpected network"))
    creating_socketpair = ContextVar("creating_socketpair", default=False)
    original_connect = socket.socket.connect
    original_socketpair = socket.socketpair

    def guarded_connect(sock, address):
        if creating_socketpair.get():
            return original_connect(sock, address)
        return blocked(address)

    def guarded_socketpair(*args, **kwargs):
        # Windows implements socketpair with a local TCP connection. Permit
        # only this synchronous stdlib call, never arbitrary localhost traffic.
        token = creating_socketpair.set(True)
        try:
            return original_socketpair(*args, **kwargs)
        finally:
            creating_socketpair.reset(token)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "socketpair", guarded_socketpair)
    yield blocked
    blocked.assert_not_called()


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
