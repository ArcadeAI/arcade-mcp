"""LangChain ReAct agent with SEP-2448: MCP server execution telemetry.

Consumer-side reference implementation of cross-org distributed tracing:

* Connects to an Arcade MCP Gmail server via streamable HTTP.
* Authenticates using MCP OAuth 2.1 (automatic via the MCP SDK).
* Detects the ``serverExecutionTelemetry`` capability.
* Dynamically discovers tools and wraps them with span passback.
* Passes ``traceparent`` + requests span passback via ``_meta.otel``.
* Receives server spans and ingests them into Jaeger / Galileo.
* Handles Google OAuth authorization flow for Gmail (one-time consent).

Two-act demo:
  Act 1 (--no-passback): Opaque tool call -- server is a black box
  Act 2 (default):       Rich span tree via passback reveals server internals
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPHTTPSpanExporter,
)
from opentelemetry.instrumentation.langchain import LangchainInstrumentor
from opentelemetry.instrumentation.langchain.callback_handler import (
    TraceloopCallbackHandler,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, set_span_in_context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from pydantic import Field, create_model

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

log = logging.getLogger(__name__)

JAEGER_GRPC = "localhost:4317"
JAEGER_HTTP = "http://localhost:4318/v1/traces"
JAEGER_UI = "http://localhost:16686"

_passback_stats: dict[str, Any] = {"span_count": 0, "truncated": False, "dropped": 0}


# --------------------------------------
# MCP OAuth 2.1 (handled by the MCP SDK
# --------------------------------------

_OAUTH_TOKEN_FILE = _PROJECT_ROOT / ".oauth_tokens.json"
_OAUTH_CLIENT_FILE = _PROJECT_ROOT / ".oauth_client.json"
_CALLBACK_PORT = 9905


class FileTokenStorage(TokenStorage):
    """Persist OAuth tokens and client registration to disk between runs."""

    async def get_tokens(self) -> OAuthToken | None:
        if _OAUTH_TOKEN_FILE.exists():
            return OAuthToken.model_validate_json(_OAUTH_TOKEN_FILE.read_text())
        return None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        _OAUTH_TOKEN_FILE.write_text(tokens.model_dump_json())

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        if _OAUTH_CLIENT_FILE.exists():
            return OAuthClientInformationFull.model_validate_json(_OAUTH_CLIENT_FILE.read_text())
        return None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        _OAUTH_CLIENT_FILE.write_text(client_info.model_dump_json())


async def _handle_redirect(authorization_url: str) -> None:
    """Open the browser for OAuth consent."""
    print("\n  Opening browser for authorization...")
    print(f"  URL: {authorization_url}\n")
    webbrowser.open(authorization_url)


async def _handle_callback() -> tuple[str, str | None]:
    """Start a local HTTP server, wait for the OAuth redirect, extract the code."""
    loop = asyncio.get_event_loop()
    future: asyncio.Future[tuple[str, str | None]] = loop.create_future()

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            qs = parse_qs(urlparse(self.path).query)
            code = qs.get("code", [None])[0]
            state = qs.get("state", [None])[0]
            if code:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<h2>Authorization successful!</h2><p>You can close this tab.</p>"
                )
                loop.call_soon_threadsafe(future.set_result, (code, state))
            else:
                error = qs.get("error", ["unknown"])[0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<h2>Authorization failed: {error}</h2>".encode())
                loop.call_soon_threadsafe(
                    future.set_exception, RuntimeError(f"OAuth error: {error}")
                )

        def log_message(self, fmt: str, *args: Any) -> None:
            pass

    server = HTTPServer(("127.0.0.1", _CALLBACK_PORT), _Handler)

    def _serve() -> None:
        server.handle_request()
        server.server_close()

    await loop.run_in_executor(None, _serve)
    return await future


# -----------------------
# Span ingestion helpers
# -----------------------


def _count_spans(resource_spans: list[dict[str, Any]]) -> int:
    return sum(len(ss.get("spans", [])) for rs in resource_spans for ss in rs.get("scopeSpans", []))


def _hex_ids_to_base64(resource_spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert hex trace/span IDs to base64 for protobuf ``ParseDict``."""
    import base64
    import copy

    _ID_FIELDS = ("traceId", "spanId", "parentSpanId")
    converted = copy.deepcopy(resource_spans)
    for rs in converted:
        for ss in rs.get("scopeSpans", []):
            for span in ss.get("spans", []):
                for fld in _ID_FIELDS:
                    if span.get(fld):
                        span[fld] = base64.b64encode(bytes.fromhex(span[fld])).decode()
    return converted


