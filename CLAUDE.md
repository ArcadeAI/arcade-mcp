# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Arcade MCP is a Python tool-calling platform for building MCP (Model Context Protocol) servers. It's a monorepo containing 5 interdependent libraries, 30+ prebuilt toolkit integrations, and a CLI.

## Commands

| Task | Command |
|------|---------|
| Install all packages | `make install` (runs `uv sync --extra all --extra dev`) |
| Run all lib tests | `make test` |
| Run a single test | `uv run pytest libs/tests/core/test_toolkit.py::TestClass::test_method` |
| Lint + type check | `make check` (pre-commit + mypy) |
| Build all wheels | `make build` |
| Run toolkit tests | `make test-toolkits` |

Package manager is **uv** — always use `uv run` to execute Python commands, never bare `pip` or `python`. Python 3.10+. Build system is Hatchling.

## Library Dependency Graph

```
arcade-core          (base: config, errors, catalog, telemetry)
├── arcade-tdk       (tool decorators, auth providers, annotations)
├── arcade-serve     (FastAPI worker infrastructure, MCP server)
│   └── arcade-mcp-server  (MCPApp class, FastAPI-like interface)
│       └── arcade-mcp CLI (depends on all above)
└── arcade-evals     (evaluation framework, critics, test suites)
```

## Versioning Rules

- Use semver. ALWAYS bump the version in `pyproject.toml` when modifying a library's code.
- ALWAYS bump the minimum required dependency version when making breaking changes between libraries.

## Key Patterns

### MCP Server (arcade-mcp-server)

```python
from typing import Annotated

from arcade_mcp_server import MCPApp

app = MCPApp(name="my_server", version="1.0.0")

@app.tool
def greet(name: Annotated[str, "The name of the person to greet"]) -> str:
    """Greet a person."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
```

Transports: `stdio` (default) and `http` (tools that require auth or secrets need resource server auth provided by arcade-mcp-server)

## Project Layout

- `libs/arcade-*/` — Core libraries. Most have their own `pyproject.toml`. libs/arcade-cli and arcade-evals use the top-level `pyproject.toml`.
- `libs/tests/` — All library tests, grouped by component (core, cli, arcade_mcp_server, tool, sdk, worker)
- `examples/mcp_servers/` — Example MCP server implementations
- `contrib/` — Community integrations (e.g., crewai)

## Development Rules

- **All changes must have tests and follow TDD.** Every new feature, bug fix, or behavioral change needs a corresponding test in `libs/tests/`.
- **Always use uv.** Never use `pip`, `pip install`, `python`, or `python -m` directly. Use `uv run`, `uv sync`, `uv build`, etc.

## Code Quality

- **ruff** for linting/formatting
- **mypy** with strict settings (`disallow_untyped_defs`, `disallow_any_unimported`)
- **pre-commit** hooks run automatically
- CI tests on Python 3.10, 3.11, 3.12 across Ubuntu/Windows/macOS
