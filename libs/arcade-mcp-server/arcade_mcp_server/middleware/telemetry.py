"""Telemetry passback middleware for MCP server."""

from __future__ import annotations

import json
import logging
import warnings
from contextvars import ContextVar
from typing import Any

from opentelemetry import context as otel_context
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor, TracerProvider
from opentelemetry.trace import SpanKind, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from arcade_mcp_server.middleware.base import CallNext, Middleware, MiddlewareContext
from arcade_mcp_server.types import JSONRPCResponse

logger = logging.getLogger("arcade.mcp.telemetry")


# Per-request span collection via ContextVar
_request_spans: ContextVar[list[ReadableSpan] | None] = ContextVar("_request_spans", default=None)


class ContextVarSpanCollector(SpanProcessor):
    """Collect ended spans into a per-request ContextVar bucket."""

    def on_start(self, span: Any, parent_context: Any = None) -> None:
        pass

    def on_end(self, span: ReadableSpan) -> None:
        bucket = _request_spans.get()
        if bucket is not None:
            bucket.append(span)

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int | None = None) -> bool:
        return True


def start_collecting() -> list[ReadableSpan]:
    """Begin collecting spans for the current async context."""
    bucket: list[ReadableSpan] = []
    _request_spans.set(bucket)
    return bucket


def stop_collecting() -> list[ReadableSpan]:
    """Stop collecting and return the collected spans."""
    bucket = _request_spans.get() or []
    _request_spans.set(None)
    return bucket


# Span filtering
def filter_top_level_spans(spans: list[ReadableSpan]) -> list[ReadableSpan]:
    """Keep only the root span and its direct children (depth <= 1)."""
    span_ids = {s.context.span_id for s in spans if s.context}
    root = None
    for s in spans:
        if s.parent and s.parent.span_id not in span_ids:
            root = s
            break
    if root is None:
        return spans
    root_id = root.context.span_id
    return [
        s
        for s in spans
        if s.context.span_id == root_id or (s.parent and s.parent.span_id == root_id)
    ]


# OTLP JSON serialization

_SPAN_KIND_MAP = {
    SpanKind.INTERNAL: 1,
    SpanKind.SERVER: 2,
    SpanKind.CLIENT: 3,
    SpanKind.PRODUCER: 4,
    SpanKind.CONSUMER: 5,
}
_STATUS_CODE_MAP = {StatusCode.UNSET: 0, StatusCode.OK: 1, StatusCode.ERROR: 2}


def _ns(ns: int | None) -> str:
    return str(ns) if ns is not None else "0"


def _attrs_to_kv(attrs: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not attrs:
        return []
    out: list[dict[str, Any]] = []
    for key, val in attrs.items():
        if isinstance(val, bool):
            out.append({"key": key, "value": {"boolValue": val}})
        elif isinstance(val, int):
            out.append({"key": key, "value": {"intValue": str(val)}})
        elif isinstance(val, float):
            out.append({"key": key, "value": {"doubleValue": val}})
        elif isinstance(val, str):
            out.append({"key": key, "value": {"stringValue": val}})
        elif isinstance(val, (list, tuple)):
            arr: list[dict[str, Any]] = []
            for v in val:
                if isinstance(v, str):
                    arr.append({"stringValue": v})
                elif isinstance(v, bool):
                    arr.append({"boolValue": v})
                elif isinstance(v, int):
                    arr.append({"intValue": str(v)})
                elif isinstance(v, float):
                    arr.append({"doubleValue": v})
            out.append({"key": key, "value": {"arrayValue": {"values": arr}}})
        else:
            out.append({"key": key, "value": {"stringValue": str(val)}})
    return out


def spans_to_otlp_json(
    spans: list[ReadableSpan],
    service_name: str,
) -> dict[str, Any]:
    """Convert ReadableSpan objects to OTLP JSON (ExportTraceServiceRequest)."""
    otlp_spans: list[dict[str, Any]] = []
    for span in spans:
        ctx = span.context
        if ctx is None:
            continue
        rec: dict[str, Any] = {
            "traceId": format(ctx.trace_id, "032x"),
            "spanId": format(ctx.span_id, "016x"),
            "name": span.name,
            "kind": _SPAN_KIND_MAP.get(span.kind, 0),
            "startTimeUnixNano": _ns(span.start_time),
            "endTimeUnixNano": _ns(span.end_time),
            "attributes": _attrs_to_kv(dict(span.attributes) if span.attributes else None),
            "status": {"code": _STATUS_CODE_MAP.get(span.status.status_code, 0)},
        }
        if span.parent and span.parent.span_id:
            rec["parentSpanId"] = format(span.parent.span_id, "016x")
        if span.events:
            rec["events"] = [
                {
                    "timeUnixNano": _ns(ev.timestamp),
                    "name": ev.name,
                    "attributes": _attrs_to_kv(dict(ev.attributes) if ev.attributes else None),
                }
                for ev in span.events
            ]
        otlp_spans.append(rec)

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": service_name}}],
                },
                "scopeSpans": [{"scope": {"name": "mcp-telemetry-passback"}, "spans": otlp_spans}],
            }
        ]
    }


