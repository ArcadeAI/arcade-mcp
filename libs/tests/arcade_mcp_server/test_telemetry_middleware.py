"""Tests for Telemetry Passback Middleware."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from arcade_mcp_server.middleware.base import MiddlewareContext
from arcade_mcp_server.middleware.telemetry import (
    DEFAULT_PASSBACK_ATTRIBUTES,
    DEFAULT_PASSBACK_EVENT_NAMES,
    ContextVarSpanCollector,
    TelemetryPassbackMiddleware,
    _attrs_to_kv,
    _ns,
    _request_spans,
    filter_descendant_spans,
    filter_top_level_spans,
    spans_to_otlp_json,
    start_collecting,
    stop_collecting,
)
from arcade_mcp_server.types import (
    CallToolResult,
    JSONRPCResponse,
    ReadResourceResult,
    TextContent,
    TextResourceContents,
)
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.trace import SpanKind, StatusCode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_span(
    *,
    name: str = "test-span",
    trace_id: int = 0xABCD,
    span_id: int = 0x1234,
    parent_span_id: int | None = None,
    kind: SpanKind = SpanKind.INTERNAL,
    start_time: int = 1000,
    end_time: int = 2000,
    status_code: StatusCode = StatusCode.UNSET,
    attributes: dict | None = None,
    events: list | None = None,
) -> ReadableSpan:
    """Build a lightweight mock ReadableSpan."""
    span = MagicMock(spec=ReadableSpan)
    ctx = MagicMock()
    ctx.trace_id = trace_id
    ctx.span_id = span_id
    span.context = ctx
    span.name = name
    span.kind = kind
    span.start_time = start_time
    span.end_time = end_time

    status = MagicMock()
    status.status_code = status_code
    span.status = status

    if parent_span_id is not None:
        parent = MagicMock()
        parent.span_id = parent_span_id
        span.parent = parent
    else:
        span.parent = None

    span.attributes = attributes
    span.events = events or []
    return span


def _make_tool_response(*, text: str = "hello") -> JSONRPCResponse[CallToolResult]:
    """Build a JSONRPCResponse wrapping a CallToolResult."""
    return JSONRPCResponse(
        id="1",
        result=CallToolResult(
            content=[TextContent(type="text", text=text)],
            isError=False,
        ),
    )


def _make_resource_response(*, text: str = "hello") -> JSONRPCResponse[ReadResourceResult]:
    """Build a JSONRPCResponse wrapping a ReadResourceResult."""
    return JSONRPCResponse(
        id="1",
        result=ReadResourceResult(
            contents=[TextResourceContents(uri="file:///test", text=text)],
        ),
    )


# ===========================================================================
# ContextVarSpanCollector
# ===========================================================================


class TestContextVarSpanCollector:
    """Test ContextVarSpanCollector class."""

    @pytest.fixture(autouse=True)
    def _reset_contextvar(self):
        """Ensure the ContextVar is clean before and after each test."""
        _request_spans.set(None)
        yield
        _request_spans.set(None)

    def test_spans_collected_when_bucket_active(self):
        collector = ContextVarSpanCollector()
        bucket = start_collecting()
        span = _make_span()
        collector.on_end(span)
        assert span in bucket

    def test_spans_not_collected_when_bucket_inactive(self):
        collector = ContextVarSpanCollector()
        span = _make_span()
        collector.on_end(span)
        # No active bucket; span is silently dropped
        assert _request_spans.get() is None

    def test_on_start_is_noop(self):
        collector = ContextVarSpanCollector()
        collector.on_start(MagicMock())

    def test_shutdown_is_noop(self):
        collector = ContextVarSpanCollector()
        collector.shutdown()

    def test_force_flush_returns_true(self):
        collector = ContextVarSpanCollector()
        assert collector.force_flush() is True


# ===========================================================================
# start_collecting / stop_collecting
# ===========================================================================


class TestCollectingLifecycle:
    """Test start_collecting / stop_collecting."""

    @pytest.fixture(autouse=True)
    def _reset_contextvar(self):
        _request_spans.set(None)
        yield
        _request_spans.set(None)

    def test_lifecycle(self):
        bucket = start_collecting()
        assert bucket == []
        assert _request_spans.get() is bucket
        span = _make_span()
        bucket.append(span)
        result = stop_collecting()
        assert span in result
        assert _request_spans.get() is None

    def test_idempotent_stop(self):
        start_collecting()
        stop_collecting()
        result = stop_collecting()
        assert result == []

    def test_isolation_between_calls(self):
        bucket1 = start_collecting()
        bucket1.append(_make_span(name="a"))
        stop_collecting()

        bucket2 = start_collecting()
        assert bucket2 == []


# ===========================================================================
# filter_top_level_spans
# ===========================================================================


class TestFilterTopLevelSpans:
    def test_root_and_children_kept_grandchildren_dropped(self):
        root = _make_span(name="root", span_id=1, parent_span_id=999)
        child = _make_span(name="child", span_id=2, parent_span_id=1)
        grandchild = _make_span(name="grandchild", span_id=3, parent_span_id=2)
        result = filter_top_level_spans([root, child, grandchild])
        names = {s.name for s in result}
        assert names == {"root", "child"}

    def test_empty_list(self):
        assert filter_top_level_spans([]) == []

    def test_single_span_no_parent(self):
        span = _make_span(name="only", span_id=1)
        result = filter_top_level_spans([span])
        assert result == [span]

    def test_single_span_with_external_parent(self):
        span = _make_span(name="only", span_id=1, parent_span_id=999)
        result = filter_top_level_spans([span])
        assert len(result) == 1
        assert result[0].name == "only"

    def test_root_without_parent_still_drops_grandchildren(self):
        """A root with no parent (no client traceparent) must not disable filtering."""
        root = _make_span(name="root", span_id=1)
        child = _make_span(name="child", span_id=2, parent_span_id=1)
        grandchild = _make_span(name="grandchild", span_id=3, parent_span_id=2)
        result = filter_top_level_spans([grandchild, child, root])
        assert {s.name for s in result} == {"root", "child"}

    def test_explicit_root_span_id(self):
        other = _make_span(name="other", span_id=7)
        root = _make_span(name="root", span_id=1, parent_span_id=999)
        child = _make_span(name="child", span_id=2, parent_span_id=1)
        grandchild = _make_span(name="grandchild", span_id=3, parent_span_id=2)
        result = filter_top_level_spans([other, grandchild, child, root], root_span_id=1)
        assert {s.name for s in result} == {"root", "child"}


class TestFilterDescendantSpans:
    def test_keeps_whole_subtree_and_drops_unrelated(self):
        root = _make_span(name="root", span_id=1, parent_span_id=999)
        child = _make_span(name="child", span_id=2, parent_span_id=1)
        grandchild = _make_span(name="grandchild", span_id=3, parent_span_id=2)
        unrelated = _make_span(name="unrelated", span_id=4, parent_span_id=999)
        result = filter_descendant_spans([grandchild, child, unrelated, root], root_span_id=1)
        assert {s.name for s in result} == {"root", "child", "grandchild"}


# ===========================================================================
# _attrs_to_kv
# ===========================================================================


class TestAttrsToKv:
    def test_bool_value(self):
        result = _attrs_to_kv({"flag": True})
        assert result == [{"key": "flag", "value": {"boolValue": True}}]

    def test_int_value(self):
        result = _attrs_to_kv({"count": 42})
        assert result == [{"key": "count", "value": {"intValue": "42"}}]

    def test_float_value(self):
        result = _attrs_to_kv({"rate": 3.14})
        assert result == [{"key": "rate", "value": {"doubleValue": 3.14}}]

    def test_str_value(self):
        result = _attrs_to_kv({"name": "foo"})
        assert result == [{"key": "name", "value": {"stringValue": "foo"}}]

    def test_list_value(self):
        result = _attrs_to_kv({"tags": ["a", "b"]})
        assert result == [
            {"key": "tags", "value": {"arrayValue": {"values": [{"stringValue": "a"}, {"stringValue": "b"}]}}}
        ]

    def test_fallback_to_string(self):
        result = _attrs_to_kv({"obj": object()})
        assert len(result) == 1
        assert "stringValue" in result[0]["value"]

    def test_empty_attrs(self):
        assert _attrs_to_kv({}) == []

    def test_none_attrs(self):
        assert _attrs_to_kv(None) == []


# ===========================================================================
# spans_to_otlp_json
# ===========================================================================


class TestSpansToOtlpJson:
    def test_full_serialization(self):
        event = MagicMock()
        event.timestamp = 1500
        event.name = "log"
        event.attributes = {"msg": "hi"}

        span = _make_span(
            name="op",
            trace_id=0xABCDEF,
            span_id=0x123456,
            parent_span_id=0x111,
            kind=SpanKind.SERVER,
            start_time=1000,
            end_time=2000,
            status_code=StatusCode.OK,
            attributes={"k": "v"},
            events=[event],
        )

        result = spans_to_otlp_json([span], "test-service")
        assert "resourceSpans" in result
        rs = result["resourceSpans"][0]
        assert rs["resource"]["attributes"][0]["value"]["stringValue"] == "test-service"
        otlp_span = rs["scopeSpans"][0]["spans"][0]
        assert otlp_span["name"] == "op"
        assert otlp_span["kind"] == 2  # SERVER
        assert otlp_span["status"]["code"] == 1  # OK
        assert "parentSpanId" in otlp_span
        assert len(otlp_span["events"]) == 1

    def test_span_without_parent(self):
        span = _make_span(name="root", span_id=1)
        result = spans_to_otlp_json([span], "svc")
        otlp_span = result["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert "parentSpanId" not in otlp_span

    def test_span_with_no_context_skipped(self):
        span = _make_span()
        span.context = None
        result = spans_to_otlp_json([span], "svc")
        assert result["resourceSpans"][0]["scopeSpans"][0]["spans"] == []

    def test_status_error(self):
        span = _make_span(status_code=StatusCode.ERROR)
        result = spans_to_otlp_json([span], "svc")
        otlp_span = result["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert otlp_span["status"]["code"] == 2

    def test_allowed_attributes_filter_span_and_event_attributes(self):
        event = MagicMock()
        event.timestamp = 1500
        event.name = "exception"
        event.attributes = {"exception.type": "ValueError", "exception.message": "secret"}
        span = _make_span(
            attributes={"mcp.tool": "t", "db.statement": "SELECT secret"},
            events=[event],
        )
        result = spans_to_otlp_json(
            [span], "svc", allowed_attributes={"mcp.tool", "exception.type"}
        )
        otlp_span = result["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert otlp_span["attributes"] == [{"key": "mcp.tool", "value": {"stringValue": "t"}}]
        assert otlp_span["events"][0]["name"] == "exception"
        assert otlp_span["events"][0]["attributes"] == [
            {"key": "exception.type", "value": {"stringValue": "ValueError"}}
        ]

    def test_allowed_event_names_drop_other_events(self):
        kept = MagicMock()
        kept.timestamp = 1
        kept.name = "exception"
        kept.attributes = None
        dropped = MagicMock()
        dropped.timestamp = 2
        dropped.name = "retry with token secret"
        dropped.attributes = None
        span = _make_span(events=[kept, dropped])
        result = spans_to_otlp_json([span], "svc", allowed_event_names={"exception"})
        otlp_span = result["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert [e["name"] for e in otlp_span["events"]] == ["exception"]

    def test_pinned_attributes_override_recorded_values(self):
        span = _make_span(span_id=5, attributes={"gen_ai.tool.call.result": "overwritten"})
        result = spans_to_otlp_json(
            [span],
            "svc",
            allowed_attributes=frozenset(),
            pinned_attributes={5: {"gen_ai.tool.call.result": "original"}},
        )
        otlp_span = result["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert otlp_span["attributes"] == [
            {"key": "gen_ai.tool.call.result", "value": {"stringValue": "original"}}
        ]


# ===========================================================================
# _ns
# ===========================================================================


class TestNs:
    def test_zero(self):
        assert _ns(0) == "0"

    def test_none(self):
        assert _ns(None) == "0"

    def test_positive(self):
        assert _ns(123456) == "123456"


# ===========================================================================
# TelemetryPassbackMiddleware
# ===========================================================================


def _make_otel_context(*, request: bool = True, detailed: bool = False, traceparent: str | None = None):
    """Build a MiddlewareContext with otel meta configured.

    Sets the request_context ContextVar so TelemetryPassbackMiddleware reads it
    from the ContextVar instead of the old session._request_meta attribute.
    """
    from arcade_mcp_server.request_context import set_request_meta

    meta_dict = {
        "traceparent": traceparent,
        "otel": {"traces": {"request": request, "detailed": detailed}},
    }
    # Set the ContextVar — tests must reset via _reset_contextvar fixture or manually
    set_request_meta(meta_dict)

    session = MagicMock()
    mcp_ctx = MagicMock()
    mcp_ctx._session = session
    return mcp_ctx


@pytest.mark.filterwarnings("ignore::FutureWarning")
class TestTelemetryPassbackMiddleware:
    """Test TelemetryPassbackMiddleware class."""

    @pytest.fixture(autouse=True)
    def _reset_contextvar(self):
        from arcade_mcp_server.request_context import _current_request_meta

        _request_spans.set(None)
        _current_request_meta.set(None)
        yield
        _request_spans.set(None)
        _current_request_meta.set(None)

    @pytest.fixture
    def tracer_provider(self):
        return TracerProvider()

    @pytest.fixture
    def middleware(self, tracer_provider):
        return TelemetryPassbackMiddleware(
            service_name="test-svc",
            tracer_provider=tracer_provider,
        )

    @pytest.fixture
    def tool_call_context(self):
        """Context for a tools/call with otel request=True."""
        return MiddlewareContext(
            message={"method": "tools/call", "params": {"name": "my_tool", "arguments": {"x": 1}}},
            mcp_context=_make_otel_context(request=True, detailed=False),
            method="tools/call",
            request_id="req-1",
        )

    @pytest.fixture
    def tool_call_context_no_request(self):
        """Context for a tools/call with otel request=False."""
        return MiddlewareContext(
            message={"method": "tools/call", "params": {"name": "my_tool", "arguments": {}}},
            mcp_context=_make_otel_context(request=False),
            method="tools/call",
            request_id="req-2",
        )

    @pytest.fixture
    def resource_read_context(self):
        """Context for resources/read with otel request=True."""
        return MiddlewareContext(
            message={"method": "resources/read", "params": {"uri": "file:///foo.txt"}},
            mcp_context=_make_otel_context(request=True, detailed=False),
            method="resources/read",
            request_id="req-3",
        )

    # --- get_capabilities ---

    def test_get_capabilities(self, middleware):
        caps = middleware.get_capabilities()
        assert "serverExecutionTelemetry" in caps
        assert caps["serverExecutionTelemetry"]["signals"]["traces"]["supported"] is True

    # --- on_call_tool: request=False passthrough ---

    @pytest.mark.asyncio
    async def test_on_call_tool_no_request_passthrough(self, middleware, tool_call_context_no_request):
        sentinel = object()

        async def handler(ctx):
            return sentinel

        result = await middleware.on_call_tool(tool_call_context_no_request, handler)
        assert result is sentinel

    # --- on_call_tool: request=True attaches spans ---

    @pytest.mark.asyncio
    async def test_on_call_tool_with_request_attaches_spans(self, middleware, tool_call_context):
        resp = _make_tool_response(text="tool output")

        async def handler(ctx):
            return resp

        result = await middleware.on_call_tool(tool_call_context, handler)
        meta = result.result.meta
        assert meta is not None
        assert "otel" in meta
        assert "traces" in meta["otel"]
        assert "resourceSpans" in meta["otel"]["traces"]

    # --- on_read_resource ---

    @pytest.mark.asyncio
    async def test_on_read_resource_attaches_spans(self, middleware, resource_read_context):
        resp = _make_resource_response(text="resource content")

        async def handler(ctx):
            return resp

        result = await middleware.on_read_resource(resource_read_context, handler)
        meta = result.result.meta
        assert meta is not None
        assert "otel" in meta
        assert "traces" in meta["otel"]

    # --- detailed=True vs detailed=False ---

    @pytest.mark.asyncio
    async def test_detailed_true_returns_all_spans(self, tracer_provider):
        mw = TelemetryPassbackMiddleware(
            service_name="svc", tracer_provider=tracer_provider, allow_detailed=True
        )

        context = MiddlewareContext(
            message={"method": "tools/call", "params": {"name": "t", "arguments": {}}},
            mcp_context=_make_otel_context(request=True, detailed=True),
            method="tools/call",
        )

        resp = _make_tool_response()

        async def handler(ctx):
            return resp

        result = await mw.on_call_tool(context, handler)
        otel = result.result.meta["otel"]["traces"]
        assert otel["truncated"] is False
        assert otel["droppedSpanCount"] == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("allow_detailed", [False, True])
    async def test_detailed_requires_server_opt_in(self, tracer_provider, allow_detailed):
        mw = TelemetryPassbackMiddleware(
            service_name="svc", tracer_provider=tracer_provider, allow_detailed=allow_detailed
        )
        tracer = tracer_provider.get_tracer("tool")
        context = MiddlewareContext(
            message={"method": "tools/call", "params": {"name": "t", "arguments": {}}},
            mcp_context=_make_otel_context(request=True, detailed=True),
            method="tools/call",
        )

        async def handler(ctx):
            with tracer.start_as_current_span("phase"), tracer.start_as_current_span("leaf"):
                pass
            return _make_tool_response()

        result = await mw.on_call_tool(context, handler)
        traces = result.result.meta["otel"]["traces"]
        names = {s["name"] for s in traces["resourceSpans"][0]["scopeSpans"][0]["spans"]}
        if allow_detailed:
            assert names == {"tools/call t", "phase", "leaf"}
            assert traces["truncated"] is False
        else:
            assert names == {"tools/call t", "phase"}
            assert traces["truncated"] is True
            assert traces["droppedSpanCount"] == 1

    @pytest.mark.asyncio
    async def test_unlisted_attributes_dropped_and_extra_allowed_kept(self, tracer_provider):
        mw = TelemetryPassbackMiddleware(
            service_name="svc",
            tracer_provider=tracer_provider,
            extra_allowed_attributes=["app.phase"],
        )
        tracer = tracer_provider.get_tracer("tool")
        context = MiddlewareContext(
            message={"method": "tools/call", "params": {"name": "t", "arguments": {"x": 1}}},
            mcp_context=_make_otel_context(request=True),
            method="tools/call",
        )

        async def handler(ctx):
            with tracer.start_as_current_span("phase") as span:
                span.set_attribute("app.phase", "fetch")
                span.set_attribute("url.full", "https://x.example/?api_key=secret")
            return _make_tool_response(text="done")

        result = await mw.on_call_tool(context, handler)
        spans = result.result.meta["otel"]["traces"]["resourceSpans"][0]["scopeSpans"][0]["spans"]
        by_name = {s["name"]: {a["key"] for a in s["attributes"]} for s in spans}
        assert by_name["phase"] == {"app.phase"}
        assert by_name["tools/call t"] == {
            "mcp.method",
            "mcp.tool",
            "gen_ai.system",
            "gen_ai.operation.name",
            "gen_ai.tool.name",
            "gen_ai.tool.call.arguments",
            "gen_ai.input.messages",
            "gen_ai.tool.call.result",
            "gen_ai.output.messages",
        }

    @pytest.mark.parametrize("arg", ["extra_allowed_attributes", "extra_allowed_event_names"])
    def test_extra_allowlists_reject_bare_string(self, tracer_provider, arg):
        with pytest.raises(TypeError, match="not a string"):
            TelemetryPassbackMiddleware(
                service_name="svc", tracer_provider=tracer_provider, **{arg: "a.b"}
            )

    def test_default_allowlists(self):
        assert DEFAULT_PASSBACK_ATTRIBUTES == {"error.type", "exception.type"}
        assert DEFAULT_PASSBACK_EVENT_NAMES == {"exception"}

    def test_defaults_reexported_from_middleware_package(self):
        from arcade_mcp_server import middleware

        assert middleware.DEFAULT_PASSBACK_ATTRIBUTES is DEFAULT_PASSBACK_ATTRIBUTES
        assert middleware.DEFAULT_PASSBACK_EVENT_NAMES is DEFAULT_PASSBACK_EVENT_NAMES

    @pytest.mark.asyncio
    @pytest.mark.parametrize("report_kind", [True, False])
    async def test_tool_error_kind_comes_from_result_not_span(self, tracer_provider, report_kind):
        """tool_error_kind is the result's _meta.arcade.errorKind, never the span's value."""
        from opentelemetry import trace

        mw = TelemetryPassbackMiddleware(service_name="svc", tracer_provider=tracer_provider)
        context = MiddlewareContext(
            message={"method": "tools/call", "params": {"name": "t", "arguments": {}}},
            mcp_context=_make_otel_context(request=True),
            method="tools/call",
        )

        async def handler(ctx):
            trace.get_current_span().set_attribute("tool_error_kind", "sk_live_span_secret")
            return JSONRPCResponse(
                id="1",
                result=CallToolResult(
                    content=[TextContent(type="text", text="failed")],
                    isError=True,
                    _meta={"arcade": {"errorKind": "TOOL_RUNTIME_FATAL"}} if report_kind else None,
                ),
            )

        result = await mw.on_call_tool(context, handler)
        spans = result.result.meta["otel"]["traces"]["resourceSpans"][0]["scopeSpans"][0]["spans"]
        attrs = {a["key"]: a["value"] for a in spans[0]["attributes"]}
        if report_kind:
            assert attrs["tool_error_kind"] == {"stringValue": "TOOL_RUNTIME_FATAL"}
        else:
            assert "tool_error_kind" not in attrs
        assert "sk_live_span_secret" not in str(result.result.meta)

    @pytest.mark.asyncio
    async def test_detailed_excludes_spans_outside_request_subtree(self, tracer_provider):
        """With allow_detailed, spans that ended during the call but are not
        descendants of the request span are not returned."""
        from opentelemetry import context as otel_context

        mw = TelemetryPassbackMiddleware(
            service_name="svc", tracer_provider=tracer_provider, allow_detailed=True
        )
        tracer = tracer_provider.get_tracer("tool")
        context = MiddlewareContext(
            message={"method": "tools/call", "params": {"name": "t", "arguments": {}}},
            mcp_context=_make_otel_context(request=True, detailed=True),
            method="tools/call",
        )

        async def handler(ctx):
            with tracer.start_as_current_span("phase"), tracer.start_as_current_span("leaf"):
                pass
            # A new root trace, ended inside the collection window.
            with tracer.start_as_current_span("unrelated", context=otel_context.Context()):
                pass
            return _make_tool_response()

        result = await mw.on_call_tool(context, handler)
        traces = result.result.meta["otel"]["traces"]
        names = {s["name"] for s in traces["resourceSpans"][0]["scopeSpans"][0]["spans"]}
        assert names == {"tools/call t", "phase", "leaf"}
        assert traces["droppedSpanCount"] == 1

    # --- traceparent propagation ---

    @pytest.mark.asyncio
    async def test_traceparent_propagation(self, tracer_provider):
        mw = TelemetryPassbackMiddleware(service_name="svc", tracer_provider=tracer_provider)

        context = MiddlewareContext(
            message={"method": "tools/call", "params": {"name": "t", "arguments": {}}},
            mcp_context=_make_otel_context(
                request=True,
                detailed=True,
                traceparent="00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
            ),
            method="tools/call",
        )

        resp = _make_tool_response()

        async def handler(ctx):
            return resp

        result = await mw.on_call_tool(context, handler)
        assert result.result.meta is not None
        assert "otel" in result.result.meta

    # --- error in call_next — spans still cleaned up ---

    @pytest.mark.asyncio
    async def test_error_in_call_next_cleans_up_spans(self, middleware, tool_call_context):
        async def handler(ctx):
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await middleware.on_call_tool(tool_call_context, handler)

        assert _request_spans.get() is None

    # --- _extract_response_text ---

    def test_extract_response_text_with_content(self, middleware):
        resp = _make_tool_response(text="hello")
        assert middleware._extract_response_text(resp) == "hello"

    def test_extract_response_text_with_contents(self, middleware):
        resp = _make_resource_response(text="world")
        assert middleware._extract_response_text(resp) == "world"

    def test_extract_response_text_no_text(self, middleware):
        # Empty text is falsy, filtered out by _extract_response_text
        resp = _make_tool_response(text="")
        assert middleware._extract_response_text(resp) is None

    def test_extract_response_text_non_jsonrpc(self, middleware):
        assert middleware._extract_response_text({"not": "a response"}) is None

    def test_extract_response_text_none_result(self, middleware):
        resp = JSONRPCResponse(id="1", result={})
        assert middleware._extract_response_text(resp) is None


# ===========================================================================
# Middleware base class default get_capabilities
# ===========================================================================


class TestMiddlewareBaseGetCapabilities:
    def test_default_returns_empty_dict(self):
        from arcade_mcp_server.middleware.base import Middleware

        mw = Middleware()
        assert mw.get_capabilities() == {}
