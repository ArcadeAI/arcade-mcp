"""Telemetry passback middleware for MCP server."""

from __future__ import annotations

import json
import logging
import warnings
from collections.abc import Iterable, Mapping
from collections.abc import Set as AbstractSet
from contextvars import ContextVar
from typing import Any

from opentelemetry import context as otel_context
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor, TracerProvider
from opentelemetry.trace import SpanKind, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from arcade_mcp_server.middleware.base import CallNext, Middleware, MiddlewareContext
from arcade_mcp_server.request_context import get_request_meta
from arcade_mcp_server.types import JSONRPCResponse

logger = logging.getLogger("arcade.mcp.telemetry")


# Span and event attribute keys returned to the client by default, on any
# span. Everything else that tool code, instrumented libraries or the framework
# writes to a span (database statements, URLs, tool error messages, developer
# messages, and any ``mcp.*`` / ``gen_ai.*`` key) is dropped from the passback
# payload unless the operator adds the key through
# ``TelemetryPassbackMiddleware(extra_allowed_attributes=...)``. The request
# span's identity (``mcp.*`` / ``gen_ai.*``) and ``tool_error_kind`` are
# returned separately, with values the middleware sets itself.
DEFAULT_PASSBACK_ATTRIBUTES: frozenset[str] = frozenset({"error.type", "exception.type"})

# Span event names returned to the client by default. Events with other names
# are dropped, because event names are free-form text.
DEFAULT_PASSBACK_EVENT_NAMES: frozenset[str] = frozenset({"exception"})


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
def filter_top_level_spans(
    spans: list[ReadableSpan], root_span_id: int | None = None
) -> list[ReadableSpan]:
    """Keep only the root span and its direct children (depth <= 1).

    ``root_span_id`` names the root explicitly. Without it, the root is the
    first span whose parent is absent or not among ``spans``.
    """
    if root_span_id is None:
        span_ids = {s.context.span_id for s in spans if s.context}
        for s in spans:
            if s.context and (s.parent is None or s.parent.span_id not in span_ids):
                root_span_id = s.context.span_id
                break
    if root_span_id is None:
        return spans
    return [
        s
        for s in spans
        if (s.context and s.context.span_id == root_span_id)
        or (s.parent and s.parent.span_id == root_span_id)
    ]


def filter_descendant_spans(spans: list[ReadableSpan], root_span_id: int) -> list[ReadableSpan]:
    """Keep the root span and every span below it, dropping unrelated spans."""
    children: dict[int, list[ReadableSpan]] = {}
    for s in spans:
        if s.parent is not None:
            children.setdefault(s.parent.span_id, []).append(s)
    keep: set[int] = {root_span_id}
    stack = [root_span_id]
    while stack:
        for child in children.get(stack.pop(), []):
            if child.context and child.context.span_id not in keep:
                keep.add(child.context.span_id)
                stack.append(child.context.span_id)
    return [s for s in spans if s.context and s.context.span_id in keep]


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


def _select_attributes(
    attrs: Mapping[str, Any] | None, allowed: AbstractSet[str] | None
) -> dict[str, Any]:
    if not attrs:
        return {}
    if allowed is None:
        return dict(attrs)
    return {k: v for k, v in attrs.items() if k in allowed}


