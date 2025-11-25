import os
from typing import Annotated
from unittest.mock import MagicMock

import pytest
from arcade_core.errors import ToolDefinitionError
from arcade_core.schema import (
    ToolCallRequest,
    ToolCallResponse,
    ToolContext,
    ToolReference,
)
from arcade_serve.core.base import BaseWorker
from arcade_serve.core.common import RequestData, Router
from arcade_serve.core.components import (
    CallToolComponent,
    CatalogComponent,
    HealthCheckComponent,
)
from arcade_tdk import tool


@tool()
def sample_tool(
    context: ToolContext, a: Annotated[int, "a"], b: Annotated[int, "b"]
) -> Annotated[int, "output"]:
    """Sample tool for testing."""
    return a + b


# Define error tool at module level to avoid indentation issues with getsource
@tool()
def error_tool(context: ToolContext) -> int:
    """This tool always raises an error."""
    raise ValueError("Something went wrong")


@pytest.fixture
def mock_router():
    router = MagicMock(spec=Router)
    router.add_route = MagicMock()
    return router


@pytest.fixture
def base_worker(mock_router):
    # Set env var temporarily for testing secret loading
    os.environ["ARCADE_WORKER_SECRET"] = "test_secret_env"  # noqa: S105
    worker = BaseWorker()
    worker.register_routes(mock_router)  # Register routes using the mock router
    # Clean up env var
    del os.environ["ARCADE_WORKER_SECRET"]
    return worker


@pytest.fixture
def base_worker_no_auth():
    return BaseWorker(disable_auth=True)


# --- BaseWorker Tests ---


def test_base_worker_init_with_secret():
    worker = BaseWorker(secret="explicit_secret")  # noqa: S106
    assert worker.secret == "explicit_secret"  # noqa: S105
    assert not worker.disable_auth


def test_base_worker_init_with_env_secret():
    os.environ["ARCADE_WORKER_SECRET"] = "env_secret_value"  # noqa: S105
    worker = BaseWorker()
    assert worker.secret == "env_secret_value"  # noqa: S105
    assert not worker.disable_auth
    del os.environ["ARCADE_WORKER_SECRET"]


def test_base_worker_init_no_secret_raises_error():
    # Ensure env var is not set
    if "ARCADE_WORKER_SECRET" in os.environ:
        del os.environ["ARCADE_WORKER_SECRET"]
    with pytest.raises(ValueError, match="No secret provided for worker"):
        BaseWorker()


def test_base_worker_init_disable_auth():
    worker = BaseWorker(disable_auth=True)
    assert worker.secret == ""
    assert worker.disable_auth


def test_register_tool(base_worker_no_auth):
    assert len(base_worker_no_auth.catalog) == 0
    base_worker_no_auth.register_tool(sample_tool, toolkit_name="test_kit")
    assert len(base_worker_no_auth.catalog) == 1
    tool_def = base_worker_no_auth.get_catalog()[0]
    assert tool_def.name == "SampleTool"
    assert tool_def.toolkit.name == "TestKit"


def test_get_catalog(base_worker_no_auth):
    base_worker_no_auth.register_tool(sample_tool, toolkit_name="test_kit")
    catalog = base_worker_no_auth.get_catalog()
    assert isinstance(catalog, list)
    assert len(catalog) == 1
    assert catalog[0].name == "SampleTool"


def test_health_check(base_worker_no_auth):
    base_worker_no_auth.register_tool(sample_tool, toolkit_name="test_kit")
    health = base_worker_no_auth.health_check()
    assert health == {"status": "ok", "tool_count": "1"}


@pytest.mark.asyncio
async def test_call_tool_success(base_worker_no_auth):
    base_worker_no_auth.register_tool(sample_tool, toolkit_name="test_kit")
    # Create ToolReference WITHOUT version, as register_tool doesn't seem to set it
    tool_ref = ToolReference(toolkit="TestKit", name="SampleTool")
    tool_request = ToolCallRequest(
        execution_id="test_exec_id",
        tool=tool_ref,
        inputs={"a": 5, "b": 3},
    )

    response = await base_worker_no_auth.call_tool(tool_request)

    assert response.success is True
    assert response.output.value == 8
    assert response.output.error is None
    assert response.execution_id == "test_exec_id"
    assert response.duration > 0


