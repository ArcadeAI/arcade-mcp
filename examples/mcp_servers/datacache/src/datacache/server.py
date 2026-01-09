#!/usr/bin/env python3
"""Datacache MCP server example."""

import os
import sys
from typing import Annotated

from arcade_mcp_server import Context, MCPApp

# ---------------------------------------------------------------------------
# How to set organization/project for datacache keying
#
# Datacache keys `organization` and `project` come from the MCP `tools/call` request
# params `_meta`, and are propagated into `ToolContext.metadata` automatically.
#
# Example JSON-RPC call:
# {
#   "jsonrpc": "2.0",
#   "id": 1,
#   "method": "tools/call",
#   "params": {
#     "name": "datacache_upsert_profile",
#     "arguments": { "profile_id": "1", "name": "Alice" },
#     "_meta": { "organization": "acme", "project": "rocket" }
#   }
# }
# ---------------------------------------------------------------------------

# Default the example to local storage so it's easy to run locally.
# (The MCP server requires ARCADE_DATACACHE_STORAGE_BACKEND when datacache is enabled.)
os.environ.setdefault("ARCADE_DATACACHE_STORAGE_BACKEND", "local")
os.environ.setdefault("ARCADE_DATACACHE_REDIS_URL", "redis://localhost:6379/0")

app = MCPApp(name="datacache_duckdb", version="1.0.0", log_level="DEBUG")


@app.tool(datacache={"keys": ["organization", "project", "user_id"], "ttl": 3600})
async def upsert_profile(
    context: Context,
    profile_id: Annotated[str, "Unique profile id"],
    name: Annotated[str, "Display name"],
) -> dict:
    """Upsert a profile row into a DuckDB-backed datacache."""
    profile = {"id": profile_id, "name": name, "kind": "example_profile"}

    response = await context.datacache.set(
        "profiles",
        profile,
        id_col="id",
    )
    return response.model_dump(mode="json")


@app.tool(datacache={"keys": ["organization", "project", "user_id"], "ttl": 3600})
async def search_profiles(
    context: Context,
    term: Annotated[str, "Search term (case-insensitive substring match)"],
) -> list[dict]:
    """Search profiles by name using a LIKE query under the hood."""
    return await context.datacache.search("profiles", "name", term)


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"
    app.run(transport=transport, host="127.0.0.1", port=8000)