def ingest_spans_json(
    otlp_json: dict[str, Any],
    endpoint: str = JAEGER_HTTP,
    headers: dict[str, str] | None = None,
    label: str = "collector",
) -> None:
    """POST OTLP JSON spans to an OTLP HTTP endpoint (e.g. Jaeger)."""
    count = _count_spans(otlp_json.get("resourceSpans", []))
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    try:
        httpx.post(endpoint, json=otlp_json, headers=hdrs).raise_for_status()
        log.info("Ingested %d server span(s) into %s", count, label)
    except httpx.ConnectError:
        log.exception("Could not connect to %s at %s", label, endpoint)
    except httpx.HTTPStatusError as exc:
        log.exception(
            "%s returned %d: %s", label, exc.response.status_code, exc.response.text[:200]
        )


def ingest_spans_protobuf(
    resource_spans: list[dict[str, Any]],
    endpoint: str,
    headers: dict[str, str],
    label: str = "Galileo",
) -> None:
    """POST OTLP protobuf spans (required by Galileo)."""
    try:
        from google.protobuf.json_format import ParseDict
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
            ExportTraceServiceRequest,
        )
    except ImportError:
        log.warning("Skipping %s protobuf export (missing protobuf deps)", label)
        return
    if not resource_spans:
        return
    b64_spans = _hex_ids_to_base64(resource_spans)
    body = ParseDict({"resourceSpans": b64_spans}, ExportTraceServiceRequest()).SerializeToString()
    try:
        resp = httpx.post(
            endpoint, content=body, headers={"Content-Type": "application/x-protobuf", **headers}
        )
        log.info(
            "Exported %d server span(s) to %s (HTTP %d)",
            _count_spans(resource_spans),
            label,
            resp.status_code,
        )
    except httpx.ConnectError:
        log.exception("Could not connect to %s at %s", label, endpoint)


# ----------------
# Galileo config
# ----------------


def _galileo_config() -> tuple[str, dict[str, str]] | None:
    """Return ``(endpoint, headers)`` for Galileo, or ``None`` if not configured."""
    api_key = os.environ.get("GALILEO_API_KEY")
    if not api_key:
        return None
    return (
        os.environ.get("GALILEO_OTLP_ENDPOINT", "https://api.galileo.ai/otel/v1/traces"),
        {
            "Galileo-API-Key": api_key,
            "project": os.environ.get("GALILEO_PROJECT", "mcp-cross-org-observability"),
            "logstream": os.environ.get("GALILEO_LOG_STREAM", "default"),
        },
    )


# ---------------
# Tracing setup
# ---------------


