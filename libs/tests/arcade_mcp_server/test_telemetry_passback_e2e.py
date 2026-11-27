"""End-to-end tests for what TelemetryPassbackMiddleware returns to the client.

These drive a real ``tools/call`` through ``MCPServer.handle_message`` with a
real ``TelemetryPassbackMiddleware`` and a real OpenTelemetry SDK
``TracerProvider``. The tool records spans the way instrumented libraries do
(a database statement, a URL with an API key in the query string) and then
fails with an ``UpstreamError`` whose ``developer_message`` carries a secret.

The passback payload goes to whoever called the tool, so it must never carry
data the framework otherwise keeps from callers.
"""

# ruff: noqa: S105, S608
import json
from typing import Annotated, Any

import pytest
import pytest_asyncio
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import UpstreamError
from arcade_mcp_server import tool
from arcade_mcp_server.middleware.telemetry import TelemetryPassbackMiddleware
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.settings import MCPSettings
from arcade_mcp_server.types import JSONRPCResponse
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Link, Status, StatusCode

DEV_MESSAGE_SECRET = "sk_live_51Hx_SECRET_FROM_DIAGNOSTICS"
URL_SECRET = "INTERNAL-BILLING-KEY-123"
DB_SECRET = "alice@example.com"
EVENT_SECRET = "exception-detail-with-token-abc123"
STATUS_SECRET = "status-description-with-token-def456"
LINK_SECRET = "link-attribute-with-token-ghi789"
RESOURCE_SECRET = "resource-attribute-with-token-jkl012"
REQUEST_SPAN_SECRET = "written-onto-request-span-mno345"
SECRETS = (
    DEV_MESSAGE_SECRET,
    URL_SECRET,
    DB_SECRET,
    EVENT_SECRET,
    STATUS_SECRET,
    LINK_SECRET,
    RESOURCE_SECRET,
    REQUEST_SPAN_SECRET,
)

# The tool records its spans with the same provider the middleware collects from.
_tracer_provider_holder: dict[str, TracerProvider] = {}


def _tracer() -> Any:
    return _tracer_provider_holder["provider"].get_tracer("billing-toolkit")


@tool
def charge_customer(customer_id: Annotated[str, "customer id"]) -> str:
    """Charge a customer via an internal billing service."""
    tracer = _tracer()
    # Code running inside the request span can write to it, including under
    # keys the middleware itself uses.
    request_span = trace.get_current_span()
    request_span.set_attribute("gen_ai.tool.call.arguments", REQUEST_SPAN_SECRET)
    request_span.set_attribute("internal.note", REQUEST_SPAN_SECRET)
    linked = request_span.get_span_context()
    with tracer.start_as_current_span(
        "db.query", links=[Link(linked, {"link.note": LINK_SECRET})]
    ) as span:
        span.set_attribute(
            "db.statement",
            f"SELECT email FROM customers WHERE id='{customer_id}' -- returned {DB_SECRET}",
        )
        span.set_attribute("db.system", "postgresql")
        with tracer.start_as_current_span("db.connect") as inner:
            inner.set_attribute("db.connection_string", f"postgres://admin:{URL_SECRET}@db")
    with tracer.start_as_current_span("http.client POST") as span:
        span.set_attribute(
            "url.full", f"https://billing.internal.example:8443/v1/charge?api_key={URL_SECRET}"
        )
        span.set_attribute("http.response.status_code", 401)
        span.add_event("exception", {"exception.message": EVENT_SECRET, "exception.type": "X"})
        span.set_status(Status(StatusCode.ERROR, STATUS_SECRET))
    raise UpstreamError(
        "The billing service is unavailable. Try again later.",
        developer_message=f"POST /v1/charge -> 401 invalid key {DEV_MESSAGE_SECRET}",
        status_code=502,
    )


@pytest.fixture
def tracer_provider() -> TracerProvider:
    provider = TracerProvider(resource=Resource.create({"deployment.note": RESOURCE_SECRET}))
    _tracer_provider_holder["provider"] = provider
    yield provider
    _tracer_provider_holder.clear()


def _catalog() -> ToolCatalog:
    catalog = ToolCatalog()
    catalog.add_tool(charge_customer, "Billing")
    return catalog


@pytest_asyncio.fixture
async def make_server(tracer_provider, mock_read_stream, mock_write_stream):
    started: list[MCPServer] = []

    async def _make(**middleware_kwargs: Any) -> tuple[MCPServer, ServerSession]:
        with pytest.warns(FutureWarning):
            mw = TelemetryPassbackMiddleware(
                service_name="billing",
                tracer_provider=tracer_provider,
                **middleware_kwargs,
            )
        settings = MCPSettings()
        settings.middleware.mask_error_details = False
        server = MCPServer(
            catalog=_catalog(),
            name="Telemetry Passback E2E",
            version="0.0.0",
            settings=settings,
            middleware=[mw],
        )
        await server.start()
        started.append(server)
        session = ServerSession(
            server=server,
            read_stream=mock_read_stream,
            write_stream=mock_write_stream,
        )
        session.mark_initialized()
        return server, session

    yield _make
    for server in started:
        await server.stop()