class TelemetryPassbackMiddleware(Middleware):
    """MCP middleware implementing SEP serverExecutionTelemetry.

    .. warning:: **Provisional API** — This middleware implements a draft SEP
       (SEP-2448: server execution telemetry) that has not yet been finalized in
       the MCP specification.  The capability schema, response payload shape,
       and constructor signature may change in a future release once the SEP is
       ratified.  Pin your ``arcade-mcp-server`` version if you need stability.

    Intercepts tools/call and resources/read to:

    1. Propagate traceparent from the client for distributed tracing.
    2. Collect server-side spans during request execution (per-request
       isolation via ContextVar).
    3. Return spans in the response _meta.otel.traces.resourceSpans.
    """

    def __init__(self, service_name: str, tracer_provider: TracerProvider) -> None:
        warnings.warn(
            "TelemetryPassbackMiddleware implements a draft version of SEP "
            "(SEP-2448: server execution telemetry) that is not yet finalized. "
            "The API may change in a future release.",
            FutureWarning,
            stacklevel=2,
        )
        self._service_name = service_name
        self._tracer = tracer_provider.get_tracer(service_name)
        self._propagator = TraceContextTextMapPropagator()
        self._collector = ContextVarSpanCollector()
        tracer_provider.add_span_processor(self._collector)

    def get_capabilities(self) -> dict[str, Any]:
        """Return the serverExecutionTelemetry capability dict."""
        return {
            "serverExecutionTelemetry": {
                "version": "2026-03-01",
                "signals": {"traces": {"supported": True}},
            }
        }

    def _extract_otel_meta(self, context: MiddlewareContext[Any]) -> dict[str, Any]:
        """Extract traceparent and otel request flags from _meta."""
        mcp_ctx = context.mcp_context
        if mcp_ctx is None:
            return {}
        session = getattr(mcp_ctx, "_session", None)
        if session is None:
            return {}
        meta = getattr(session, "_request_meta", None)
        if meta is None:
            return {}

        otel_meta = getattr(meta, "otel", None)
        traces = otel_meta.get("traces", {}) if isinstance(otel_meta, dict) else {}

        return {
            "traceparent": getattr(meta, "traceparent", None),
            "request": traces.get("request", False) if isinstance(traces, dict) else False,
            "detailed": traces.get("detailed", False) if isinstance(traces, dict) else False,
        }

    def _parent_context(self, traceparent: str | None) -> Any:
        if traceparent:
            return self._propagator.extract(carrier={"traceparent": traceparent})
        return otel_context.get_current()

    def _attach_spans(self, response: Any, collected: list[ReadableSpan], detailed: bool) -> Any:
        if not detailed:
            filtered = filter_top_level_spans(collected)
            dropped = len(collected) - len(filtered)
        else:
            filtered = collected
            dropped = 0

        payload = {
            "traces": {
                "resourceSpans": spans_to_otlp_json(filtered, self._service_name).get(
                    "resourceSpans", []
                ),
                "truncated": dropped > 0,
                "droppedSpanCount": dropped,
            }
        }

        if isinstance(response, JSONRPCResponse) and response.result is not None:
            result = response.result
            if not isinstance(result, dict) and hasattr(result, "meta"):
                meta = result.meta or {}
                meta["otel"] = payload
                result.meta = meta

        return response

    @staticmethod
    def _extract_response_text(response: Any) -> str | None:
        """Extract text content from a JSONRPCResponse."""
        if not isinstance(response, JSONRPCResponse) or response.result is None:
            return None
        result = response.result
        for attr in ("content", "contents"):
            items = getattr(result, attr, None)
            if items and isinstance(items, list):
                parts = [p for c in items if (p := getattr(c, "text", None))]
                if parts:
                    return "\n".join(str(p) for p in parts)
        return None

    async def _handle_with_telemetry(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
        span_name: str,
        span_attributes: dict[str, Any] | None = None,
        tool_arguments: str | None = None,
    ) -> Any:
        """Common telemetry logic for tools/call and resources/read."""
        otel = self._extract_otel_meta(context)
        if not otel.get("request", False):
            return await call_next(context)

        start_collecting()

        try:
            with self._tracer.start_as_current_span(
                span_name,
                context=self._parent_context(otel.get("traceparent")),
                kind=SpanKind.SERVER,
                attributes=span_attributes or {},
            ) as span:
                if tool_arguments:
                    span.set_attribute(
                        "gen_ai.input.messages",
                        json.dumps([{"role": "user", "content": tool_arguments}]),
                    )
                response = await call_next(context)
                output = self._extract_response_text(response)
                if output:
                    span.set_attribute("gen_ai.tool.call.result", output[:500])
                    span.set_attribute(
                        "gen_ai.output.messages",
                        json.dumps([{"role": "assistant", "content": output}]),
                    )
        finally:
            collected = stop_collecting()

        return self._attach_spans(response, collected, otel.get("detailed", False))

    async def on_call_tool(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Intercept tools/call to collect and return server spans."""
        msg = context.message
        params = msg.get("params", {}) if isinstance(msg, dict) else {}
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        return await self._handle_with_telemetry(
            context,
            call_next,
            span_name=f"tools/call {name}",
            span_attributes={
                "mcp.method": "tools/call",
                "mcp.tool": name,
                "gen_ai.system": "mcp",
                "gen_ai.operation.name": "execute_tool",
                "gen_ai.tool.name": name,
                "gen_ai.tool.call.arguments": json.dumps(arguments) if arguments else "",
            },
            tool_arguments=json.dumps(arguments) if arguments else None,
        )

    async def on_read_resource(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Intercept resources/read to collect and return server spans."""
        msg = context.message
        params = msg.get("params", {}) if isinstance(msg, dict) else {}
        uri = params.get("uri", "")
        return await self._handle_with_telemetry(
            context,
            call_next,
            span_name=f"resources/read {uri}",
            span_attributes={
                "mcp.method": "resources/read",
                "mcp.resource.uri": uri,
                "gen_ai.system": "mcp",
                "gen_ai.operation.name": "execute_tool",
                "gen_ai.tool.name": f"resources/read {uri}",
            },
            tool_arguments=json.dumps({"uri": uri}) if uri else None,
        )
