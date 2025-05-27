import asyncio

import pytest
from arcade_serve.mcp.message_processor import MCPMessageProcessor, create_message_processor
from arcade_serve.mcp.types import InitializeRequest, PingRequest


@pytest.mark.asyncio
async def test_message_processor_parses_initialize_json():
    """Ensure JSON initialize strings are converted into InitializeRequest objects."""
    json_init = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
    processor = MCPMessageProcessor()

    result = await processor.process_request(json_init)

    assert isinstance(result, InitializeRequest)
    assert result.id == 1
    assert result.method == "initialize"


@pytest.mark.asyncio
async def test_message_processor_passes_notifications_unchanged():
    """Unknown notifications should be passed through as parsed dictionaries without errors."""
    json_notification = '{"jsonrpc":"2.0","id":null,"method":"notifications/custom","params":{}}\n'
    processor = MCPMessageProcessor()

    result = await processor.process_request(json_notification)

    # The MCPMessageProcessor keeps unknown notifications as simple dicts
    assert isinstance(result, dict)
    assert result["method"] == "notifications/custom"


@pytest.mark.asyncio
async def test_message_processor_middleware_execution_order(monkeypatch):
    """Middleware (sync + async) should be executed in the order they were added."""

    order: list[str] = []

    def mw_sync(msg, direction):  # type: ignore[return-value]
        order.append("sync")
        return msg

    async def mw_async(msg, direction):  # type: ignore[return-value]
        await asyncio.sleep(0)  # ensure it is truly async
        order.append("async")
        return msg

    processor = create_message_processor(mw_sync, mw_async)

    # Use a pre-parsed PingRequest instance so we don't test parsing again here
    ping = PingRequest(id=42)

    _ = await processor.process_request(ping)

    assert order == ["sync", "async"]
