import asyncio
import base64
import json
from typing import Annotated

import pytest
import pytest_asyncio
from arcade_core.catalog import ToolCatalog
from arcade_mcp_server import Image, ToolResult, tool
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.types import ToolExecution
from typing_extensions import TypedDict

PNG = b"\x89PNG fake"
VALUE = {"name": "cat.png", "size": 5}
EXPECTED_IMAGE = {
    "type": "image",
    "data": base64.b64encode(PNG).decode("ascii"),
    "mimeType": "image/png",
}


class FileDetails(TypedDict):
    """A file's details."""

    name: str
    size: int


@tool(execution=ToolExecution(taskSupport="optional"))
def get_picture() -> Annotated[ToolResult[FileDetails], "The file"]:
    """Return a file's details and its picture."""
    return ToolResult(FileDetails(name="cat.png", size=5), content=[Image(PNG, "image/png")])


@pytest_asyncio.fixture
async def server(mcp_settings):
    catalog = ToolCatalog()
    catalog.add_tool(get_picture, "Files")
    server = MCPServer(catalog=catalog, name="Test", version="1.0.0", settings=mcp_settings)
    await server.start()
    yield server
    await server.stop()


@pytest_asyncio.fixture
async def session(server):
    session = ServerSession(server=server, read_stream=None, write_stream=None)
    session.mark_initialized()
    return session


def _assert_picture_result(result) -> None:
    dumped = result.model_dump(exclude_none=True, by_alias=True)
    assert dumped["content"] == [
        EXPECTED_IMAGE,
        {"type": "text", "text": json.dumps(VALUE, ensure_ascii=False)},
    ]
    assert dumped["structuredContent"] == VALUE
    assert dumped["isError"] is False


def test_image_dumps_without_null_keys():
    assert Image(PNG, "image/png").model_dump(by_alias=True, exclude_none=True) == EXPECTED_IMAGE


@pytest.mark.asyncio
async def test_call_tool_returns_image_text_and_structured_content(server, session):
    response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "Files.GetPicture", "arguments": {}},
        },
        session,
    )

    _assert_picture_result(response.result)


@pytest.mark.asyncio
async def test_task_call_returns_image_text_and_structured_content(server, session):
    session.negotiated_version = "2025-11-25"
    session._negotiated_capabilities = {"tasks": {"requests": {"tools": {"call": {}}}}}
    response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "Files.GetPicture", "arguments": {}, "task": {"ttl": 60000}},
        },
        session,
    )

    stored = await asyncio.wait_for(
        server._task_manager.get_result(
            response.result.task.taskId, context_key=f"session:{session.session_id}"
        ),
        timeout=5.0,
    )
    _assert_picture_result(stored)


@pytest.mark.asyncio
async def test_tool_result_output_schema_matches_inner_type(server, session):
    response = await server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, session
    )

    schema = response.result.tools[0].outputSchema
    assert schema["type"] == "object"
    assert set(schema["properties"]) == {"name", "size"}