async def _call(server: MCPServer, session: ServerSession, *, detailed: bool) -> dict[str, Any]:
    response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "Billing_ChargeCustomer",
                "arguments": {"customer_id": "c_42"},
                "_meta": {"otel": {"traces": {"request": True, "detailed": detailed}}},
            },
        },
        session=session,
    )
    assert isinstance(response, JSONRPCResponse)
    result = response.result.model_dump(by_alias=True, exclude_none=True)
    assert result["isError"] is True
    return result


def _spans(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    traces = result["_meta"]["otel"]["traces"]
    spans = traces["resourceSpans"][0]["scopeSpans"][0]["spans"]
    return {s["name"]: s for s in spans}


def _attr_keys(span: dict[str, Any]) -> set[str]:
    return {a["key"] for a in span["attributes"]}


def _attr(span: dict[str, Any], key: str) -> Any:
    for a in span["attributes"]:
        if a["key"] == key:
            return next(iter(a["value"].values()))
    raise KeyError(key)


@pytest.mark.asyncio
@pytest.mark.parametrize("detailed", [False, True])
async def test_default_passback_returns_no_secrets(make_server, detailed):
    """With default options, no secret from the tool reaches the client."""
    server, session = await make_server()
    result = await _call(server, session, detailed=detailed)

    blob = json.dumps(result)
    for secret in SECRETS:
        assert secret not in blob, f"{secret!r} leaked in passback"

    # The span payload still identifies the call and the failure kind.
    root = _spans(result)["tools/call Billing_ChargeCustomer"]
    assert _attr(root, "mcp.tool") == "Billing_ChargeCustomer"
    assert _attr(root, "gen_ai.tool.name") == "Billing_ChargeCustomer"
    assert _attr(root, "tool_error_kind") == "UPSTREAM_RUNTIME_SERVER_ERROR"
    assert root["status"]["code"] in (0, 2)
    assert "tool_error_developer_message" not in _attr_keys(root)
    assert "tool_error_message" not in _attr_keys(root)
    # The middleware's own echo of the client's arguments keeps its value.
    assert _attr(root, "gen_ai.tool.call.arguments") == json.dumps({"customer_id": "c_42"})

    # Event names survive; their attributes go through the same allowlist.
    http_span = _spans(result)["http.client POST"]
    assert http_span["status"]["code"] == 2
    assert [e["name"] for e in http_span["events"]] == ["exception"]
    assert http_span["events"][0]["attributes"] == [
        {"key": "exception.type", "value": {"stringValue": "X"}}
    ]

    resource = result["_meta"]["otel"]["traces"]["resourceSpans"][0]["resource"]
    assert resource["attributes"] == [{"key": "service.name", "value": {"stringValue": "billing"}}]


@pytest.mark.asyncio
async def test_client_detailed_is_ignored_without_server_opt_in(make_server):
    """A client asking for detailed spans gets only the top level unless the server allows it."""
    server, session = await make_server()
    result = await _call(server, session, detailed=True)

    names = set(_spans(result))
    assert "tools/call Billing_ChargeCustomer" in names
    assert "db.query" in names  # direct child of the request span
    assert "db.connect" not in names  # grandchild: needs server opt-in
    traces = result["_meta"]["otel"]["traces"]
    assert traces["truncated"] is True
    assert traces["droppedSpanCount"] == 1


@pytest.mark.asyncio
async def test_server_opt_in_returns_detailed_spans_still_filtered(make_server):
    """allow_detailed=True returns nested spans, but attributes stay allowlisted."""
    server, session = await make_server(allow_detailed=True)
    result = await _call(server, session, detailed=True)

    spans = _spans(result)
    assert "db.connect" in spans
    assert result["_meta"]["otel"]["traces"]["truncated"] is False
    blob = json.dumps(result)
    for secret in SECRETS:
        assert secret not in blob

    # Detailed still has to be requested by the client.
    result = await _call(server, session, detailed=False)
    assert "db.connect" not in _spans(result)


@pytest.mark.asyncio
async def test_operator_can_extend_attribute_allowlist(make_server):
    """Attributes the operator adds come through; everything else is still dropped."""
    server, session = await make_server(
        extra_allowed_attributes={"db.system", "http.response.status_code"}
    )
    result = await _call(server, session, detailed=False)

    spans = _spans(result)
    assert _attr(spans["db.query"], "db.system") == "postgresql"
    assert _attr(spans["http.client POST"], "http.response.status_code") == "401"
    assert "db.statement" not in _attr_keys(spans["db.query"])
    assert "url.full" not in _attr_keys(spans["http.client POST"])
    blob = json.dumps(result)
    for secret in SECRETS:
        assert secret not in blob


@pytest.mark.asyncio
async def test_operator_opt_in_to_developer_message(make_server):
    """Exposing the developer message is possible, but only as an explicit operator choice."""
    server, session = await make_server(extra_allowed_attributes={"tool_error_developer_message"})
    result = await _call(server, session, detailed=False)

    root = _spans(result)["tools/call Billing_ChargeCustomer"]
    assert DEV_MESSAGE_SECRET in _attr(root, "tool_error_developer_message")
