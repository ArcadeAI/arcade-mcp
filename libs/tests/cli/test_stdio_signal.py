"""Tests for Windows signal handling in stdio transport.

Verifies that:
- The signal-handler support message is suppressed on Windows.
- No noisy "Failed to set up signal handler" warning is logged on Windows.
- A stdlib signal.signal(SIGINT) fallback is registered on Windows.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Callable, Coroutine
from typing import Any
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_signal_handler_support_message_is_suppressed_on_windows() -> None:
    """On Windows, don't log a user-facing signal-support message."""
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

        messages = [r.getMessage() for r in log_records]
        assert not any("Windows does not support asyncio signal handlers" in m for m in messages), (
            "Windows signal support message should be suppressed."
        )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)


@pytest.mark.asyncio
async def test_signal_handler_no_failed_setup_warning_on_windows() -> None:
    """On Windows, avoid warning noise when asyncio signal handlers are unavailable."""
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

        failed_setup_warnings = [
            r for r in log_records if "Failed to set up signal handler" in r.getMessage()
        ]
        assert len(failed_setup_warnings) == 0, (
            "Should not emit setup warnings for expected Windows asyncio limitations."
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


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only SIGINT fallback behavior")
@pytest.mark.asyncio
async def test_windows_sigint_fallback_schedules_stop_on_transport_loop() -> None:
    """Windows SIGINT fallback should schedule stop() on the captured event loop."""
    import signal

    import arcade_mcp_server.transports.stdio as stdio_mod
    from arcade_mcp_server.transports.stdio import StdioTransport

    transport = StdioTransport(name="test-stdio-loop-schedule")
    registered_handlers: dict[int, Callable[[int, object], None]] = {}
    scheduled_callbacks: list[Callable[[], None]] = []
    created_coroutines: list[Coroutine[Any, Any, None]] = []

    def capture_signal(signum: int, handler: Callable[[int, object], None]) -> None:
        registered_handlers[signum] = handler

    def capture_call_soon_threadsafe(callback: Callable[[], None], *args: object) -> None:
        assert not args
        scheduled_callbacks.append(callback)

    def capture_create_task(coro: Coroutine[Any, Any, None]) -> object:
        created_coroutines.append(coro)
        coro.close()
        return object()

    loop = asyncio.get_running_loop()
    original_add = loop.add_signal_handler

    def raise_not_impl(*args: object, **kwargs: object) -> None:
        raise NotImplementedError

    loop.add_signal_handler = raise_not_impl  # type: ignore[method-assign]
    with (
        patch.object(loop, "call_soon_threadsafe", side_effect=capture_call_soon_threadsafe),
        patch.object(loop, "create_task", side_effect=capture_create_task),
        patch.object(stdio_mod.signal, "signal", side_effect=capture_signal),
    ):
        try:
            await transport.start()

            handler = registered_handlers[signal.SIGINT]
            handler(signal.SIGINT, object())

            assert len(scheduled_callbacks) == 1
            scheduled_callback = scheduled_callbacks[0]

            scheduled_callback()
            assert len(created_coroutines) == 1
        finally:
            loop.add_signal_handler = original_add  # type: ignore[method-assign]
            await transport.stop()
