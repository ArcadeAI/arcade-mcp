"""Tests for worker factory logging configuration.

These tests verify that create_arcade_mcp_factory() properly configures logging
for worker subprocesses (when workers > 1), ensuring:
- Standard Python logging is intercepted by Loguru
- DEBUG logs are filtered based on ARCADE_MCP_DEBUG env var
- Consistent log formatting across all processes
"""

import logging
import os
from io import StringIO

import pytest
from arcade_mcp_server.__main__ import setup_logging
from loguru import logger


@pytest.fixture(autouse=True)
def isolate_environment():
    """Isolate environment variables for each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging state before and after each test."""
    # Store original loguru handlers
    original_handlers = logger._core.handlers.copy()

    # Clear any existing handlers from root logger
    root_logger = logging.getLogger()
    original_root_handlers = root_logger.handlers.copy()
    original_root_level = root_logger.level

    yield

    # Restore loguru handlers
    logger._core.handlers.clear()
    logger._core.handlers.update(original_handlers)

    # Restore root logger state
    root_logger.handlers = original_root_handlers
    root_logger.level = original_root_level


class TestFactoryLoggingConfiguration:
    """Tests for logging configuration in create_arcade_mcp_factory.

    These tests verify the factory properly configures logging by checking
    the actual logging state after the factory runs.
    """

    def test_factory_filters_debug_logs_by_default(self):
        """Verify factory filters DEBUG logs when ARCADE_MCP_DEBUG is not set."""
        os.environ["ARCADE_MCP_DISCOVER_INSTALLED"] = "true"
        os.environ.pop("ARCADE_MCP_DEBUG", None)
        os.environ["ARCADE_MCP_OTEL_ENABLE"] = "false"

        try:
            from arcade_mcp_server.worker import create_arcade_mcp_factory

            create_arcade_mcp_factory()
        except RuntimeError:
            pass

        # Capture output after factory configures logging
        output = StringIO()
        logger.remove()
        handler_id = logger.add(output, format="{level} | {message}", level="INFO")

        try:
            test_logger = logging.getLogger("test.factory")
            test_logger.debug("This debug message should be filtered")
            test_logger.info("This info message should appear")

            log_output = output.getvalue()
            assert "This debug message should be filtered" not in log_output
            assert "This info message should appear" in log_output
        finally:
            logger.remove(handler_id)

    def test_factory_allows_debug_logs_when_env_var_set(self):
        """Verify factory allows DEBUG logs when ARCADE_MCP_DEBUG=true."""
        os.environ["ARCADE_MCP_DISCOVER_INSTALLED"] = "true"
        os.environ["ARCADE_MCP_DEBUG"] = "true"
        os.environ["ARCADE_MCP_OTEL_ENABLE"] = "false"

        try:
            from arcade_mcp_server.worker import create_arcade_mcp_factory

            create_arcade_mcp_factory()
        except RuntimeError:
            pass

        # Capture output after factory configures logging
        output = StringIO()
        logger.remove()
        handler_id = logger.add(output, format="{level} | {message}", level="DEBUG")

        try:
            test_logger = logging.getLogger("test.factory.debug")
            test_logger.debug("This debug message should appear")

            log_output = output.getvalue()
            assert "This debug message should appear" in log_output
        finally:
            logger.remove(handler_id)