@pytest.mark.asyncio
async def test_call_tool_execution_error(base_worker_no_auth):
    # Tool is now defined at module level
    try:
        base_worker_no_auth.register_tool(error_tool, toolkit_name="error_kit")
    except ToolDefinitionError as e:
        pytest.fail(f"Failed to register error_tool: {e}")

    # Create ToolReference WITHOUT version
    tool_ref = ToolReference(toolkit="ErrorKit", name="ErrorTool")
    tool_request = ToolCallRequest(
        execution_id="test_exec_error",
        tool=tool_ref,
        inputs={},
    )

    response = await base_worker_no_auth.call_tool(tool_request)

    assert response.success is False
    assert response.output.value is None
    assert response.output.error is not None


@pytest.mark.asyncio
async def test_call_tool_not_found(base_worker_no_auth):
    # Use ToolReference without version for lookup consistency
    tool_ref = ToolReference(toolkit="nonexistent", name="nosuchtool")
    tool_request = ToolCallRequest(
        execution_id="test_exec_notfound",
        tool=tool_ref,
        inputs={},
    )

    # Update regex to match actual error format
    with pytest.raises(ValueError):
        await base_worker_no_auth.call_tool(tool_request)


# --- Component Tests (tested via BaseWorker registration) ---


def test_register_routes_registers_default_components(base_worker, mock_router):
    # BaseWorker calls register_routes in its init via the fixture
    assert mock_router.add_route.call_count == len(BaseWorker.default_components)

    calls = mock_router.add_route.call_args_list
    expected_paths = ["tools", "tools/invoke", "health"]
    registered_paths = [
        call[0][0] for call in calls
    ]  # call[0] are positional args, call[0][0] is endpoint_path

    assert sorted(registered_paths) == sorted(expected_paths)

    # Check if components were instantiated and passed to add_route
    assert any(isinstance(call[0][1], CatalogComponent) for call in calls)
    assert any(isinstance(call[0][1], CallToolComponent) for call in calls)
    assert any(isinstance(call[0][1], HealthCheckComponent) for call in calls)


@pytest.mark.asyncio
async def test_catalog_component_call(base_worker_no_auth):
    base_worker_no_auth.register_tool(sample_tool, toolkit_name="test_kit")
    component = CatalogComponent(base_worker_no_auth)
    # Mock request data - not actually used by this component's __call__
    mock_request = MagicMock(spec=RequestData)
    catalog_response = await component(mock_request)

    assert isinstance(catalog_response, list)
    assert len(catalog_response) == 1
    assert catalog_response[0].name == "SampleTool"


@pytest.mark.asyncio
async def test_call_tool_component_call(base_worker_no_auth):
    base_worker_no_auth.register_tool(sample_tool, toolkit_name="test_kit")
    component = CallToolComponent(base_worker_no_auth)

    # Create ToolReference WITHOUT version
    tool_ref = ToolReference(toolkit="TestKit", name="SampleTool")
    request_body = {
        "execution_id": "comp_test_exec",
        "tool": tool_ref.model_dump(),
        "inputs": {"a": 10, "b": 5},
    }
    mock_request = MagicMock(spec=RequestData)
    mock_request.body_json = request_body

    response = await component(mock_request)

    assert isinstance(response, ToolCallResponse)
    assert response.success is True
    assert response.output.value == 15
    assert response.execution_id == "comp_test_exec"


@pytest.mark.asyncio
async def test_health_check_component_call(base_worker_no_auth):
    component = HealthCheckComponent(base_worker_no_auth)
    mock_request = MagicMock(spec=RequestData)
    health_response = await component(mock_request)

    assert health_response == {"status": "ok", "tool_count": "0"}
