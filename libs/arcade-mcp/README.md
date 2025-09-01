# ``arcade-mcp``

A Pythonic library to run MCP servers locally using Arcade's core runtime. Designed for local-first development with simple, explicit Python entrypoints.

## Install

```bash
uv add arcade-ai --all-extras
```

## Usage

Create a toolkit with templates:

```bash
arcade new my_toolkit
cd my_toolkit
```

Run the server with uv:

```bash
# Default transport (stream)
uv run server.py

# Specific transport
uv run server.py stream
uv run server.py sse
uv run server.py stdio
```

Connect clients:

```bash
# Cursor (local)
arcade connect cursor --from-local

# Cursor (from Arcade cloud)
arcade connect cursor --from-arcade

# Claude (from Arcade cloud)
arcade connect claude --from-arcade
```

Notes:
- MCP endpoints are served at `/mcp` for HTTP transports (stream, sse).
- `.env` at the project root is automatically loaded for local runs.
- Auto-discovery loads the local toolkit in the current directory, or falls back to installed Arcade toolkits.
