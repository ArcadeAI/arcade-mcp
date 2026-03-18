"""
MCP Server Execution Telemetry (SEP) — span passback support.

Provides utilities for collecting OpenTelemetry spans during MCP request
handling and serializing them as OTLP JSON for return in _meta.otel.
"""

from __future__ import annotations

import logging
from typing import Any

from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

logger = logging.getLogger(__name__)

SERVER_EXECUTION_TELEMETRY_CAPABILITY = {
    "version": "2026-03-01",
    "signals": {"traces": {"supported": True}},
}


def should_passback(meta: dict[str, Any] | None) -> tuple[bool, bool]:
    """Check if the client requested span passback via _meta.otel.

    Returns (enabled, detailed) where:
      - enabled: client set otel.traces.request = true
      - detailed: client set otel.traces.detailed = true (full span tree)
    """
    if not meta:
        return False, False
    otel = meta.get("otel")
    if not isinstance(otel, dict):
        return False, False
    traces = otel.get("traces")
    if not isinstance(traces, dict):
        return False, False
    enabled = traces.get("request") is True
    detailed = traces.get("detailed") is True
    return enabled, detailed


def parse_traceparent(meta: dict[str, Any] | None) -> trace.context_api.Context | None:
    """Extract W3C traceparent from _meta and return an OTel Context.

    traceparent lives directly in _meta (outside the otel key), per SEP-414.
    """
    if not meta:
        return None
    traceparent = meta.get("traceparent")
    if not traceparent or not isinstance(traceparent, str):
        return None
    return extract(carrier={"traceparent": traceparent})


class PassbackCollector:
    """Collects spans in-memory for a single request, separate from the
    server's own OTel pipeline.

    Uses its own TracerProvider + InMemorySpanExporter so passback spans
    are never sent to the server's telemetry backend.
    """

    def __init__(self, service_name: str = "mcp-server") -> None:
        self._exporter = InMemorySpanExporter()
        resource = Resource.create({"service.name": service_name})
        self._provider = TracerProvider(resource=resource)
        self._provider.add_span_processor(SimpleSpanProcessor(self._exporter))
        self._tracer = self._provider.get_tracer("mcp-span-passback")

    @property
    def tracer(self) -> trace.Tracer:
        return self._tracer

    def collect(self) -> list[Any]:
        """Return finished ReadableSpan objects."""
        return list(self._exporter.get_finished_spans())

    def shutdown(self) -> None:
        self._provider.shutdown()


def serialize_spans(spans: list[Any]) -> list[dict[str, Any]]:
    """Serialize ReadableSpan objects to the OTLP JSON resourceSpans array.

    Returns the value to embed at _meta.otel.traces.resourceSpans — an array
    that can be wrapped in {"resourceSpans": ...} and POSTed to /v1/traces.
    """
    if not spans:
        return []

    try:
        from google.protobuf.json_format import MessageToDict
        from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans

        pb = encode_spans(spans)
        d = MessageToDict(pb)
        return d.get("resourceSpans", [])
    except Exception:
        logger.exception("Failed to serialize passback spans")
        return []


def build_passback_meta(resource_spans: list[dict[str, Any]]) -> dict[str, Any]:
    """Construct the _meta dict containing passback telemetry.

    Returns a dict suitable for setting as CallToolResult.meta or
    ReadResourceResult.meta (serialized as _meta).
    """
    return {
        "otel": {
            "traces": {
                "resourceSpans": resource_spans,
            },
        },
    }
