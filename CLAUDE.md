# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Arcade MCP is a Python tool-calling platform for building MCP (Model Context Protocol) servers. It's a monorepo containing 5 interdependent libraries and a CLI. Python 3.10+. Build system is Hatchling. Package manager is **uv** (always use `uv run`, never bare `pip` or `python`).

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
├── arcade-serve     (FastAPI worker infrastructure, OpenTelemetry)
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

### Two Transport Modes

- **stdio**: JSON-RPC over stdin/stdout. Used by Claude Desktop and CLI. Supports auth/secrets natively. **Must never have stray stdout/stderr output** — this corrupts the protocol.
- **http**: FastAPI endpoints with SSE. Used by Cursor, VS Code. Requires `ResourceServerAuth` (OAuth 2.1 token validation) for tools that need auth or secrets.

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

Validates Bearer tokens on every HTTP request. Supports multiple authorization servers.

### Middleware

`MCPServer` runs a middleware chain (`libs/arcade-mcp-server/arcade_mcp_server/middleware/`). Built-in: `ErrorHandlingMiddleware`, `LoggingMiddleware`. Custom middleware implements `Middleware` with `async def __call__(self, request, call_next)`.

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
