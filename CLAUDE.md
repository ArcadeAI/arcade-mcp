# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Arcade MCP is a Python platform for building tool servers that speak **two protocols from the same process**:

1. **MCP (Model Context Protocol)** — the open standard for AI tool integration (JSON-RPC 2.0 over stdio or HTTP+SSE). Used by Claude Desktop, Cursor, VS Code, etc.
2. **Arcade Worker** — Arcade's internal REST+JWT protocol for managed tool execution by the Arcade Engine (`/worker/*` endpoints).

Both protocols share the same tool catalog. A single `MCPApp` definition serves both.

Monorepo with 5 interdependent libraries and a CLI. Python 3.10+. Build system: Hatchling. Package manager: **uv** (always use `uv run`, never bare `pip` or `python`).

## Commands

| Task | Command |
|------|---------|
| Install all packages | `make install` (runs `uv sync --extra all --extra dev` + pre-commit install) |
| Run all lib tests | `make test` |
| Run a single test | `uv run pytest libs/tests/core/test_toolkit.py::TestClass::test_method` |
| Lint + type check | `make check` (pre-commit + mypy per-lib) |
| Build all wheels | `make build` |

## Library Dependency Graph

```
arcade-core          (base: config, errors, catalog, schema, auth definitions, telemetry)
├── arcade-tdk       (@tool decorator, error adapter chain, auth providers)
├── arcade-serve     (Arcade Worker protocol: /worker/* REST endpoints, JWT auth, OpenTelemetry)
│   └── arcade-mcp-server  (MCPApp, MCPServer, Context, transports, resource server auth)
│       └── arcade-mcp CLI (typer-based: new, login, configure, deploy, server, secret, evals)
└── arcade-evals     (evaluation framework, critics, test suites)
```

Each lib under `libs/arcade-*/` has its own `pyproject.toml` and version, except arcade-cli and arcade-evals which use the root `pyproject.toml`. The root `pyproject.toml` defines the uv workspace members and the `arcade` CLI entry point.

## Versioning Rules

- Use semver. Bump the version in `pyproject.toml` when modifying a library's code — but first check `git diff main` to see if the version has already been bumped in the current branch. Only bump once per branch/PR.
- ALWAYS bump the minimum required dependency version when making breaking changes between libraries.

## Architecture

### MCPApp — The Main Entry Point

`MCPApp` (`libs/arcade-mcp-server/arcade_mcp_server/mcp_app.py`) provides a FastAPI-like decorator API. At build time, `@app.tool` registers functions into a `ToolCatalog`; `@app.resource` and `app.add_prompt` register resources/prompts. At runtime, `app.run()` creates an `MCPServer` and starts the chosen transport.

```python
from arcade_mcp_server import MCPApp, Context, tool

app = MCPApp(name="my_server", version="1.0.0")

@app.tool
async def greet(context: Context, name: Annotated[str, "Name to greet"]) -> str:
    """Greet a person."""
    await context.log.info(f"Greeting {name}")
    return f"Hello, {name}!"

if __name__ == "__main__":
    app.run(transport="stdio")  # or "http" with host/port
```

### Transport Modes

- **stdio**: JSON-RPC over stdin/stdout. Used by Claude Desktop and CLI. Supports auth/secrets natively. **Must never have stray stdout/stderr output** — this corrupts the protocol.
- **http**: FastAPI endpoints with SSE. Used by Cursor, VS Code. Requires `ResourceServerAuth` (OAuth 2.1 token validation) for tools that need auth or secrets.

### Dual-Protocol HTTP Mode (MCP + Arcade Worker)

In HTTP mode, the server speaks **two independent protocols** from the same FastAPI app. This is the key integration point between the MCP ecosystem and the Arcade Engine.

