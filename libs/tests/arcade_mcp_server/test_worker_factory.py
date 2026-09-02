import logging
import os
from io import StringIO

import pytest
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


class TestFactoryResourceCountLog:
    """The startup line that says how many resources were discovered.

    All of the resource plumbing can be correct and a deployment still serve an
    empty catalog because no toolkit declared anything. This line is how that is
    noticed, so it is worth holding in place.
    """

    def test_factory_logs_the_resource_count(self, monkeypatch):
        import contextlib
        from typing import Annotated

        from arcade_core.catalog import ToolCatalog
        from arcade_core.resource_schema import Resource
        from arcade_mcp_server import worker as worker_module
        from arcade_tdk import ToolContext, tool

        @tool()
        def a_tool(context: ToolContext, x: Annotated[int, "x"]) -> Annotated[str, "out"]:
            """A fixture tool, so the factory gets past its zero-tools guard."""
            return str(x)

        catalog = ToolCatalog()
        catalog.add_tool(a_tool, "fixture_kit")
        catalog.resources.add(
            Resource(uri="ui://k/1.0.0/a.html", name="a", mimeType="text/html"), "<html>"
        )
        monkeypatch.setattr(worker_module, "discover_tools", lambda **kwargs: catalog)
        # setup_logging() opens with logger.remove(), which would drop the sink below.
        monkeypatch.setattr(worker_module, "setup_logging", lambda **kwargs: None)
        os.environ["ARCADE_MCP_OTEL_ENABLE"] = "false"

        output = StringIO()
        handler_id = logger.add(output, format="{message}", level="INFO")
        try:
            try:
                worker_module.create_arcade_mcp_factory()
            except Exception:
                # The factory keeps building an app after logging; the line is the subject.
                pass
            assert "Total resources loaded: 1" in output.getvalue()
        finally:
            with contextlib.suppress(ValueError):
                logger.remove(handler_id)