def setup_tracing() -> TracerProvider:
    """Jaeger (gRPC) + optional Galileo (OTLP HTTP) + LangChain auto-instrumentation."""
    resource = Resource.create({"service.name": "mcp-gmail-agent"})
    provider = TracerProvider(resource=resource)

    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=JAEGER_GRPC, insecure=True))
    )

    gc = _galileo_config()
    if gc:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPHTTPSpanExporter(endpoint=gc[0], headers=gc[1]))
        )
        log.info("Galileo tracing enabled -> %s", gc[0])

    trace.set_tracer_provider(provider)
    LangchainInstrumentor().instrument()
    return provider


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LangChain agent with SEP-0000 span passback")
    p.add_argument("query", nargs="?", default="List my 5 most recent emails")
    p.add_argument("--detailed", action="store_true", help="Request full span tree")
    p.add_argument(
        "--no-passback",
        action="store_true",
        help="Disable span passback (before SEP-0000 -- server is a black box)",
    )
    p.add_argument(
        "--server-url",
        default="http://127.0.0.1:8000/mcp",
        help="MCP server URL (default: http://127.0.0.1:8000/mcp)",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Instrumentor span look-up
# ---------------------------------------------------------------------------


def _find_instrumentor_span(tool_name: str) -> trace.Span | None:
    """Locate the LangChain instrumentor's span for the active tool invocation."""
    try:
        from langchain_core.callbacks import BaseCallbackManager

        mgr = BaseCallbackManager(handlers=[])
        for handler in mgr.inheritable_handlers:
            if isinstance(handler, TraceloopCallbackHandler):
                for run_id in reversed(list(handler.spans)):
                    holder = handler.spans[run_id]
                    span = getattr(holder, "span", None)
                    if span and tool_name in getattr(span, "name", ""):
                        return span
    except Exception:
        log.debug("Could not look up instrumentor span for %s", tool_name, exc_info=True)
    return None


# --------------------------
# Passback span processing
# --------------------------


def _extract_trace_id(resource_spans: list[dict[str, Any]]) -> str | None:
    """Return the first traceId found in resource_spans, or None."""
    for rs in resource_spans:
        for ss in rs.get("scopeSpans", []):
            for sp in ss.get("spans", []):
                tid = sp.get("traceId")
                if tid:
                    return tid
    return None


def _process_passback_spans(meta: dict[str, Any] | None) -> None:
    """Extract server spans from response ``_meta`` and ingest into collectors."""
    if not meta:
        return
    otel_data = meta.get("otel") if isinstance(meta, dict) else getattr(meta, "otel", None)
    if not otel_data:
        return
    traces = otel_data.get("traces", {})
    resource_spans = traces.get("resourceSpans")
    if not resource_spans:
        return

    span_count = _count_spans(resource_spans)
    truncated = traces.get("truncated", False)
    dropped = traces.get("droppedSpanCount", 0)

    _passback_stats["span_count"] += span_count
    _passback_stats["truncated"] = _passback_stats["truncated"] or truncated
    _passback_stats["dropped"] += dropped
    if not _passback_stats.get("trace_id"):
        _passback_stats["trace_id"] = _extract_trace_id(resource_spans) or ""

    print(f"  Server-side spans: {span_count} received and ingested")
    if truncated:
        print(f"  ({dropped} additional spans available with --detailed)")

    ingest_spans_json({"resourceSpans": resource_spans}, endpoint=JAEGER_HTTP, label="Jaeger")

    gc = _galileo_config()
    if gc:
        ingest_spans_protobuf(resource_spans, endpoint=gc[0], headers=gc[1])


# ----------------------------------------------------
# OAuth helpers (Gmail tool authorization via Arcade)
# ----------------------------------------------------


def _extract_auth_url(result: Any) -> str | None:
    """Check if a tool result contains an authorization URL (OAuth required)."""
    for item in result.content:
        text = getattr(item, "text", None)
        if text and "authorization_url" in text:
            try:
                data = json.loads(text)
                return data.get("authorization_url")
            except (json.JSONDecodeError, TypeError):
                pass
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured.get("authorization_url")
    return None


# ---------------------------------------------------------------------------
# Dynamic MCP tool wrappers
# ---------------------------------------------------------------------------


def build_mcp_tools(
    session: ClientSession,
    mcp_tools: list[Any],
    tracer: trace.Tracer,
    propagator: TraceContextTextMapPropagator,
    detailed: bool,
    passback: bool = True,
) -> list[StructuredTool]:
    """Create LangChain tools from MCP tool definitions, with optional span passback."""
    tools: list[StructuredTool] = []

    for mcp_tool in mcp_tools:
        name = mcp_tool.name
        desc = mcp_tool.description or f"MCP tool: {name}"
        schema = mcp_tool.inputSchema
        props = schema.get("properties", {})
        required = set(schema.get("required", []))

        def _make_fn(t_name: str) -> Any:
            async def _call(**kwargs: str) -> str:
                parent_ctx = None
                inst_span = _find_instrumentor_span(t_name)
                if inst_span:
                    parent_ctx = set_span_in_context(inst_span)

                with tracer.start_as_current_span(
                    f"mcp.call_tool {t_name}",
                    context=parent_ctx,
                    kind=SpanKind.CLIENT,
                    attributes={
                        "mcp.tool": t_name,
                        "mcp.server": "mcp-gmail-server",
                        "gen_ai.operation.name": "execute_tool",
                        "gen_ai.tool.name": f"mcp.call_tool {t_name}",
                        "gen_ai.tool.call.arguments": json.dumps(kwargs),
                    },
                ) as span:
                    carrier: dict[str, str] = {}
                    propagator.inject(carrier)

                    meta: dict[str, Any] = {
                        "traceparent": carrier.get("traceparent", ""),
                    }
                    if passback:
                        meta["otel"] = {"traces": {"request": True, "detailed": detailed}}

                    result = await session.call_tool(t_name, arguments=kwargs, meta=meta)

                    # Handle Gmail OAuth if needed (one-time consent)
                    auth_url = _extract_auth_url(result)
                    if auth_url:
                        span.set_attribute("mcp.auth.required", True)
                        print(f"\n  Authorization required. Open this URL:\n\n  {auth_url}\n")
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            input,
                            "  Press Enter after authorizing...",
                        )
                        result = await session.call_tool(t_name, arguments=kwargs, meta=meta)

                    text = result.content[0].text if result.content else ""
                    span.set_attribute("gen_ai.tool.call.result", text[:500])

                    if passback:
                        _process_passback_spans(result.meta)
                    else:
                        print("  Server-side spans: NONE (passback not requested)")

                    return text

            return _call

        fields = {}
        for pname, pinfo in props.items():
            pdesc = pinfo.get("description", "")
            if pname in required:
                fields[pname] = (str, Field(description=pdesc))
            else:
                fields[pname] = (str, Field(default="", description=pdesc))

        tools.append(
            StructuredTool(
                name=name,
                description=desc,
                coroutine=_make_fn(name),
                args_schema=create_model(f"{name}Args", **fields),
            )
        )

    return tools


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="  %(message)s")

    args = parse_args()
    provider = setup_tracing()
    tracer = trace.get_tracer("mcp-gmail-agent")
    propagator = TraceContextTextMapPropagator()
    passback = not args.no_passback

    if args.no_passback:
        mode = "Act 1: The Black Box (no passback)"
    elif args.detailed:
        mode = "Act 2: The Revelation (detailed span tree)"
    else:
        mode = "Act 2: The Revelation (span passback)"

    print(f"\n{'=' * 60}")
    print(f"  {mode}")
    print(f"{'=' * 60}\n")

    server_url = args.server_url

    # MCP SDK handles OAuth 2.1 automatically:
    # On 401 → discovers auth server via RFC 9728 → PKCE flow → caches tokens
    oauth_auth = OAuthClientProvider(
        server_url=server_url,
        client_metadata=OAuthClientMetadata(
            client_name="mcp-gmail-agent",
            redirect_uris=["http://127.0.0.1:9905/callback"],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="none",  # noqa: S106 - OAuth 2.1 public client (no secret)
        ),
        storage=FileTokenStorage(),
        redirect_handler=_handle_redirect,
        callback_handler=_handle_callback,
    )
    http_client = httpx.AsyncClient(auth=oauth_auth)
    print(f"  Connecting to MCP server at {server_url} ...")

    async with (
        streamable_http_client(url=server_url, http_client=http_client) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        init = await session.initialize()

        telemetry_cap = getattr(init.capabilities, "serverExecutionTelemetry", None)
        print(f"  Server: {init.serverInfo.name} v{init.serverInfo.version}")
        print(f"  serverExecutionTelemetry: {telemetry_cap is not None}")
        if telemetry_cap:
            print(f"  Capability: {telemetry_cap}")

        discovered = await session.list_tools()
        print(f"  Tools: {[t.name for t in discovered.tools]}\n")

        lc_tools = build_mcp_tools(
            session,
            discovered.tools,
            tracer,
            propagator,
            detailed=args.detailed,
            passback=passback,
        )

        agent = create_agent(ChatOpenAI(model="gpt-4o-mini"), lc_tools)

        print(f"  Query: {args.query}")
        if passback:
            print(f"  Detailed: {args.detailed}")
        print()

        result = await agent.ainvoke({"messages": [("user", args.query)]})

        print(f"\n  Agent: {result['messages'][-1].content}\n")

    provider.force_flush()
    provider.shutdown()

    trace_id = _passback_stats.get("trace_id", "")
    if trace_id:
        print(f"  Jaeger UI: {JAEGER_UI}/trace/{trace_id}")
    else:
        print(f"  Jaeger UI: {JAEGER_UI}  (search for service mcp-gmail-agent)")
    print("  Service:   mcp-gmail-agent")
    if args.no_passback:
        print("  Expected:  only agent-side spans (server is a black box)")
    elif args.detailed:
        print(
            "  Expected:  full span tree -- auth.validate, gmail.list_messages,"
            " gmail.fetch_details (with HTTP child spans), format_response"
        )
    else:
        print(
            "  Expected:  server phases visible -- auth.validate,"
            " gmail.list_messages, gmail.fetch_details, format_response"
        )
    print()


if __name__ == "__main__":
    asyncio.run(main())