**MCP endpoints** (`/mcp/*`) — always enabled in HTTP mode:
- Standard MCP JSON-RPC 2.0 over HTTP + SSE (tools/list, tools/call, resources/read, etc.)
- Mounted as an ASGI sub-application via `_MCPASGIProxy` in `worker.py`
- Optionally protected by `ResourceServerMiddleware` (OAuth 2.1 Bearer tokens)

**Arcade Worker endpoints** (`/worker/*`) — enabled when `ARCADE_WORKER_SECRET` is set:
- `GET /worker/health` — health check (no auth)
- `GET /worker/tools` — returns `ToolDefinition` list
- `POST /worker/tools/invoke` — executes a tool via `ToolCallRequest`/`ToolCallResponse`
- Protected by HS256 JWT (signed with the worker secret, `audience="worker"`, `ver="1"`)
- This is the Arcade Engine's internal protocol for managed tool execution

The decision point is in `create_arcade_mcp()` (`libs/arcade-mcp-server/arcade_mcp_server/worker.py`): if `ARCADE_WORKER_SECRET` (read via `MCPSettings.arcade.server_secret`) is set, a `FastAPIWorker` (from `libs/arcade-serve/`) is created and its routes are registered. Both protocols share the same `ToolCatalog`.

**Key classes by protocol:**

| Layer | MCP side | Worker side |
|-------|----------|-------------|
| Protocol | JSON-RPC 2.0 | REST + JWT |
| Server | `MCPServer` (`arcade_mcp_server/server.py`) | `FastAPIWorker` (`arcade_serve/fastapi/worker.py`) |
| Base | `HTTPSessionManager` | `BaseWorker` (`arcade_serve/core/base.py`) |
| Route handlers | MCP spec methods (initialize, tools/call, etc.) | `CatalogComponent`, `CallToolComponent`, `HealthCheckComponent` (`arcade_serve/core/components.py`) |
| Auth | `ResourceServerMiddleware` (OAuth 2.1) | HS256 JWT via worker secret |

Any change to tool registration, catalog structure, or the `create_arcade_mcp()` factory affects both protocols. Changes to `arcade-serve` affect only the worker side; changes to `MCPServer`/transports affect only the MCP side.

### Tool Discovery

`discover_tools()` (`libs/arcade-core/arcade_core/discovery.py`) has three modes:

1. **Specific package**: `arcade mcp --tool-package github` — loads the `arcade-github` (or `arcade_github`) installed package as a `Toolkit`
2. **All installed**: `arcade mcp --discover-installed` — finds all installed `arcade-*` packages via `Toolkit.find_all_arcade_toolkits()`
3. **Local file discovery** (default): scans cwd for `*.py`, `tools/*.py`, `arcade_tools/*.py`, `tools/**/*.py`. Uses a fast AST pass (`get_tools_from_file`) to find `@tool`-decorated functions without full import, then dynamically loads only files with tools.

Discovery patterns and filters are defined in `DISCOVERY_PATTERNS` and `FILTER_PATTERNS` constants. Test files (`test_*.py`, `_test.py`) are automatically excluded.

### The `@tool` Decorator

Defined in `libs/arcade-tdk/arcade_tdk/tool.py`. Wraps functions with an error adapter chain and sets dunder attributes (`__tool_name__`, `__tool_requires_auth__`, etc.):

```python
@tool(requires_auth=Google(scopes=["gmail.readonly"]), requires_secrets=["API_KEY"])
async def my_tool(context: Context, query: Annotated[str, "Search query"]) -> str:
    token = context.get_auth_token_or_empty()
    secret = context.get_secret("API_KEY")
    ...
```

The error adapter chain is: [user adapters] → [auth-provider adapter] → [GraphQL adapter] → [HTTP adapter fallback]. Each adapter translates service-specific exceptions into `ToolRuntimeError` subclasses.

### Context System

`Context` (`libs/arcade-mcp-server/arcade_mcp_server/context.py`) extends `ToolContext` and provides namespaced runtime capabilities to tools:

| Namespace | Purpose |
|-----------|---------|
| `context.log` | Logging (`.info()`, `.error()`, etc.) |
| `context.progress` | Progress reporting for long-running ops |
| `context.resources` | Read MCP resources |
| `context.tools` | Call other tools (`await context.tools.call_raw(name, args)`) |
| `context.prompts` | Access MCP prompts |
| `context.sampling` | Create model messages via the client |
| `context.ui` | User elicitation (`await context.ui.elicit(...)`) |
| `context.notifications` | Send notifications to the client |

Plus inherited data: `context.user_id`, `context.secrets`, `context.authorization`, `context.metadata`.

Context uses a `ContextVar` (`_current_model_context`) for per-request isolation across async tasks. Instances are auto-created by the server — tools receive them as a parameter.

### Settings and Configuration

`MCPSettings` (`libs/arcade-mcp-server/arcade_mcp_server/settings.py`) is a layered Pydantic settings system. Each sub-settings class reads from env vars with a specific prefix:

| Sub-settings | Env prefix | Key fields |
|--------------|-----------|------------|
| `ServerSettings` | `MCP_SERVER_` | `name`, `version`, `title`, `instructions` |
| `ArcadeSettings` | `ARCADE_` | `api_key`, `api_url`, `server_secret` (alias: `ARCADE_WORKER_SECRET`), `environment`, `auth_disabled` |
| `TransportSettings` | `MCP_TRANSPORT_` | `session_timeout_seconds`, `max_sessions`, `cleanup_interval_seconds` |
| `MiddlewareSettings` | `MCP_MIDDLEWARE_` | `enable_logging`, `log_level`, `enable_error_handling`, `mask_error_details` |
| `NotificationSettings` | `MCP_NOTIFICATION_` | `rate_limit_per_minute`, `default_debounce_ms` |
| `ResourceServerSettings` | `MCP_RESOURCE_SERVER_` | `canonical_url`, `authorization_servers` (JSON array) |
| `ToolEnvironmentSettings` | *(see secrets)* | `tool_environment` |

**`.env` file discovery**: `find_env_file()` traverses upward from cwd, bounded by the nearest `pyproject.toml` (prevents loading unrelated `.env` from `~/`). Existing env vars take precedence (loaded with `override=False`).

A global `settings = MCPSettings.from_env()` singleton is created at import time.

### Tool Secrets

`ToolEnvironmentSettings` auto-collects **every environment variable** that does NOT start with `MCP_` or `_` into `tool_environment`. These become available to tools via `context.get_secret("KEY")`.

