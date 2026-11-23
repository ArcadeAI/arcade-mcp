import asyncio
import base64
import json
import sys
import textwrap
from typing import Annotated

import pytest
import pytest_asyncio
from arcade_core.catalog import ToolCatalog
from arcade_mcp_server import Image, ToolResult, tool
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.types import ToolExecution
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
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


@tool(execution=ToolExecution(taskSupport="optional"))
def get_broken_picture() -> Annotated[ToolResult[FileDetails], "The file"]:
    """Return a content block that is not a valid MCP block."""
    return ToolResult(FileDetails(name="cat.png", size=5), content=[{"type": "image"}])


@pytest_asyncio.fixture
async def server(mcp_settings):
    catalog = ToolCatalog()
    catalog.add_tool(get_picture, "Files")
    catalog.add_tool(get_broken_picture, "Files")
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

    tool = next(t for t in response.result.tools if t.name == "Files_GetPicture")
    schema = tool.outputSchema
    assert schema["type"] == "object"
    assert set(schema["properties"]) == {"name", "size"}


@pytest.mark.asyncio
async def test_malformed_content_block_is_a_tool_output_error(server, session):
    session.negotiated_version = "2025-11-25"
    response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "Files.GetBrokenPicture", "arguments": {}},
        },
        session,
    )

    assert response.result.isError is True
    assert response.result.content[0].text == "Failed to serialize tool output"


@pytest.mark.asyncio
async def test_malformed_content_block_in_task_is_a_tool_output_error(server, session):
    session.negotiated_version = "2025-11-25"
    session._negotiated_capabilities = {"tasks": {"requests": {"tools": {"call": {}}}}}
    response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "Files.GetBrokenPicture", "arguments": {}, "task": {"ttl": 60000}},
        },
        session,
    )

    stored = await asyncio.wait_for(
        server._task_manager.get_result(
            response.result.task.taskId, context_key=f"session:{session.session_id}"
        ),
        timeout=5.0,
    )
    assert stored.isError is True
    assert stored.content[0].text == "Failed to serialize tool output"


SERVER_SCRIPT = """
from typing import Annotated
from typing_extensions import TypedDict
from arcade_mcp_server import Image, MCPApp, ToolResult

app = MCPApp(name="probe", version="1.0.0", log_level="ERROR")


class FileDetails(TypedDict):
    \"\"\"A file's details.\"\"\"

    name: str
    size: int


@app.tool
def get_picture() -> Annotated[ToolResult[FileDetails], "The file"]:
    \"\"\"Return a file's details and its picture.\"\"\"
    return ToolResult(FileDetails(name="cat.png", size=5), content=[Image(b"PNG", "image/png")])


if __name__ == "__main__":
    app.run(transport="stdio")
"""


@pytest.mark.asyncio
async def test_official_mcp_client_accepts_picture_result(tmp_path):
    script = tmp_path / "server.py"
    script.write_text(textwrap.dedent(SERVER_SCRIPT), encoding="utf-8")
    params = StdioServerParameters(command=sys.executable, args=[str(script)])

    async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
        await client.initialize()
        tools = await client.list_tools()
        result = await client.call_tool(tools.tools[0].name, {})

    assert result.isError is False
    assert [block.type for block in result.content] == ["image", "text"]
    assert result.structuredContent == VALUE
