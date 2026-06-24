# Google Sheets MCP App (POC)

A proof-of-concept that shows **`arcade-mcp` supports MCP Apps** — the
[SEP-1865 extension](https://modelcontextprotocol.io/extensions/apps) where a tool is
linked to an interactive HTML UI that the host renders in a sandboxed iframe.

It exposes two tools, each backed by a `ui://` HTML resource:

| Tool | What it renders | Linked UI |
| --- | --- | --- |
| `GoogleSheetsApp_RenderRangePreview(spreadsheet_id, a1_range)` | a spreadsheet **grid** (`<table>`) of the range, **flagged cells highlighted** | `ui://google_sheets_app/grid.html` |
| `GoogleSheetsApp_RenderSheetEmbed(spreadsheet_id, gid)` | the **live sheet in an `<iframe>`** beside the review panel | `ui://google_sheets_app/embed.html` |

> POC scope: the grid uses generated **sample** data (no Google OAuth); the embed defaults to a
> public sample spreadsheet so the iframe actually loads.

## Gap 1 — "where to look first"

The spike (TOO-1337) isn't "render a sheet", it's: after the agent turns a 60-page doc into a
40-tab spreadsheet, **where should the reviewer look first?** Doc→spreadsheet extraction is lossy,
so both tools also return **review flags** — the cells the agent was unsure about:

```jsonc
"flags": [
  {"cell": "E2", "severity": "high",   "reason": "Couldn't confidently parse '$9O,000' — likely an OCR artifact (a letter inside a number)."},
  {"cell": "B3", "severity": "high",   "reason": "'Email' was blank in the source — the agent could not extract a value."},
  {"cell": "D2", "severity": "medium", "reason": "Date '2021-13-05' is invalid/ambiguous in the source — verify."}
],
"where_to_look_first": ["E2 — Couldn't confidently parse …", "B3 — 'Email' was blank …", …]
```

The grid UI highlights those cells; the embed UI lists them beside the live sheet. Each flag
**deep-links into the live sheet** (`…/edit#gid=<gid>&range=<cell>`) so the reviewer jumps straight
to the cell. In the POC the flags come from injected sample anomalies; in production they'd be the
extraction agent's own confidence signal.

## How MCP Apps works here

1. The tool advertises its UI via `_meta`: `@app.tool(meta={"ui": {"resourceUri": "ui://…"}})`.
2. The UI is a normal MCP **resource** served as `text/html;profile=mcp-app`.
3. A real MCP Apps **host** (Claude web/desktop, the `ext-apps` basic-host) fetches the UI
   resource, renders it in a sandboxed iframe, and **pushes the tool result into it**
   (`app.ontoolresult`). The UI can also call tools back via `app.callServerTool`.

`arcade-mcp` the *server* only returns `content` + `structuredContent` from `tools/call`;
the host is what renders the iframe and delivers data to it.

### Two resource flavors per tool

- **Bridge UI** (`ui://google_sheets_app/grid.html`, `…/embed.html`) — the spec-correct MCP App UI
  that `_meta.ui.resourceUri` points at. It does the `ui/initialize` postMessage handshake and
  renders whatever tool result the host pushes in. Needs an Apps host to see it render.
- **Static templated UI** (`ui://google_sheets_app/grid/{spreadsheet_id}/{a1_range}`,
  `…/embed/{spreadsheet_id}/{gid}`) — a fully self-contained HTML document with the data baked in.
  Needs **no** Apps host: any MCP client can `resources/read` it and get renderable HTML. Each tool
  returns this concrete URI as `preview_uri`.

## Run

```sh
cd /path/to/arcade-mcp           # repo root (uv workspace has arcade-mcp-server)

# stdio (for Claude Desktop / CLI hosts)
uv run python examples/mcp_servers/google_sheets_app/server.py stdio

# http (for the ext-apps basic-host, Cursor, etc.) — http://127.0.0.1:8000
uv run python examples/mcp_servers/google_sheets_app/server.py http
```

## Verify over MCP (no UI host needed)

```sh
uv run python examples/mcp_servers/google_sheets_app/mcp_smoke_client.py
```

A self-contained stdio MCP client. It runs `initialize → tools/list → tools/call → resources/read`
and asserts the MCP Apps wiring (tool `_meta.ui.resourceUri`, `text/html;profile=mcp-app` UI,
structured tool output, renderable `<table>`/`<iframe>` HTML). It writes the fetched HTML to
`grid_preview.html` / `embed_preview.html` / `grid_bridge.html` so you can open the grid in a
browser without an Apps host.

## See it render in a real host

- **ext-apps basic-host:** run the server over `http`, then
  `SERVERS='["http://localhost:8000/mcp"]' npm start` from `ext-apps/examples/basic-host`.
- **Claude:** expose the `http` server with `npx cloudflared tunnel --url http://localhost:8000`
  and add the tunnel URL as a custom connector.

## Constraints (so the app stays useful)

- **Read-only / preview** — the app displays, never mutates the sheet.
- **Bounded range** — capped at `MAX_COLS=26` × `MAX_ROWS=50`; larger ranges are truncated (flagged
  in the UI) so the HTML payload stays small inside the MCP message.
- **Self-contained HTML** — inline CSS/JS only; the host iframe is deny-by-default CSP, so no
  external asset fetches.
- **Identifiers, not secrets** — pass `spreadsheet_id` / `a1_range`; never bake tokens into HTML.

## Limitations (discovered while building)

- **Tools can't emit HTML directly.** In `arcade-mcp`, a tool's return value is always coerced to
  `TextContent` + `structuredContent` (`convert_to_mcp_content`); it cannot return an
  `EmbeddedResource`/inline HTML. So the UI **must** be delivered the MCP-Apps way (a `ui://`
  resource + `_meta` link), not inline in the tool result. (This is why the pattern fits.)
- **Rendering needs an Apps host.** A plain MCP client (and the smoke client) can fetch the HTML +
  data over the wire but won't visually render it. Protocol verification ≠ visual verification.
- **Data-into-iframe is host-dependent.** The host pushes the initiating tool result to the UI; the
  server doesn't. The static templated resource exists to give a host-independent render.
- **The live iframe is constrained.** It needs the embeddable `/preview` URL (the `/edit` URL is
  `X-Frame-Options`-blocked) and only renders sheets the **end viewer's** browser session can access
  (not the agent's Arcade token). The embed UI declares `_meta.ui.csp.frameDomains:
  ["https://docs.google.com"]` so a SEP-1865-compliant host permits the frame, but
  third-party-cookie rules can still block it.

## Standards (SEP-1865)

Compliance points, all verified over MCP by `mcp_smoke_client.py`:

- UI resources served as `text/html;profile=mcp-app`.
- Tools linked to their UI only via `_meta.ui.resourceUri` in `tools/list` (no redundant body field).
- The embed UI declares `_meta.ui.csp.frameDomains` so the host's deny-by-default sandbox allows the
  Google iframe.
- The bridge UI does the `ui/initialize` handshake, announces `ui/notifications/initialized`, and
  renders from the host-pushed `ui/notifications/tool-result` (its `params` is the `CallToolResult`).
  The `ui/initialize` **request** params must include `protocolVersion` (a string) alongside
  `appInfo`/`appCapabilities` — the ext-apps reference host validates this and rejects init if it's
  missing (verified empirically against the basic-host).

## Connecting a browser-based host over HTTP (CORS)

arcade-mcp's HTTP transport only emits a CORS **preflight** (`OPTIONS`) handler when the OAuth
resource-server middleware is enabled; a no-auth server answers `OPTIONS` with `405`, which browsers
treat as a failed preflight (non-browser clients don't preflight, so stdio/curl/subagents are
unaffected). To connect a browser MCP-Apps host (e.g. the ext-apps `basic-host`), run the server via
`run_cors.py`, which wraps the FastAPI app in `CORSMiddleware`:

```sh
uv run python examples/mcp_servers/google_sheets_app/run_cors.py 8000
# then: SERVERS='["http://localhost:8000/mcp/"]' npm run start   (in ext-apps/examples/basic-host)
```

Verified end-to-end: the basic-host connects, calls the tools, and renders the grid UI (with the
gap-1 flags) inside its sandbox.

## Recommendation (spike outcome)

**The MCP App format can deliver gap 1 at the right fidelity — recommend proceeding, with the grid
as the primary surface.**

- The format fits: arcade-mcp supports the full MCP Apps pattern (`_meta.ui.resourceUri` + `ui://`
  resource) with no library changes; verified over MCP by `mcp_smoke_client.py` (32/32) and an
  independent subagent (17/17 with fresh inputs).
- **The grid tool is the gap-1 workhorse.** It renders the data, highlights the flagged cells, and
  the deep-links jump the reviewer into the live sheet — all inside the chat. Fidelity is bounded by
  payload size (cap the range), which is acceptable for a review surface.
- **The iframe tool is best as a secondary "open the real thing" affordance.** It's highest-fidelity
  (the actual sheet) but the least controllable: embedding depends on the viewer's Google session and
  host CSP, and we can't draw our own flag overlays on top of Google's iframe — hence the side panel
  of deep-links rather than in-iframe highlights.
- **What production needs that this POC stubs:** a real per-cell confidence signal from the
  extraction agent (here it's injected sample anomalies), and live values via the Google Sheets
  toolkit instead of generated data. Gap 2 (precise in-chat edits) stays out of scope.
