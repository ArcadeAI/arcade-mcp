<div align="center">
  <img src="https://docs.arcade.dev/images/logo/arcade-logo.png" alt="Arcade" width="400">
</div>

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/ArcadeAI/arcade-mcp/blob/main/LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/ArcadeAI/arcade-mcp/main.yml?branch=main)](https://github.com/ArcadeAI/arcade-mcp/actions?query=branch%3Amain)
[![PyPI](https://img.shields.io/pypi/v/arcade-mcp)](https://pypi.org/project/arcade-mcp/)
[![Python Version](https://img.shields.io/pypi/pyversions/arcade-mcp)](https://pypi.org/project/arcade-mcp/)

</div>

# Arcade MCP

**Open-source Python framework for building MCP servers and tools.**

[Documentation](https://docs.arcade.dev) • [Examples](examples/mcp_servers/) • [Discord](https://discord.com/invite/GUZEMpEZ9p)

## What is arcade-mcp

`arcade-mcp` is the Python framework for building [Model Context Protocol](https://modelcontextprotocol.io) servers and the tools that run inside them. It powers the 7,500+ prebuilt tools across 81 MCP servers at [Arcade.dev](https://arcade.dev), and is open-sourced so you can build your own.

Use it when you need MCP tools that aren't already in the prebuilt catalog: internal APIs, custom OAuth providers, domain-specific integrations.

**Highlights:**

- Decorator API covering the full MCP spec: tools, resources, prompts, sampling, elicitation, progress, logging.
- [Authorized tool calling](#authorized-tool-calling). Declare `requires_auth=GitHub(scopes=["repo"])` and Arcade handles OAuth, token refresh, and per-call scoping. The client and the LLM never see the token.
- Vendor-neutral. Any MCP client, any LLM, any agent framework (LangChain, Mastra, Pydantic AI, CrewAI, Google ADK, OpenAI Agents).
- `arcade evals` for testing tool-call accuracy against real LLMs.
- `arcade deploy` for one-command hosting on Arcade Cloud.

## Authorized tool calling

Tools can declare which OAuth scopes they need, and Arcade handles the rest: prompting the end user to authorize, storing and refreshing tokens, scoping them per call, and injecting them into your tool at runtime. **The client and the LLM never see the token.**

A tool that reads the user's GitHub repos is one decorator away:

```python
from arcade_mcp_server import MCPApp, Context
from arcade_mcp_server.auth import GitHub

app = MCPApp(name="gh", version="1.0.0")

@app.tool(requires_auth=GitHub(scopes=["repo"]))
async def list_my_repos(context: Context) -> list[str]:
    """List the authenticated user's GitHub repositories."""
    token = context.get_auth_token_or_empty()
    ...
```

When the tool is invoked through Arcade Cloud, the user is presented with a URL to complete the OAuth challenge in their browser. On success, the token is injected into `context` for that call. Subsequent calls reuse and refresh the token automatically.

22 helper classes ship with the framework for popular providers:

`Asana`, `Atlassian`, `Attio`, `ClickUp`, `Discord`, `Dropbox`, `Figma`, `GitHub`, `Google`, `Hubspot`, `Linear`, `LinkedIn`, `Microsoft`, `Notion`, `PagerDuty`, `Reddit`, `Slack`, `Spotify`, `Twitch`, `X`, `Zoom`.

For any other OAuth API, use the generic `OAuth2(...)` class and register your OAuth app in the Arcade Dashboard.

## Quick Start

### Install the CLI

```bash
uv tool install arcade-mcp
```

### Scaffold a new server

```bash
arcade new my_server
cd my_server/src/my_server
```

The scaffold creates `pyproject.toml`, `.env.example`, and a `server.py` with example tools.

A minimal tool:

```python
from typing import Annotated
from arcade_mcp_server import MCPApp

app = MCPApp(name="my_server", version="1.0.0")

@app.tool
def greet(name: Annotated[str, "Name to greet"]) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    app.run(transport="stdio")
```

### Run

```bash
uv run server.py             # stdio (default), for Claude Desktop and CLI tools
uv run server.py http        # HTTP+SSE, for Cursor and VS Code; docs at http://127.0.0.1:8000/docs
```

### Configure your MCP client

```bash
arcade configure claude                                 # Claude Desktop, stdio
arcade configure cursor --transport http --port 8080    # Cursor, local HTTP on :8080
arcade configure vscode --entrypoint my_server.py       # VS Code, stdio launching my_server.py
```

For more patterns (MCP resources, sampling, progress reporting, tool chaining, end-to-end agents, eval suites, Resource Server Auth), browse [`examples/mcp_servers/`](examples/mcp_servers/). Run `arcade --help` for the full CLI.

## With Arcade Cloud

`arcade login` followed by `arcade deploy` packages your server, discovers and upserts required secrets, and polls until it's healthy on Arcade Cloud. From there, the Arcade Engine fulfills [authorized tool calling](#authorized-tool-calling) flows for end users, and `arcade server logs/list/status` plus `arcade dashboard` provide observability and management.

Standalone is supported too. Run your server in any MCP client over stdio or HTTP. Supply your own access tokens for tools with `requires_auth=...`, and protect production HTTP endpoints with [Resource Server Auth](examples/mcp_servers/authorization/) (OAuth 2.1 Bearer tokens validated against your IdP).

## Install from Source

Requires Python 3.10+ and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ArcadeAI/arcade-mcp.git
cd arcade-mcp
make install
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development workflow and [`SECURITY.md`](SECURITY.md) for vulnerability reporting.

## Community

- Discord: <https://discord.com/invite/GUZEMpEZ9p>
- X: <https://x.com/TryArcade>
- LinkedIn: <https://www.linkedin.com/company/arcade-mcp>
- Issues: <https://github.com/ArcadeAI/arcade-mcp/issues>
- Documentation: <https://docs.arcade.dev>

## License

MIT. See [`LICENSE`](LICENSE).
