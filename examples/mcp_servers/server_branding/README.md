# server_branding

Demonstrates the **server-level branding fields** added to
`Implementation` (the `serverInfo` in `InitializeResult`) in MCP 2025-11-25:

- `icons: list[Icon]` — SEP-973.
- `description: str` — free-form description of the server.
- `websiteUrl: str` — link to docs, landing page, or wherever.

Also touches on **SEP-986 tool name format** — the SHOULD-level constraint
on tool names — because it's a trivial addition alongside the branding
story.

## What you'll see on the wire

Start the server and hit `initialize`:

```bash
uv sync
uv run python src/server_branding/server.py        # HTTP on :8000
```

```bash
curl -s -X POST http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-11-25",
      "capabilities": {},
      "clientInfo": {"name": "curl", "version": "0"}
    }
  }' | jq .result.serverInfo
```

The response:

```jsonc
{
  "name": "server_branding",
  "title": "Server Branding Demo",
  "version": "1.0.0",
  "description": "Example MCP server showing off the 2025-11-25 server-level branding fields: ...",
  "websiteUrl": "https://arcade.dev",
  "icons": [
    {
      "src": "data:image/svg+xml;base64,...",
      "mimeType": "image/svg+xml",
      "sizes": ["64x64", "any"],
      "theme": "light"
    },
    { "src": "...", "theme": "dark", ... },
    { "src": "https://docs.arcade.dev/images/arcade-logo-512.png", "sizes": ["512x512"], ... }
  ]
}
```

Older (2025-06-18) sessions see the same response with `icons` /
`description` / `websiteUrl` **stripped** — the server-side version gating
prevents sending fields the client's protocol version doesn't understand.

## Icon field anatomy

```python
Icon(
    src="data:image/svg+xml;base64,...",  # or an https:// URL
    mimeType="image/svg+xml",             # optional hint
    sizes=["64x64", "any"],                # WHATWG icon sizes syntax
    theme="light",                         # "light" | "dark" | absent (neutral)
)
```

Register multiple icons for different themes / DPIs / aspect ratios; the
client picks the best fit. Data URIs work when you want a fully
self-contained example; for real deployments, host the assets somewhere
cacheable.

## Tool name format (SEP-986)

MCP 2025-11-25 SHOULDs tool names match `[A-Za-z0-9_.-]{1,128}`. Arcade's
convention — PascalCase via `snake_to_pascal_case` — is a strict subset.

Tool register-time behaviour (Arcade's `ToolCatalog.add_tool` runs every name
through `snake_to_pascal_case` regardless of source, so the wire name is
always PascalCase-ish):

| Source | Registered name | Valid under SEP-986 |
|---|---|---|
| `def echo(...)` | `Echo` | ✅ |
| `def generate_report(...)` | `GenerateReport` | ✅ |
| `@app.tool(name="data.fetch-utility")` | `Data.fetch-utility` (first segment PascalCased) | ✅ (dots and dashes are allowed) |
| `@app.tool(name="my tool")` | `My tool` — space remains | ❌ — `is_valid_tool_name` returns False |
| `@app.tool(name="🚀launch")` | `🚀launch` | ❌ |

`arcade_mcp_server.validation.is_valid_tool_name` lets you check a name
programmatically:

```python
from arcade_mcp_server.validation import is_valid_tool_name

assert is_valid_tool_name("GenerateReport")
assert is_valid_tool_name("data.fetch-utility")
assert not is_valid_tool_name("my tool")
```

## What's NOT demonstrated here

Per-tool, per-resource, and per-prompt icons (also part of SEP-973) *are*
defined on the wire types (`MCPTool.icons`, `Resource.icons`, etc.) but the
`@app.tool` / `@app.resource` / `app.add_prompt` decorators do not
currently accept an `icons=` kwarg. That's tracked for a follow-up PR; for
now, use server-level icons (above) and / or set `__tool_icons__` manually
on a decorated function if you need them in the short term.

## Related SEPs

- **SEP-973** — Server/tool/resource/prompt icons.
- **SEP-986** — Tool name format guidance.
- **MCP 2025-11-25 Implementation fields** — `description`, `websiteUrl`
  added to `Implementation`.
