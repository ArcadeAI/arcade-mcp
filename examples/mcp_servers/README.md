# MCP Server Examples

Runnable examples demonstrating `arcade-mcp-server` features. Each directory is a
self-contained Python package built from the same `pyproject.toml` template —
copy one as a starting point for your own server.

## Running an example

```bash
cd examples/mcp_servers/<name>
uv sync
uv run python src/<name>/server.py         # stdio transport (default)
uv run python src/<name>/server.py http    # HTTP+SSE transport
```

If you are iterating on the library itself, uncomment the `[tool.uv.sources]`
block at the bottom of the example's `pyproject.toml` to pick up your local
editable `arcade-mcp-server`.

## Examples by MCP spec version

### MCP 2025-11-25 — the "tasks, richer elicitation, sampling-with-tools" release

These examples exercise primitives introduced between `2025-06-18` and
`2025-11-25`.

| Example | Feature | SEP |
|---|---|---|
| [`task_augmentation/`](task_augmentation/) | Durable long-running tool invocations (`ToolExecution.taskSupport`, `/tasks/*` lifecycle, `io.modelcontextprotocol/related-task` `_meta`) | SEP-1686 |
| [`enum_elicitation/`](enum_elicitation/) | All five enum schema variants for `elicit` — single/multi-select, titled/untitled, legacy | SEP-1330 + SEP-1034 + SEP-1613 |
| [`url_elicitation/`](url_elicitation/) | Out-of-band user verification via `context.ui.elicit(mode="url", ...)` | SEP-1036 |
| [`sampling_with_tools/`](sampling_with_tools/) | Tool calling inside `context.sampling.create_message` (`tools=[...]`, `tool_choice=...`) | SEP-1577 |
| [`server_branding/`](server_branding/) | Server icons + description + `websiteUrl` in `InitializeResult.serverInfo`; tool-name-format guidance | SEP-973 + SEP-986 |
| [`typed_errors/`](typed_errors/) | Typed tool execution errors (`RetryableToolError`, `ContextRequiredToolError`, `UpstreamRateLimitError`) — now returned as tool errors, not JSON-RPC `-32602` | SEP-1303 |
| [`authorization/`](authorization/) | OAuth 2.1 Resource Server Auth with PRM discovery (RFC 9728) and incremental scope consent via `WWW-Authenticate: insufficient_scope` | SEP-985 + SEP-835 |

### Pre-existing primitives

Examples that predate 2025-11-25 but are still the best place to learn the
corresponding feature:

| Example | What it shows |
|---|---|
| [`simple/`](simple/) | The minimum viable `MCPApp`: a couple of `@app.tool`s, a secret, and an OAuth-gated tool |
| [`echo/`](echo/) | Even smaller — one tool, stdio transport |
| [`logging/`](logging/) | `context.log.*` (debug/info/warning/error) over stdio and HTTP |
| [`progress_reporting/`](progress_reporting/) | `context.progress.report(...)` for long-running tools |
| [`sampling/`](sampling/) | Plain `context.sampling.create_message(...)` — model-to-model without tool calling |
| [`user_elicitation/`](user_elicitation/) | Form-mode `context.ui.elicit(...)` + `ElicitResult.action` dispatch |
| [`resources/`](resources/) | `@app.resource`, resource templates, `context.resources.*` |
| [`tool_chaining/`](tool_chaining/) | `context.tools.call_raw(...)` — tools calling other tools |
| [`tool_metadata/`](tool_metadata/) | `@app.tool(metadata=ToolMetadata(...))` — behavior hints and extras |
| [`tools_with_output_schema/`](tools_with_output_schema/) | Declaring `outputSchema` via typed return annotations |
| [`custom_server_with_prebuilt_tools/`](custom_server_with_prebuilt_tools/) | Mixing a custom `MCPApp` with an installed Arcade toolkit |
| [`local_filesystem/`](local_filesystem/) | A toolkit that touches real local state (filesystem) |
| [`telemetry_passback/`](telemetry_passback/) | Emitting OpenTelemetry spans from a tool body |
| [`server_with_evaluations/`](server_with_evaluations/) | Tool catalog shipped alongside an `arcade_evals` suite |

## What's intentionally not demonstrated here

Some items from the 2025-11-25 spec touch transport/client surfaces that don't
change the tool-author story. They're called out here so you know they're
covered (or known gaps) without looking for an example that doesn't exist:

- **OpenID Connect Discovery 1.0 for authorization servers** (PR #797) —
  not yet implemented in this repo.
- **OAuth Client ID Metadata Documents** (SEP-991) — not yet implemented.
- **SSE polling / GET stream resumption** (SEP-1699) — transport-side, no
  tool-author surface.
- **Per-tool / per-resource / per-prompt `icons`** (SEP-973) — the wire fields
  exist on `MCPTool`, `Resource`, `ResourceTemplate`, and `Prompt`, but the
  `@app.tool` / `@app.resource` decorators do not currently accept an `icons=`
  kwarg. `server_branding/` shows the server-level icons instead, and the
  per-primitive kwargs are tracked for a follow-up release.
- **JSON Schema 2020-12 as the default dialect** (SEP-1613) — enforced inside
  `context.ui.elicit` validation; surfaces automatically across every
  elicitation example. Pasting in a schema with `"$schema":
  "…2019-09/schema"` now produces a clean `ValueError`.
- **HTTP 403 for invalid Origin** — transport-level behavior in HTTP mode; no
  new tool API.

## Layout (for every example)

```
examples/mcp_servers/<name>/
├── pyproject.toml         # project + hatchling + arcade_toolkits entry point
├── README.md              # what the example demonstrates, how to run it
└── src/
    └── <name>/
        ├── __init__.py    # empty
        └── server.py      # the MCPApp definition
```
