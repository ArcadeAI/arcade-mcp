# SEP-0000 Telemetry Passback — Reference Implementation

End-to-end reference implementation of **SEP-0000 `serverExecutionTelemetry`** — cross-organization distributed tracing via MCP.

## Overview

This example demonstrates how an MCP server can **pass back OpenTelemetry spans** to the calling client, enabling full distributed tracing across organizational boundaries. Without this capability, the server side of an MCP tool call is a black box — you can see *that* it was called, but not *what happened inside*.

The example includes three components:

1. **Server** (`server.py`) — An Arcade MCP server with Gmail tools that uses `TelemetryPassbackMiddleware` to collect and return spans. This shows how a **vendor adopts** the SEP.
2. **Agent** (`agent.py`) — A LangChain ReAct agent that requests span passback, receives server spans, and ingests them into Jaeger/Galileo. This shows how a **consumer uses** the SEP.
3. **Jaeger** (`docker-compose.yml`) — Local trace collector and UI for visualizing the stitched traces.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for Jaeger)
- An [Arcade](https://www.arcade.dev) account ([quickstart](https://docs.arcade.dev/en/get-started/quickstarts/mcp-server-quickstart))
- An OpenAI API key (for the LangChain agent)

## Setup

```bash
cd examples/mcp_servers/telemetry_passback

# Copy env file and add your keys
cp .env.example .env
# Edit .env: set OPENAI_API_KEY, ARCADE_API_KEY, ARCADE_USER_ID

# Install dependencies
uv sync

# Start Jaeger
docker compose up -d
```

## Usage

The server and agent run as **separate processes**. Start the server first, then run the agent in another terminal.

### Start the Server

```bash
# Terminal 1
uv run python src/telemetry_passback/server.py
```

The server listens at `http://127.0.0.1:8000/mcp` with OAuth 2.1 resource server auth via Arcade.

### Run the Agent

In a separate terminal. On first run, the MCP SDK will open your browser for OAuth authorization (one-time).

#### Act 1 — "The Black Box" (no passback)

```bash
uv run python src/telemetry_passback/agent.py --no-passback "List my 3 most recent emails"
```

Open Jaeger at [http://localhost:16686](http://localhost:16686): you see agent LLM reasoning spans + one opaque `mcp.call_tool` CLIENT span. The tool call took ~3 seconds but there's no way to tell why. Is it the LLM? The network? Auth? The Gmail API? Everything inside the server is invisible.

#### Act 2 — "The Revelation" (with passback)

```bash
uv run python src/telemetry_passback/agent.py --detailed "List my 3 most recent emails"
```

Same call, but now the span tree reveals the server's internal structure:

```
mcp-gmail-agent
├── LangChain agent reasoning
├── ChatOpenAI (LLM decides to call tool)
├── mcp.call_tool list_emails (CLIENT)
│   └── tools/call list_emails (SERVER)           ← FROM SPAN PASSBACK
│       ├── auth.validate (50ms)
│       ├── gmail.list_messages (400ms)
│       │   └── GET messages (HTTP)
│       ├── gmail.fetch_details (1.6s)             ← bottleneck!
│       │   ├── GET messages/abc (HTTP, 520ms)
│       │   ├── GET messages/def (HTTP, 510ms)
│       │   └── GET messages/ghi (HTTP, 530ms)
│       └── format_response (5ms)
└── ChatOpenAI (LLM — final answer)
```

Now the consumer can see exactly what's happening: auth is fast, listing is fine, but **detail fetching is sequential** — three HTTP calls in a waterfall. Armed with this information, the consumer can:

- **File an informed bug report** to the server vendor: "your `list_emails` has an N+1 in detail fetching — each email triggers a sequential HTTP call"
- **Adjust their usage**: request fewer emails, use a query filter to reduce N
- **Make an informed vendor choice**: compare span trees across MCP server providers

This is the core value of the SEP — **the consumer doesn't need access to the server's code or deployment to understand its performance characteristics**.

### Granularity Control

The `--detailed` flag demonstrates the SEP's span filtering. Without it, the server returns only top-level phase spans (auth, list, fetch, format). With `--detailed`, the full tree including HTTP child spans is returned. This lets the server vendor control how much internal detail is exposed.

```bash
# Top-level phases only (default)
uv run python src/telemetry_passback/agent.py "List my 3 most recent emails"

# Full span tree including HTTP child spans
uv run python src/telemetry_passback/agent.py --detailed "List my 3 most recent emails"
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `query` | `"List my 5 most recent emails"` | The question to ask the agent |
| `--detailed` | `false` | Request full span tree |
| `--no-passback` | `false` | Disable span passback (Act 1 — server is a black box) |
| `--server-url` | `http://127.0.0.1:8000/mcp` | MCP server URL |

## Expected Results in Jaeger

Open [http://localhost:16686](http://localhost:16686) and search for service **`mcp-gmail-agent`**.

| Mode | What you see |
|------|-------------|
| `--no-passback` | Only agent-side spans: LLM calls + opaque `mcp.call_tool`. Server is a black box. |
| Default | Server phase spans stitched into the same trace: `auth.validate`, `gmail.list_messages`, `gmail.fetch_details`, `format_response`. |
| `--detailed` | Full span tree: phase spans plus HTTP child spans under each phase, revealing the sequential N+1 pattern in `gmail.fetch_details`. |

## Architecture

```
┌─────────────────────────┐     HTTP (streamable)    ┌──────────────────────────┐
│   agent.py              │ ───────────────────────>│   server.py              │
│   (LangChain ReAct)     │   :8000/mcp              │   (Arcade MCP Server)    │
│                         │                          │                          │
│   OAuth 2.1 via MCP SDK │  traceparent in _meta    │   OAuth 2.1 (Arcade)     │
│   OTel → Jaeger/Galileo │ ───────────────────────>│   OTel (internal only)   │
│                         │  spans back in _meta     │   TelemetryPassback MW   │
│                         │ <───────────────────────│                          │
└─────────────────────────┘                         └──────────────────────────┘
         │                                                     │
         └──────────── Stitched trace in Jaeger ───────────────┘
```

### How It Works

**Server side** (`server.py`):
1. Validates Bearer tokens via `ArcadeResourceServerAuth` (OAuth 2.1, RFC 9728 discovery)
2. `TelemetryPassbackMiddleware` intercepts `tools/call` requests
3. Reads `_meta.traceparent` and `_meta.otel.traces.{request, detailed}`
4. Creates a SERVER span under the client's trace (via traceparent propagation)
5. Tool function creates logical-phase spans with `gen_ai.*` semantic conventions
6. httpx auto-instrumentation creates HTTP child spans for Gmail API calls
7. Middleware serializes to OTLP JSON and attaches to `response._meta.otel.traces`

**Client side** (`agent.py`):
1. MCP SDK handles OAuth 2.1 automatically (discovers auth server on 401, PKCE flow, token caching)
2. Connects to the server via streamable HTTP, detects `serverExecutionTelemetry` capability
3. For each tool call, creates a CLIENT span and injects `traceparent` in `_meta`
4. Sends `_meta.otel.traces.request: true` to opt into span passback
5. Receives server spans in response `_meta.otel.traces.resourceSpans`
6. POSTs OTLP JSON to Jaeger for trace stitching
7. Optionally exports to Galileo (protobuf) if `GALILEO_API_KEY` is set

## Configuration

Copy `.env.example` to `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | OpenAI API key for the LangChain agent |
| `ARCADE_API_KEY` | (required) | Arcade API key |
| `ARCADE_USER_ID` | (required) | Your Arcade account email |
| `ARCADE_API_URL` | `https://api.arcade.dev` | Arcade API endpoint |
| `GALILEO_API_KEY` | (optional) | Enables export to Galileo alongside Jaeger |
| `GALILEO_PROJECT` | (optional) | Galileo project name |
| `GALILEO_LOG_STREAM` | `default` | Galileo log stream |
| `GALILEO_OTLP_ENDPOINT` | `https://app.galileo.ai/api/galileo/otel/traces` | Galileo OTLP endpoint |
