# pctx_code_mode

ProjectTracker MCP server — a project-management toolset (projects, sprints, tasks, comments, time entries, sprint metrics) built with `arcade-mcp-server`'s `MCPApp` with automatic Code Mode by including the `pctx_url` kwarg.

The server speaks two transports:
- **stdio** — for Claude Desktop, Cursor, MCP CLIs, and the standard `arcade evals` runner.
- **HTTP+SSE** — for Claude Code and any HTTP MCP client.

## Prerequisites

The server's `MCPApp` is configured with `pctx_url=getenv("PCTX_URL", "http://localhost:8080")`. **For Code Mode behavior (executing tools through the pctx sandbox), pctx must be running.**.

### Install pctx

Follow instructions on (GitHub)[https://github.com/portofcontext/pctx] to install/upgrade to the latest version of `pctx` (`v0.7.1`).

### Start pctx

```bash
pctx start         # listens on 127.0.0.1:8080 by default
```

If you bind pctx to a different host or port, export `PCTX_URL=http://...` before launching the MCP server.

## Install the MCP server

From this directory:

```bash
cd examples/mcp_servers/pctx_code_mode
uv sync
```

This builds the `pctx_code_mode` script into the local `.venv`.

## Run

stdio (default):

```bash
uv run pctx_code_mode
# equivalent to:
uv run pctx_code_mode stdio
```

HTTP+SSE on `127.0.0.1:8000`:

```bash
uv run pctx_code_mode http
```

Override host/port via env:

```bash
ARCADE_SERVER_HOST=0.0.0.0 ARCADE_SERVER_PORT=8001 uv run pctx_code_mode http
```

## Demo

## 1. Add to Claude Code (HTTP transport)

With the server running on HTTP (e.g. `uv run pctx_code_mode http`), register it:

```bash
claude mcp add --transport http project-tracker http://127.0.0.1:8000/mcp
```

Then in Claude Code, run `/mcp` to verify the connection. The ProjectTracker Code Mode tools (`ProjectTracker_ListFunctions`, `ProjectTracker_GetFunctionDetails`, `ProjectTracker_ExecuteTypescript`) should appear under the `project-tracker` server.

To remove later: `claude mcp remove project-tracker`.

## 2. Run some prompts

Example prompt to watch the agent use the code mode functionality calling/chaining multiple tools via code.

```
Spin up a new project called "Q3 Launch" owned by maria@co, then create its first two-week sprint ("Sprint 1", starting Monday) and load it with these tasks: design review (2pt, alex), API contract (5pt, priya), staging deploy script (3pt, jordan), kickoff doc (1pt, maria). Activate the sprint when everything's in.
```
