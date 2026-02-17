from __future__ import annotations

import asyncio
from datetime import datetime
from io import StringIO
from unittest.mock import MagicMock, patch

from rich.console import Console

from arcade_cli.server import _display_deployment_logs, _stream_deployment_logs


def test_display_deployment_logs_preserves_square_bracket_content() -> None:
    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False)

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [
        {"timestamp": "2026-01-15T15:30:00Z", "line": "[INFO] startup [ERROR] details"}
    ]
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response

    import arcade_cli.server as server_mod

    original_console = server_mod.console
    server_mod.console = test_console
    try:
        with (
            patch("arcade_cli.server.httpx.Client") as mock_httpx_client,
            patch("arcade_cli.server._format_timestamp_to_local", return_value="2026-01-15 10:30:00 EST"),
        ):
            mock_httpx_client.return_value.__enter__.return_value = mock_client
            _display_deployment_logs(
                "http://localhost:8123/logs",
                {},
                datetime(2026, 1, 15, 15, 30, 0),
                datetime(2026, 1, 15, 15, 35, 0),
                debug=False,
            )
    finally:
        server_mod.console = original_console

    output = buf.getvalue()
    assert "[2026-01-15 10:30:00 EST]" in output
    assert "[INFO]" in output
    assert "[ERROR]" in output


def test_stream_deployment_logs_preserves_square_bracket_content() -> None:
    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False)

    class FakeStreamResponse:
        async def __aenter__(self) -> FakeStreamResponse:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def raise_for_status(self) -> None:
            return None

        async def aiter_lines(self):  # type: ignore[no-untyped-def]
            yield 'data: {"Timestamp":"2026-01-15T15:30:00Z","Line":"[ERROR] stream details"}'
            yield "[INFO] plain stream line"

    class FakeAsyncClient:
        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        def stream(self, *args, **kwargs) -> FakeStreamResponse:  # type: ignore[no-untyped-def]
            return FakeStreamResponse()

    import arcade_cli.server as server_mod

    original_console = server_mod.console
    server_mod.console = test_console
    try:
        with (
            patch("arcade_cli.server.httpx.AsyncClient", return_value=FakeAsyncClient()),
            patch("arcade_cli.server._format_timestamp_to_local", return_value="2026-01-15 10:30:00 EST"),
        ):
            asyncio.run(
                _stream_deployment_logs(
                    "http://localhost:8123/logs/stream",
                    {},
                    datetime(2026, 1, 15, 15, 30, 0),
                    datetime(2026, 1, 15, 15, 35, 0),
                    debug=False,
                )
            )
    finally:
        server_mod.console = original_console

    output = buf.getvalue()
    assert "[2026-01-15 10:30:00 EST]" in output
    assert "[ERROR]" in output
    assert "[INFO] plain stream line" in output