def spans_to_otlp_json(
    spans: list[ReadableSpan],
    service_name: str,
    *,
    allowed_attributes: AbstractSet[str] | None = None,
    pinned_attributes: Mapping[int, Mapping[str, Any]] | None = None,
    allowed_event_names: AbstractSet[str] | None = None,
) -> dict[str, Any]:
    """Convert ReadableSpan objects to OTLP JSON (ExportTraceServiceRequest).

    Only the span name, kind, ids, timing, status code, attributes and event
    names/attributes are serialized. Status descriptions, links and the
    tracer provider's resource attributes are never included; the resource
    carries only ``service.name``.

    Args:
        allowed_attributes: When given, only span and event attribute keys in
            this set are serialized. ``None`` serializes every attribute.
        pinned_attributes: Per span id, attributes to emit with exactly these
            values, regardless of ``allowed_attributes`` and of what other code
            later wrote to the span under the same keys.
        allowed_event_names: When given, only events with these names are
            serialized. ``None`` serializes every event.
    """
    otlp_spans: list[dict[str, Any]] = []
    for span in spans:
        ctx = span.context
        if ctx is None:
            continue
        attrs = _select_attributes(span.attributes, allowed_attributes)
        if pinned_attributes and ctx.span_id in pinned_attributes:
            attrs.update(pinned_attributes[ctx.span_id])
        rec: dict[str, Any] = {
            "traceId": format(ctx.trace_id, "032x"),
            "spanId": format(ctx.span_id, "016x"),
            "name": span.name,
            "kind": _SPAN_KIND_MAP.get(span.kind, 0),
            "startTimeUnixNano": _ns(span.start_time),
            "endTimeUnixNano": _ns(span.end_time),
            "attributes": _attrs_to_kv(attrs),
            "status": {"code": _STATUS_CODE_MAP.get(span.status.status_code, 0)},
        }
        if span.parent and span.parent.span_id:
            rec["parentSpanId"] = format(span.parent.span_id, "016x")
        events = [
            ev
            for ev in span.events or ()
            if allowed_event_names is None or ev.name in allowed_event_names
        ]
        if events:
            rec["events"] = [
                {
                    "timeUnixNano": _ns(ev.timestamp),
                    "name": ev.name,
                    "attributes": _attrs_to_kv(
                        _select_attributes(ev.attributes, allowed_attributes)
                    ),
                }
                for ev in events
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

    The payload goes to whoever called the tool, so it is filtered on the
    server's terms, independent of what other code writes to spans:

    * On the request span, the ``mcp.*`` / ``gen_ai.*`` identity, the tool
      arguments and result text (the same data the client sent and received)
      and ``tool_error_kind`` (taken from the result's
      ``_meta.arcade.errorKind``) are values this middleware sets itself.
      Values other code writes under those keys are ignored.
    * On every span, other attributes (span and event) are returned only when
      their key is in :data:`DEFAULT_PASSBACK_ATTRIBUTES` (``error.type``,
      ``exception.type``) or ``extra_allowed_attributes``. ``mcp.*`` and
      ``gen_ai.*`` keys on child spans, tool error messages, developer
      messages, database statements, URLs and anything else are dropped.
    * Events are returned only when their name is in
      :data:`DEFAULT_PASSBACK_EVENT_NAMES` (``exception``) or
      ``extra_allowed_event_names``.
    * Status descriptions, span links and the tracer provider's resource
      attributes are never returned.
    * By default only the request span and its direct children are returned.
      A client's ``detailed: true`` is ignored unless the server sets
      ``allow_detailed=True``. ``request`` and ``detailed`` must be JSON
      ``true``; any other value counts as false.

    Limits operators should know about:

    * **Span names are returned verbatim**, for the request span's children
      (and all descendants with ``allow_detailed``). Avoid instrumentation
      whose span names hold data, such as full URLs or query text.
    * Spans are collected through a ``ContextVar``, so an asyncio task first
      started while a passback request is running inherits that request's
      collection. Spans that a long-lived task started there ends later, on
      behalf of other callers, can land in the first caller's payload (still
      filtered as above).

    Args:
        service_name: ``service.name`` reported in the payload's resource.
        tracer_provider: SDK provider whose spans are collected.
        extra_allowed_attributes: Additional span/event attribute keys the
            operator accepts returning to clients, on any span. Adding
            ``tool_error_developer_message`` (or similar) exposes data the
            framework otherwise withholds from callers.
        extra_allowed_event_names: Additional span event names to return.
        allow_detailed: Let clients request the full nested span tree with
            ``_meta.otel.traces.detailed: true``. Defaults to ``False``.
    """

    def __init__(
        self,
        service_name: str,
        tracer_provider: TracerProvider,
        *,
        extra_allowed_attributes: Iterable[str] = (),
        extra_allowed_event_names: Iterable[str] = (),
        allow_detailed: bool = False,
    ) -> None:
        for arg_name, value in (
            ("extra_allowed_attributes", extra_allowed_attributes),
            ("extra_allowed_event_names", extra_allowed_event_names),
        ):
            if isinstance(value, str):
                raise TypeError(f"{arg_name} must be a collection of strings, not a string")
        warnings.warn(
            "TelemetryPassbackMiddleware implements a draft version of SEP "
            "(SEP-2448: server execution telemetry) that is not yet finalized. "
            "The API may change in a future release.",
            FutureWarning,
            stacklevel=2,
        )
        self._service_name = service_name
        self._allowed_attributes = DEFAULT_PASSBACK_ATTRIBUTES | frozenset(extra_allowed_attributes)
        self._allowed_event_names = DEFAULT_PASSBACK_EVENT_NAMES | frozenset(
            extra_allowed_event_names
        )
        self._allow_detailed = allow_detailed
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
        meta = get_request_meta()
        if meta is None:
            return {}

        otel_meta = getattr(meta, "otel", None)
        traces = otel_meta.get("traces", {}) if isinstance(otel_meta, dict) else {}

        if not isinstance(traces, dict):
            traces = {}

        return {
            "traceparent": getattr(meta, "traceparent", None),
            "request": traces.get("request") is True,
            "detailed": traces.get("detailed") is True,
        }

    def _parent_context(self, traceparent: str | None) -> Any:
        if traceparent:
            return self._propagator.extract(carrier={"traceparent": traceparent})
        return otel_context.get_current()

    def _attach_spans(
        self,
        response: Any,
        collected: list[ReadableSpan],
        detailed: bool,
        root_span_id: int,
        own_attributes: Mapping[str, Any],
    ) -> Any:
        if detailed and self._allow_detailed:
            filtered = filter_descendant_spans(collected, root_span_id)
        else:
            if detailed:
                logger.debug(
                    "Client requested detailed spans; returning top-level spans only "
                    "because allow_detailed is not enabled"
                )
            filtered = filter_top_level_spans(collected, root_span_id)
        dropped = len(collected) - len(filtered)

        payload = {
            "traces": {
                "resourceSpans": spans_to_otlp_json(
                    filtered,
                    self._service_name,
                    allowed_attributes=self._allowed_attributes,
                    pinned_attributes={root_span_id: own_attributes},
                    allowed_event_names=self._allowed_event_names,
                ).get("resourceSpans", []),
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
    def _extract_error_kind(response: Any) -> str | None:
        """Return the error kind the server reported in ``_meta.arcade.errorKind``."""
        if not isinstance(response, JSONRPCResponse) or response.result is None:
            return None
        result = response.result
        if getattr(result, "isError", None) is not True:
            return None
        meta = getattr(result, "meta", None)
        arcade = meta.get("arcade") if isinstance(meta, dict) else None
        kind = arcade.get("errorKind") if isinstance(arcade, dict) else None
        return kind if isinstance(kind, str) else None

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
        # Attributes this middleware writes to its own span. They are returned
        # with exactly these values; everything else goes through the allowlist.
        own_attributes: dict[str, Any] = dict(span_attributes or {})

        try:
            with self._tracer.start_as_current_span(
                span_name,
                context=self._parent_context(otel.get("traceparent")),
                kind=SpanKind.SERVER,
                attributes=own_attributes,
            ) as span:
                root_span_id = span.get_span_context().span_id

                def record(key: str, value: str) -> None:
                    own_attributes[key] = value
                    span.set_attribute(key, value)

                if tool_arguments:
                    record(
                        "gen_ai.input.messages",
                        json.dumps([{"role": "user", "content": tool_arguments}]),
                    )
                response = await call_next(context)
                error_kind = self._extract_error_kind(response)
                if error_kind:
                    record("tool_error_kind", error_kind)
                output = self._extract_response_text(response)
                if output:
                    record("gen_ai.tool.call.result", output[:500])
                    record(
                        "gen_ai.output.messages",
                        json.dumps([{"role": "assistant", "content": output}]),
                    )
        finally:
            collected = stop_collecting()

        return self._attach_spans(
            response,
            collected,
            otel.get("detailed") is True,
            root_span_id,
            own_attributes,
        )

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
