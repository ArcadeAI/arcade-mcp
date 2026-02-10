"""Tests for Windows signal handling in stdio transport.

Verifies that:
- The signal handler on Windows logs at INFO level (not WARNING).
- The message contains actionable guidance (Ctrl+C / close terminal).
- The message is logged only ONCE (not once per signal).
- A stdlib signal.signal(SIGINT) fallback is registered on Windows.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_signal_handler_logs_info_on_windows() -> None:
    """On Windows, the signal handler warning should be logged at INFO level."""
    from arcade_mcp_server.transports.stdio import StdioTransport

    transport = StdioTransport(name="test-stdio")

    log_records: list[logging.LogRecord] = []

    class RecordHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            log_records.append(record)

    logger = logging.getLogger("arcade.mcp.transports.stdio")
    handler = RecordHandler()
    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(logging.DEBUG)

    try:
        with patch.object(sys, "platform", "win32"):
            # Simulate the NotImplementedError that Windows raises for
            # loop.add_signal_handler.
            loop = asyncio.get_running_loop()
            original_add = loop.add_signal_handler

            def raise_not_impl(*args, **kwargs):
                raise NotImplementedError

            loop.add_signal_handler = raise_not_impl  # type: ignore[assignment]

            # Also mock signal.signal so we don't actually install a handler
            with patch("arcade_mcp_server.transports.stdio.signal.signal"):
                try:
                    await transport.start()
                finally:
                    loop.add_signal_handler = original_add  # type: ignore[assignment]
                    await transport.stop()

        # Find the Windows-specific log message
        win_records = [
            r for r in log_records
            if "Windows" in r.getMessage() and "signal" in r.getMessage().lower()
        ]
        assert len(win_records) >= 1, (
            f"Expected a Windows signal info message. Got: {[r.getMessage() for r in log_records]}"
        )
        for rec in win_records:
            assert rec.levelno == logging.INFO, (
                f"Expected INFO level but got {rec.levelname}: {rec.getMessage()}"
            )
            # Should contain actionable guidance
            msg = rec.getMessage()
            assert "Ctrl+C" in msg or "close the terminal" in msg.lower(), (
                f"Message should contain actionable guidance: {msg}"
            )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)


@pytest.mark.asyncio
async def test_signal_handler_logs_once_on_windows() -> None:
    """The Windows info message should appear only once, not once per signal."""
    from arcade_mcp_server.transports.stdio import StdioTransport

    transport = StdioTransport(name="test-stdio-once")

    log_records: list[logging.LogRecord] = []

    class RecordHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            log_records.append(record)

    logger = logging.getLogger("arcade.mcp.transports.stdio")
    handler = RecordHandler()
    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(logging.DEBUG)

    try:
        with patch.object(sys, "platform", "win32"):
            loop = asyncio.get_running_loop()
            original_add = loop.add_signal_handler

            def raise_not_impl(*args, **kwargs):
                raise NotImplementedError

            loop.add_signal_handler = raise_not_impl  # type: ignore[assignment]

            with patch("arcade_mcp_server.transports.stdio.signal.signal"):
                try:
                    await transport.start()
                finally:
                    loop.add_signal_handler = original_add  # type: ignore[assignment]
                    await transport.stop()

        # The message "Windows does not support asyncio signal handlers" should
        # appear exactly ONCE, even though we try to register for both SIGINT
        # and SIGTERM.
        win_records = [
            r for r in log_records
            if "Windows" in r.getMessage()
            and "signal" in r.getMessage().lower()
            and r.levelno == logging.INFO
        ]
        assert len(win_records) == 1, (
            f"Expected exactly 1 Windows signal message but got {len(win_records)}: "
            f"{[r.getMessage() for r in win_records]}"
        )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)


@pytest.mark.asyncio
async def test_signal_signal_fallback_registered_on_windows() -> None:
    """On Windows, signal.signal(SIGINT, ...) should be called as a fallback."""
    from arcade_mcp_server.transports.stdio import StdioTransport

    transport = StdioTransport(name="test-stdio-fallback")

    log_records: list[logging.LogRecord] = []

    class RecordHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            log_records.append(record)

    logger = logging.getLogger("arcade.mcp.transports.stdio")
    handler = RecordHandler()
    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(logging.DEBUG)

    try:
        with patch.object(sys, "platform", "win32"):
            loop = asyncio.get_running_loop()
            original_add = loop.add_signal_handler

            def raise_not_impl(*args, **kwargs):
                raise NotImplementedError

            loop.add_signal_handler = raise_not_impl  # type: ignore[assignment]

            with patch("arcade_mcp_server.transports.stdio.signal.signal") as mock_signal:
                try:
                    await transport.start()
                finally:
                    loop.add_signal_handler = original_add  # type: ignore[assignment]
                    await transport.stop()

            # signal.signal should have been called with SIGINT
            import signal
            sigint_calls = [
                c for c in mock_signal.call_args_list
                if c[0][0] == signal.SIGINT
            ]
            assert len(sigint_calls) == 1, (
                f"Expected signal.signal(SIGINT, ...) to be called once. "
                f"All calls: {mock_signal.call_args_list}"
            )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)
