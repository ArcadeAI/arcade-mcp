"""Shared fixtures and utilities for arcade-mcp-server tests."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Annotated, Any
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from arcade_core.catalog import MaterializedTool, ToolCatalog, ToolMeta, create_func_models
from arcade_core.schema import (
    InputParameter,
    OAuth2Requirement,
    ToolAuthRequirement,
    ToolDefinition,
    ToolExecution,
    ToolInput,
    ToolkitDefinition,
    ToolOutput,
    ToolRequirements,
    ValueSchema,
)
from arcade_mcp_server import tool
from arcade_mcp_server.context import Context
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.settings import MCPSettings
from arcade_tdk.auth import OAuth2


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_tool_def() -> ToolDefinition:
    """Create a sample tool definition."""
    return ToolDefinition(
        name="test_tool",
        fully_qualified_name="TestToolkit.test_tool",
        description="A test tool",
        toolkit=ToolkitDefinition(name="TestToolkit", description="Test toolkit", version="1.0.0"),
        input=ToolInput(
            parameters=[
                InputParameter(
                    name="text",
                    required=True,
                    description="Input text",
                    value_schema=ValueSchema(val_type="string"),
                )
            ]
        ),
        output=ToolOutput(description="Tool output", value_schema=ValueSchema(val_type="string")),
        requirements=ToolRequirements(),
        execution=ToolExecution(taskSupport="optional"),
    )


@pytest.fixture
def sample_tool_def_with_auth() -> ToolDefinition:
    """Create a sample tool definition."""
    return ToolDefinition(
        name="sample_tool_with_auth",
        fully_qualified_name="TestToolkit.sample_tool_with_auth",
        description="A test tool",
        toolkit=ToolkitDefinition(name="TestToolkit", description="Test toolkit", version="1.0.0"),
        input=ToolInput(
            parameters=[
                InputParameter(
                    name="text",
                    required=True,
                    description="Input text",
                    value_schema=ValueSchema(val_type="string"),
                )
            ]
        ),
        output=ToolOutput(description="Tool output", value_schema=ValueSchema(val_type="string")),
        requirements=ToolRequirements(
            authorization=ToolAuthRequirement(
                provider_type="oauth2",
                provider_id="test-provider",
                id="test-provider",
                oauth2=OAuth2Requirement(
                    scopes=["test.scope", "another.scope"],
                ),
            ),
        ),
    )


@pytest.fixture
def sample_tool_func():
    """Create a sample tool function."""

    @tool
    def sample_tool(
        text: Annotated[str, "Input text to echo"],
    ) -> Annotated[str, "Echoed text result"]:
        """Echo input text back to the caller."""
        return f"Echo: {text}"

    return sample_tool


@pytest.fixture
def sample_tool_func_with_auth():
    """Create a sample tool function."""

    @tool(
        requires_auth=OAuth2(
            id="test-provider",
            scopes=["test.scope", "another.scope"],
        ),
    )
    def sample_tool_with_auth(
        text: Annotated[str, "Input text to echo"],
    ) -> Annotated[str, "Echoed text result"]:
        """Echo input text back to the caller."""
        return f"Echo: {text}"

    return sample_tool_with_auth


@pytest.fixture
def materialized_tool(sample_tool_func, sample_tool_def) -> MaterializedTool:
    """Create a materialized tool with required models and metadata."""
    input_model, output_model = create_func_models(sample_tool_func)
    meta = ToolMeta(module=sample_tool_func.__module__, toolkit=sample_tool_def.toolkit.name)
    return MaterializedTool(
        tool=sample_tool_func,
        definition=sample_tool_def,
        meta=meta,
        input_model=input_model,
        output_model=output_model,
    )


@pytest.fixture
def materialized_tool_with_auth(
    sample_tool_func_with_auth, sample_tool_def_with_auth
) -> MaterializedTool:
    """Create a materialized tool with required models and metadata."""
    input_model, output_model = create_func_models(sample_tool_func_with_auth)
    meta = ToolMeta(
        module=sample_tool_func_with_auth.__module__, toolkit=sample_tool_def_with_auth.toolkit.name
    )
    return MaterializedTool(
        tool=sample_tool_func_with_auth,
        definition=sample_tool_def_with_auth,
        meta=meta,
        input_model=input_model,
        output_model=output_model,
    )


def _make_tool_def(
    name: str,
    fqn: str,
    *,
    params: list[InputParameter] | None = None,
    execution: ToolExecution | None = None,
) -> ToolDefinition:
    """Helper to create a ToolDefinition with optional execution config."""
    return ToolDefinition(
        name=name,
        fully_qualified_name=fqn,
        description=f"A test tool: {name}",
        toolkit=ToolkitDefinition(name="TestToolkit", description="Test toolkit", version="1.0.0"),
        input=ToolInput(parameters=params or []),
        output=ToolOutput(description="Tool output", value_schema=ValueSchema(val_type="string")),
        requirements=ToolRequirements(),
        execution=execution,
    )


def _materialize(func: Any, defn: ToolDefinition) -> MaterializedTool:
    """Helper to materialize a tool from function + definition."""
    input_model, output_model = create_func_models(func)
    meta = ToolMeta(module=func.__module__, toolkit=defn.toolkit.name)
    return MaterializedTool(
        tool=func,
        definition=defn,
        meta=meta,
        input_model=input_model,
        output_model=output_model,
    )


@pytest.fixture
def failing_tool_func():
    """A tool that always raises an exception."""

    @tool
    def failing_tool() -> Annotated[str, "Never returned"]:
        """A tool that always fails."""
        raise RuntimeError("Tool execution failed")

    return failing_tool


@pytest.fixture
def failing_tool_def() -> ToolDefinition:
    return _make_tool_def(
        "failing_tool",
        "TestToolkit.failing_tool",
        execution=ToolExecution(taskSupport="optional"),
    )


@pytest.fixture
def materialized_failing_tool(failing_tool_func, failing_tool_def) -> MaterializedTool:
    return _materialize(failing_tool_func, failing_tool_def)


@pytest.fixture
def slow_tool_func():
    """A tool that sleeps for a long time (for cancellation tests)."""

    @tool
    async def slow_tool() -> Annotated[str, "Result"]:
        """A tool that sleeps."""
        await asyncio.sleep(60)
        return "done"

    return slow_tool


@pytest.fixture
def slow_tool_def() -> ToolDefinition:
    return _make_tool_def(
        "slow_tool",
        "TestToolkit.slow_tool",
        execution=ToolExecution(taskSupport="optional"),
    )


@pytest.fixture
def materialized_slow_tool(slow_tool_func, slow_tool_def) -> MaterializedTool:
    return _materialize(slow_tool_func, slow_tool_def)


@pytest.fixture
def error_result_tool_func():
    """A tool that returns isError=True (not an exception)."""

    @tool
    def error_result_tool() -> Annotated[str, "Error result"]:
        """A tool that indicates error via return value."""
        return None  # type: ignore[return-value]

    return error_result_tool


@pytest.fixture
def error_result_tool_def() -> ToolDefinition:
    return _make_tool_def(
        "error_result_tool",
        "TestToolkit.error_result_tool",
        execution=ToolExecution(taskSupport="optional"),
    )


@pytest.fixture
def materialized_error_result_tool(error_result_tool_func, error_result_tool_def) -> MaterializedTool:
    return _materialize(error_result_tool_func, error_result_tool_def)


@pytest.fixture
def forbidden_task_tool_func():
    """A tool with taskSupport=forbidden."""

    @tool
    def forbidden_task_tool() -> Annotated[str, "Result"]:
        """A tool that forbids task augmentation."""
        return "ok"

    return forbidden_task_tool


@pytest.fixture
def forbidden_task_tool_def() -> ToolDefinition:
    return _make_tool_def(
        "forbidden_task_tool",
        "TestToolkit.forbidden_task_tool",
        execution=ToolExecution(taskSupport="forbidden"),
    )


@pytest.fixture
def materialized_forbidden_task_tool(
    forbidden_task_tool_func, forbidden_task_tool_def
) -> MaterializedTool:
    return _materialize(forbidden_task_tool_func, forbidden_task_tool_def)


@pytest.fixture
def required_task_tool_func():
    """A tool with taskSupport=required."""

    @tool
    def required_task_tool() -> Annotated[str, "Result"]:
        """A tool that requires task augmentation."""
        return "ok"

    return required_task_tool


@pytest.fixture
def required_task_tool_def() -> ToolDefinition:
    return _make_tool_def(
        "required_task_tool",
        "TestToolkit.required_task_tool",
        execution=ToolExecution(taskSupport="required"),
    )


@pytest.fixture
def materialized_required_task_tool(
    required_task_tool_func, required_task_tool_def
) -> MaterializedTool:
    return _materialize(required_task_tool_func, required_task_tool_def)


@pytest.fixture
def no_execution_tool_func():
    """A tool with no execution field (default = forbidden)."""

    @tool
    def no_execution_tool() -> Annotated[str, "Result"]:
        """A tool with no execution config."""
        return "ok"

    return no_execution_tool


@pytest.fixture
def no_execution_tool_def() -> ToolDefinition:
    return _make_tool_def(
        "no_execution_tool",
        "TestToolkit.no_execution_tool",
        # No execution field -- defaults to None which means forbidden
    )


@pytest.fixture
def materialized_no_execution_tool(
    no_execution_tool_func, no_execution_tool_def
) -> MaterializedTool:
    return _materialize(no_execution_tool_func, no_execution_tool_def)


@pytest.fixture
def tool_catalog(
    materialized_tool: MaterializedTool,
    materialized_tool_with_auth: MaterializedTool,
    materialized_failing_tool: MaterializedTool,
    materialized_slow_tool: MaterializedTool,
    materialized_error_result_tool: MaterializedTool,
    materialized_forbidden_task_tool: MaterializedTool,
    materialized_required_task_tool: MaterializedTool,
    materialized_no_execution_tool: MaterializedTool,
) -> ToolCatalog:
    """Create a tool catalog with sample tools."""
    catalog = ToolCatalog()
    for mt in [
        materialized_tool,
        materialized_tool_with_auth,
        materialized_failing_tool,
        materialized_slow_tool,
        materialized_error_result_tool,
        materialized_forbidden_task_tool,
        materialized_required_task_tool,
        materialized_no_execution_tool,
    ]:
        catalog._tools[mt.definition.get_fully_qualified_name()] = mt
    return catalog


@pytest.fixture
def mcp_settings() -> MCPSettings:
    """Create test MCP settings."""
    settings = MCPSettings()
    settings.debug = True
    settings.middleware.enable_logging = True
    settings.middleware.mask_error_details = False
    return settings


@pytest_asyncio.fixture
async def mcp_server(tool_catalog, mcp_settings) -> AsyncGenerator[MCPServer, None]:
    """Create and start an MCP server."""
    server = MCPServer(
        catalog=tool_catalog,
        name="Test Server",
        version="1.0.0",
        settings=mcp_settings,
    )
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
def mock_read_stream() -> AsyncMock:
    """Create a mock read stream."""
    stream = AsyncMock()
    stream.read = AsyncMock()
    return stream


@pytest.fixture
def mock_write_stream() -> AsyncMock:
    """Create a mock write stream."""
    stream = AsyncMock()
    stream.write = AsyncMock()
    stream.send = AsyncMock()
    return stream


@pytest_asyncio.fixture
async def server_session(mcp_server, mock_read_stream, mock_write_stream) -> ServerSession:
    """Create a server session."""
    session = ServerSession(
        server=mcp_server,
        read_stream=mock_read_stream,
        write_stream=mock_write_stream,
    )
    return session


@pytest_asyncio.fixture
async def initialized_server_session(server_session) -> ServerSession:
    """Create an initialized server session."""
    server_session.mark_initialized()
    return server_session


@pytest.fixture
def sample_messages() -> dict[str, Any]:
    """Sample MCP protocol messages for testing."""
    return {
        "initialize": {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "sampling": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        },
        "initialized": {"jsonrpc": "2.0", "method": "notifications/initialized"},
        "list_tools": {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        "call_tool": {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "TestToolkit.test_tool", "arguments": {"text": "Hello, world!"}},
        },
        "ping": {"jsonrpc": "2.0", "id": 4, "method": "ping"},
    }


@pytest.fixture
def mock_context() -> Context:
    """Create a mock context."""
    context = Mock(spec=Context)
    context.server = Mock()
    context.request_id = "test-request-123"
    context.session_id = "test-session-456"
    context.state = {}

    # Mock async methods
    context.log = AsyncMock()
    context.debug = AsyncMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    context.report_progress = AsyncMock()
    context.read_resource = AsyncMock(return_value=[])
    context.list_roots = AsyncMock(return_value=[])
    context.sample = AsyncMock()
    context.elicit = AsyncMock()
    context.send_tool_list_changed = AsyncMock()
    context.send_resource_list_changed = AsyncMock()
    context.send_prompt_list_changed = AsyncMock()

    return context


# Async test helpers
async def wait_for(condition, timeout=1.0):
    """Wait for a condition to become true."""
    start = asyncio.get_event_loop().time()
    while not condition():
        if asyncio.get_event_loop().time() - start > timeout:
            raise TimeoutError("Condition not met within timeout")
        await asyncio.sleep(0.01)


async def collect_messages(stream, count):
    """Collect a specific number of messages from a stream."""
    messages = []
    for _ in range(count):
        msg = await stream.read()
        messages.append(msg)
    return messages
