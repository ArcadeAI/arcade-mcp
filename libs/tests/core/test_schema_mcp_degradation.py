"""
Tests for MCP feature graceful degradation in ToolContext.

This module tests that:
1. Non-critical MCP features (log, progress) silently no-op in deployed environments
2. Critical MCP features (resources, tools, etc.) raise informative errors
"""

import pytest
from arcade_core.schema import ToolContext

# =====================
# Non-Critical Features (No-Op Tests)
# =====================


@pytest.mark.asyncio
async def test_log_debug_no_op():
    """Test that context.log.debug() executes without error."""
    context = ToolContext()
    # Should not raise any exception
    await context.log.debug("test message")


@pytest.mark.asyncio
async def test_log_info_no_op():
    """Test that context.log.info() executes without error."""
    context = ToolContext()
    # Should not raise any exception
    await context.log.info("test message")


@pytest.mark.asyncio
async def test_log_warning_no_op():
    """Test that context.log.warning() executes without error."""
    context = ToolContext()
    # Should not raise any exception
    await context.log.warning("test message")


@pytest.mark.asyncio
async def test_log_error_no_op():
    """Test that context.log.error() executes without error."""
    context = ToolContext()
    # Should not raise any exception
    await context.log.error("test message")


@pytest.mark.asyncio
async def test_log_log_no_op():
    """Test that context.log.log() executes without error."""
    context = ToolContext()
    # Should not raise any exception
    await context.log.log("info", "test message")


@pytest.mark.asyncio
async def test_log_with_extra_kwargs_no_op():
    """Test that context.log methods with extra kwargs execute without error."""
    context = ToolContext()
    # Should not raise any exception
    await context.log.info("test message", logger_name="test_logger", extra={"key": "value"})


@pytest.mark.asyncio
async def test_progress_report_no_op():
    """Test that context.progress.report() executes without error."""
    context = ToolContext()
    # Should not raise any exception
    await context.progress.report(0.5, total=1.0, message="Halfway done")


@pytest.mark.asyncio
async def test_progress_report_minimal_no_op():
    """Test that context.progress.report() with minimal params executes without error."""
    context = ToolContext()
    # Should not raise any exception
    await context.progress.report(0.5)


# =====================
# Critical Features (Error Tests)
# =====================


def test_resources_raises_error():
    """Test that accessing context.resources raises RuntimeError."""
    context = ToolContext()
    with pytest.raises(
        RuntimeError,
        match="The resources feature is not supported for Arcade managed servers \\(non-local\\)",
    ):
        _ = context.resources


def test_tools_raises_error():
    """Test that accessing context.tools raises RuntimeError."""
    context = ToolContext()
    with pytest.raises(
        RuntimeError,
        match="The tools feature is not supported for Arcade managed servers \\(non-local\\)",
    ):
        _ = context.tools


def test_prompts_raises_error():
    """Test that accessing context.prompts raises RuntimeError."""
    context = ToolContext()
    with pytest.raises(
        RuntimeError,
        match="The prompts feature is not supported for Arcade managed servers \\(non-local\\)",
    ):
        _ = context.prompts


def test_sampling_raises_error():
    """Test that accessing context.sampling raises RuntimeError."""
    context = ToolContext()
    with pytest.raises(
        RuntimeError,
        match="The sampling feature is not supported for Arcade managed servers \\(non-local\\)",
    ):
        _ = context.sampling


def test_ui_raises_error():
    """Test that accessing context.ui raises RuntimeError."""
    context = ToolContext()
    with pytest.raises(
        RuntimeError,
        match="The ui feature is not supported for Arcade managed servers \\(non-local\\)",
    ):
        _ = context.ui


def test_notifications_raises_error():
    """Test that accessing context.notifications raises RuntimeError."""
    context = ToolContext()
    with pytest.raises(
        RuntimeError,
        match="The notifications feature is not supported for Arcade managed servers \\(non-local\\)",
    ):
        _ = context.notifications


def test_request_id_raises_error():
    """Test that accessing context.request_id raises RuntimeError."""
    context = ToolContext()
    with pytest.raises(
        RuntimeError,
        match="The request_id feature is not supported for Arcade managed servers \\(non-local\\)",
    ):
        _ = context.request_id


def test_session_id_raises_error():
    """Test that accessing context.session_id raises RuntimeError."""
    context = ToolContext()
    with pytest.raises(
        RuntimeError,
        match="The session_id feature is not supported for Arcade managed servers \\(non-local\\)",
    ):
        _ = context.session_id
