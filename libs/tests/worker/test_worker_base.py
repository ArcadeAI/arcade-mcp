from typing import Annotated
from unittest.mock import MagicMock

import pytest
from arcade_core.errors import ErrorKind, ToolDefinitionError, UpstreamError
from arcade_core.schema import (
    ToolCallError,
    ToolCallOutput,
    ToolCallRequest,
    ToolCallResponse,
    ToolContext,
    ToolReference,
)
from arcade_serve.core import base as base_module
from arcade_serve.core import components as components_module
from arcade_serve.core.base import BaseWorker
from arcade_serve.core.common import RequestData, Router
from arcade_serve.core.components import (
    CallToolComponent,
    CatalogComponent,
    HealthCheckComponent,
    ListResourcesComponent,
    ReadResourceComponent,
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


class FakeSpan:
    def __init__(self, name: str):
        self.name = name
        self.attributes: dict[str, object] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value


class FakeTracer:
    def __init__(self):
        self.spans: list[FakeSpan] = []

    def start_as_current_span(self, name: str) -> FakeSpan:
        span = FakeSpan(name)
        self.spans.append(span)
        return span


@pytest.fixture
def mock_router():
    router = MagicMock(spec=Router)
    router.add_route = MagicMock()
    return router


@pytest.fixture
def base_worker(mock_router, monkeypatch):
    # Set env var temporarily for testing secret loading
    monkeypatch.setenv("ARCADE_WORKER_SECRET", "test_secret_env")
    worker = BaseWorker()
    worker.register_routes(mock_router)  # Register routes using the mock router
    return worker


@pytest.fixture
def base_worker_no_auth():
    return BaseWorker(disable_auth=True)


@pytest.fixture
def fake_tracer():
    return FakeTracer()


# --- BaseWorker Tests ---


def test_base_worker_init_with_secret():
    worker = BaseWorker(secret="explicit_secret")  # noqa: S106
    assert worker.secret == "explicit_secret"  # noqa: S105
    assert not worker.disable_auth


def test_base_worker_init_with_env_secret(monkeypatch):
    monkeypatch.setenv("ARCADE_WORKER_SECRET", "env_secret_value")
    worker = BaseWorker()
    assert worker.secret == "env_secret_value"  # noqa: S105
    assert not worker.disable_auth


def test_base_worker_init_no_secret_raises_error(monkeypatch):
    # Ensure env var is not set
    monkeypatch.delenv("ARCADE_WORKER_SECRET", raising=False)
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


@pytest.mark.asyncio
async def test_call_tool_success_and_error_logs_use_same_tool_identifiers(
    base_worker_no_auth, caplog
):
    """Success and error log lines must use identical tool identifier strings
    so logs can be correlated with a single grep pattern."""
    import logging

    base_worker_no_auth.register_tool(sample_tool, toolkit_name="test_kit")
    base_worker_no_auth.register_tool(error_tool, toolkit_name="test_kit")

    success_req = ToolCallRequest(
        execution_id="exec_consistency_ok",
        tool=ToolReference(toolkit="TestKit", name="SampleTool"),
        inputs={"a": 1, "b": 2},
    )
    error_req = ToolCallRequest(
        execution_id="exec_consistency_err",
        tool=ToolReference(toolkit="TestKit", name="ErrorTool"),
        inputs={},
    )

    with caplog.at_level(logging.DEBUG, logger="arcade_serve.core.base"):
        await base_worker_no_auth.call_tool(success_req)
        await base_worker_no_auth.call_tool(error_req)

    success_line = next(
        r
        for r in caplog.records
        if "exec_consistency_ok" in r.getMessage() and "success" in r.getMessage()
    )
    error_line = next(
        r
        for r in caplog.records
        if "exec_consistency_err" in r.getMessage() and "failed:" in r.getMessage()
    )
    # Both must use the bare tool name (".name"), NOT the full ``Toolkit.Tool`` fqname.
    assert "Tool SampleTool " in success_line.getMessage()
    assert "Tool ErrorTool " in error_line.getMessage()
    # Neither line should contain the full-fqname form ``TestKit.SampleTool``.
    assert "TestKit.SampleTool" not in success_line.getMessage()
    assert "TestKit.ErrorTool" not in error_line.getMessage()
    # Both must use the same "version <X>" word — proves the same source
    # (``tool_fqname.toolkit_version``) is read on both paths.
    assert "version " in success_line.getMessage()
    assert "version " in error_line.getMessage()


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
async def test_call_tool_error_records_run_tool_span_attributes(
    base_worker_no_auth, fake_tracer, monkeypatch
):
    monkeypatch.setattr(base_module.trace, "get_tracer", lambda name: fake_tracer)
    base_worker_no_auth.register_tool(error_tool, toolkit_name="error_kit")
    tool_request = ToolCallRequest(
        execution_id="exec_span_attrs",
        tool=ToolReference(toolkit="ErrorKit", name="ErrorTool"),
        inputs={},
    )

    response = await base_worker_no_auth.call_tool(tool_request)

    assert response.success is False
    run_tool_span = next(span for span in fake_tracer.spans if span.name == "RunTool")
    assert run_tool_span.attributes["tool_error_kind"] == "TOOL_RUNTIME_FATAL"
    assert run_tool_span.attributes["tool_error_can_retry"] is False
    # Error text echoes end-user content and must never reach spans.
    assert "tool_error_message" not in run_tool_span.attributes
    assert "tool_error_developer_message" not in run_tool_span.attributes
    assert not any("Something went wrong" in str(v) for v in run_tool_span.attributes.values())


@pytest.mark.asyncio
async def test_call_tool_error_log_text_matches_structured_extras(base_worker_no_auth, caplog):
    """The primary failure warning's f-string must use the same resolved
    ``tool_fqname.name`` / ``tool_fqname.toolkit_version`` values that
    ``log_extra`` exposes — otherwise the human-readable text and the
    Datadog facets disagree on which tool/version produced the error.
    Previously the f-string used ``tool_request.tool.version`` (the *requested*
    version, often ``None``) while the extras used the resolved version."""
    base_worker_no_auth.register_tool(error_tool, toolkit_name="error_kit")
    tool_request = ToolCallRequest(
        execution_id="exec_log_check",
        tool=ToolReference(toolkit="ErrorKit", name="ErrorTool"),
        inputs={},
    )

    with caplog.at_level("WARNING", logger="arcade_serve.core.base"):
        await base_worker_no_auth.call_tool(tool_request)

    primary = next(
        r
        for r in caplog.records
        if "exec_log_check" in r.getMessage() and "failed:" in r.getMessage()
    )
    # Text and structured extra must agree on name + version.
    assert "Tool ErrorTool " in primary.getMessage()
    assert getattr(primary, "tool_name", None) == "ErrorTool"
    extra_version = getattr(primary, "toolkit_version", None)
    assert f"version {extra_version}" in primary.getMessage()


@pytest.mark.asyncio
async def test_call_tool_error_text_logged_at_debug_only(base_worker_no_auth, caplog):
    """The @tool fallback puts ``str(exception)`` into ``developer_message``.
    That text echoes end-user content, so it (and ``message``) must only be
    logged at DEBUG, never at WARNING or above."""
    import logging

    base_worker_no_auth.register_tool(error_tool, toolkit_name="error_kit")
    tool_request = ToolCallRequest(
        execution_id="exec_dev_msg",
        tool=ToolReference(toolkit="ErrorKit", name="ErrorTool"),
        inputs={},
    )

    with caplog.at_level(logging.DEBUG, logger="arcade_serve.core.base"):
        await base_worker_no_auth.call_tool(tool_request)

    above_debug = [r for r in caplog.records if r.levelno > logging.DEBUG]
    assert not any("Something went wrong" in r.getMessage() for r in above_debug)
    assert not any("Developer message:" in r.getMessage() for r in above_debug)

    debug_dev = [
        r
        for r in caplog.records
        if r.levelno == logging.DEBUG and "Developer message:" in r.getMessage()
    ]
    assert len(debug_dev) == 1
    assert "ValueError" in debug_dev[0].getMessage()
    assert "Something went wrong" in debug_dev[0].getMessage()


@tool
def leaky_error_tool(context: ToolContext, email: Annotated[str, "Contact email"]) -> int:
    """Fails with error text that echoes the user's input."""
    raise UpstreamError(
        f"No contact with email {email} in the CRM",
        developer_message=f"GET /contacts?email={email} returned 404",
        status_code=404,
    )


@pytest.mark.asyncio
async def test_call_tool_error_text_never_logged_or_traced_above_debug(
    base_worker_no_auth, caplog, fake_tracer, monkeypatch
):
    """User content in a tool error must not appear in WARNING logs, their
    structured extras, or span attributes; the WARNING line still carries
    which tool failed, the kind, status and retry advice."""
    import logging

    monkeypatch.setattr(base_module.trace, "get_tracer", lambda name: fake_tracer)
    email = "jane@example.com"
    base_worker_no_auth.register_tool(leaky_error_tool, toolkit_name="crm_kit")
    tool_request = ToolCallRequest(
        execution_id="exec_leak",
        tool=ToolReference(toolkit="CrmKit", name="LeakyErrorTool"),
        inputs={"email": email},
    )

    with caplog.at_level(logging.INFO, logger="arcade_serve.core.base"):
        response = await base_worker_no_auth.call_tool(tool_request)

    # The caller still gets the full error.
    assert email in response.output.error.message

    for record in caplog.records:
        assert email not in record.getMessage()
        assert email not in str(record.__dict__)
    for span in fake_tracer.spans:
        assert not any(email in str(v) for v in span.attributes.values())

    warning = next(
        r for r in caplog.records if "exec_leak" in r.getMessage() and "failed:" in r.getMessage()
    )
    assert warning.levelno == logging.WARNING
    assert "Tool LeakyErrorTool " in warning.getMessage()
    assert "kind=UPSTREAM_RUNTIME_NOT_FOUND" in warning.getMessage()
    assert "status=404" in warning.getMessage()
    assert "can_retry=False" in warning.getMessage()
    assert warning.error_kind == "UPSTREAM_RUNTIME_NOT_FOUND"
    assert warning.error_status_code == 404


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
    expected_paths = ["tools", "tools/invoke", "health", "resources/list", "resources/read"]
    registered_paths = [
        call[0][0] for call in calls
    ]  # call[0] are positional args, call[0][0] is endpoint_path

    assert sorted(registered_paths) == sorted(expected_paths)

    # Check if components were instantiated and passed to add_route
    assert any(isinstance(call[0][1], CatalogComponent) for call in calls)
    assert any(isinstance(call[0][1], CallToolComponent) for call in calls)
    assert any(isinstance(call[0][1], HealthCheckComponent) for call in calls)
    assert any(isinstance(call[0][1], ListResourcesComponent) for call in calls)
    assert any(isinstance(call[0][1], ReadResourceComponent) for call in calls)


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
async def test_call_tool_component_allows_missing_output():
    class OutputlessWorker:
        async def call_tool(self, call_tool_request):
            return ToolCallResponse(
                execution_id="comp_outputless_exec",
                duration=1,
                finished_at="2026-01-01T00:00:00",
                success=False,
                output=None,
            )

    component = CallToolComponent(OutputlessWorker())
    mock_request = MagicMock(spec=RequestData)
    mock_request.body_json = {
        "execution_id": "comp_outputless_exec",
        "tool": ToolReference(toolkit="TestKit", name="SampleTool").model_dump(),
        "inputs": {},
    }

    response = await component(mock_request)

    assert response.success is False
    assert response.output is None


@pytest.mark.asyncio
async def test_call_tool_component_error_records_call_tool_span_attributes(
    fake_tracer, monkeypatch
):
    monkeypatch.setattr(components_module.trace, "get_tracer", lambda name: fake_tracer)

    class ErrorWorker:
        environment = "test"

        async def call_tool(self, call_tool_request):
            return ToolCallResponse(
                execution_id="comp_error_exec",
                duration=1,
                finished_at="2026-01-01T00:00:00",
                success=False,
                output=ToolCallOutput(
                    error=ToolCallError(
                        kind=ErrorKind.TOOL_RUNTIME_FATAL,
                        message="public component failure",
                        developer_message="component developer details",
                    ),
                ),
            )

    component = CallToolComponent(ErrorWorker())
    mock_request = MagicMock(spec=RequestData)
    mock_request.body_json = {
        "execution_id": "comp_error_exec",
        "tool": ToolReference(toolkit="TestKit", name="SampleTool").model_dump(),
        "inputs": {},
    }

    response = await component(mock_request)

    assert response.success is False
    call_tool_span = next(span for span in fake_tracer.spans if span.name == "CallTool")
    assert call_tool_span.attributes["tool_error_kind"] == "TOOL_RUNTIME_FATAL"
    assert call_tool_span.attributes["tool_error_can_retry"] is False
    assert "tool_error_message" not in call_tool_span.attributes
    assert "tool_error_developer_message" not in call_tool_span.attributes


@pytest.mark.asyncio
async def test_health_check_component_call(base_worker_no_auth):
    component = HealthCheckComponent(base_worker_no_auth)
    mock_request = MagicMock(spec=RequestData)
    health_response = await component(mock_request)

    assert health_response == {"status": "ok", "tool_count": "0"}