This means:
- Set secrets as env vars or in `.env` — they're automatically available
- `MCP_*` prefixed vars are settings, not secrets
- `ARCADE_*` prefixed vars are available as secrets (they don't start with `MCP_` or `_`)
- `requires_secrets=["API_KEY"]` in `@tool` declares which secrets a tool needs

### Auth Providers

Pre-built OAuth2 providers in `arcade_tdk.auth` (re-exported from `arcade_core.auth`):

Asana, Atlassian, Attio, ClickUp, Discord, Dropbox, Figma, GitHub, Google, Hubspot, Linear, LinkedIn, Microsoft, Notion, OAuth2 (generic), PagerDuty, Reddit, Slack, Spotify, Twitch, X, Zoom

Usage: `@tool(requires_auth=GitHub(scopes=["repo"]))`. For unlisted services, use `OAuth2(...)` directly with custom provider ID and scopes. Each provider includes an error adapter that maps provider-specific HTTP errors to `ToolRuntimeError` subclasses.

### Error Hierarchy

All errors in `arcade_core/errors.py`. Tool developers should use these subclasses of `ToolExecutionError`:

| Error class | When to use | `can_retry` | `ErrorKind` |
|-------------|-------------|-------------|-------------|
| `RetryableToolError` | Transient failure, LLM can retry with same/different args. Accepts `additional_prompt_content` and `retry_after_ms`. | `True` | `TOOL_RUNTIME_RETRY` |
| `ContextRequiredToolError` | Needs human input before retry (e.g., ambiguous argument). Requires `additional_prompt_content`. | `False` | `TOOL_RUNTIME_CONTEXT_REQUIRED` |
| `FatalToolError` | Unrecoverable failure (500). | `False` | `TOOL_RUNTIME_FATAL` |
| `UpstreamError` | External API failure. Auto-maps HTTP status codes to error kinds and retryability (5xx/429 retryable). Requires `status_code`. | varies | `UPSTREAM_RUNTIME_*` |
| `UpstreamRateLimitError` | Rate limit (429). Requires `retry_after_ms`. | `True` | `UPSTREAM_RUNTIME_RATE_LIMIT` |

The error adapter chain (in `@tool`) catches exceptions thrown by tool bodies and upstream APIs, converting them to these types. Unhandled exceptions become `FatalToolError`. The `to_payload()` method serializes errors for the wire.

### Resource Server Auth (HTTP transport only)

For HTTP transport with auth/secrets, configure OAuth 2.1 validation:

```python
from arcade_mcp_server.resource_server import ResourceServerAuth, AuthorizationServerEntry

auth = ResourceServerAuth(
    canonical_url="https://mcp.example.com/mcp",
    authorization_servers=[AuthorizationServerEntry(
        authorization_server_url="https://auth.example.com",
        issuer="https://auth.example.com",
        jwks_uri="https://auth.example.com/.well-known/jwks.json",
        algorithm="RS256",
        expected_audiences=["client-id"],
    )]
)
app = MCPApp(name="protected", auth=auth)
```

Validates Bearer tokens on every HTTP request. Supports multiple authorization servers. Can also be configured via `MCP_RESOURCE_SERVER_*` env vars.

### Middleware

`MCPServer` runs a middleware chain (`libs/arcade-mcp-server/arcade_mcp_server/middleware/`). Built-in: `ErrorHandlingMiddleware`, `LoggingMiddleware`. Custom middleware implements `Middleware` with `async def __call__(self, request, call_next)`.

## CLI Commands

The `arcade` CLI (`libs/arcade-cli/arcade_cli/main.py`) is typer-based. Key commands:

| Command | Purpose |
|---------|---------|
| `arcade mcp stdio` | Run server with stdio transport (for Claude Desktop, MCP clients) |
| `arcade mcp http` | Run server with HTTP+SSE transport (for Cursor, VS Code) |
| `arcade mcp --tool-package github` | Load a specific installed toolkit |
| `arcade mcp --discover-installed` | Load all installed `arcade-*` toolkits |
| `arcade new <name>` | Scaffold a new server (minimal template by default, `--full` for toolkit scaffold) |
| `arcade deploy` | Deploy server to Arcade Cloud (packages + pushes + polls status) |
| `arcade configure <client>` | Write MCP client config (claude, cursor, vscode) |
| `arcade login` / `logout` / `whoami` | Arcade authentication (OAuth) |
| `arcade secret set/unset/list` | Manage tool secrets in Arcade Cloud |
| `arcade server logs/list/status` | Manage deployed servers |
| `arcade show` | Display installed tools/servers |
| `arcade evals` | Run tool-calling evaluations (requires `[evals]` extra) |
| `arcade update` | Check for and install CLI updates |

`arcade mcp` is a passthrough — it spawns `python -m arcade_mcp_server` as a subprocess with the provided arguments.

## Key Environment Variables

| Env var | Purpose |
|---------|---------|
| `ARCADE_WORKER_SECRET` | Enables `/worker/*` endpoints for Arcade Engine integration |
| `ARCADE_DISABLED_TOOLS` | Comma-separated `ToolkitName::ToolName` pairs to exclude from catalog |
| `ARCADE_DISABLED_TOOLKITS` | Comma-separated toolkit names to exclude from catalog |
| `ARCADE_API_KEY` | API key for Arcade Cloud (deploy, evals) |
| `ARCADE_API_BASE_URL` | Arcade API endpoint (default: `https://api.arcade.dev`) |
| `ARCADE_ENVIRONMENT` | Environment label (`dev`, `prod`) — used in telemetry |
| `ARCADE_AUTH_DISABLED` | Disable worker JWT auth (not for production) |
| `ARCADE_USAGE_TRACKING=0` | Opt out of CLI usage tracking |
| `ARCADE_DISABLE_AUTOUPDATE=1` | Disable CLI auto-update checks |
| Any non-`MCP_`/`_` prefixed var | Automatically available as a tool secret via `context.get_secret()` |

### Debug-only flags: expose error internals in tool error responses (toolkit authors)

When set, these flags append `developer_message` and/or the tool stacktrace to the `message` field of the MCP tool error response — useful while debugging a toolkit, because most MCP clients render only `message` and drop `developer_message`. Use ONLY for local debugging. Both require the exact value `yes-i-accept-leaking-internals-to-the-agent` (nothing else is accepted — `true`, `1`, etc. are rejected and log a warning). Each logs a loud WARNING on first activation. Implemented in `libs/arcade-mcp-server/arcade_mcp_server/_debug_exposure.py`.

| Env var | Effect when set to the magic ack value |
|---------|-----------------------------------------|
| `ARCADE_DEBUG_EXPOSE_DEVELOPER_MESSAGE_IN_TOOL_ERROR_RESPONSES` | Appends `developer_message` to the error response `message` field |
| `ARCADE_DEBUG_EXPOSE_STACKTRACE_IN_TOOL_ERROR_RESPONSES` | Appends the tool stacktrace to the error response `message` field |

**Never enable in production.** The `message` field is returned verbatim to whoever called the tool — LLMs, transcripts, end-user UIs, and anything else downstream.

## Project Layout

- `libs/arcade-*/` — Core libraries, each with own `pyproject.toml` (except cli/evals → root)
- `libs/tests/` — All tests, grouped by component: `core/`, `arcade_mcp_server/`, `tool/`, `cli/`, `sdk/`, `worker/`, `arcade_evals/`, `mcp/`
- `examples/mcp_servers/` — Example servers (simple, resources, tool_chaining, sampling, authorization, user_elicitation, etc.)
- `tests/` — Top-level integration/install tests (separate from lib tests)

## Testing

Tests live in `libs/tests/` and are configured in root `pyproject.toml` (`testpaths = ["libs/tests"]`).

Key global fixtures (`libs/tests/conftest.py`):
- `isolate_environment` (autouse) — snapshots/restores env vars per test, disables PostHog tracking
- Evals tests auto-skip if `anthropic`/`openai` not installed (use `@pytest.mark.evals` marker)

MCP server test fixtures (`libs/tests/arcade_mcp_server/conftest.py`):
- `event_loop`, `sample_tool_def`, `mock_mcp_server`, `sample_context`

## Development Rules

- **All changes must have tests and follow TDD.** Every new feature, bug fix, or behavioral change needs a corresponding test in `libs/tests/`.
- **Always use uv.** Never use `pip`, `pip install`, `python`, or `python -m` directly. Use `uv run`, `uv sync`, `uv build`, etc.
- **Never pollute stdout/stderr in MCP stdio paths.** Code reachable by `arcade-mcp-server` or the `arcade mcp` CLI command must never print, log to stdout, or spawn processes that write to stdout/stderr. The MCP stdio transport requires a clean JSON-only channel — any stray output corrupts the protocol. When adding CLI-wide hooks or notifications, always gate them to exclude MCP transport paths.

## Code Quality

- **ruff** for linting/formatting (line-length 100, target py310)
- **mypy** with strict settings (`disallow_untyped_defs`, `disallow_any_unimported`)
- **pre-commit** hooks run automatically (ruff, file checks)
- CI tests on Python 3.10–3.14 across Ubuntu/Windows/macOS
