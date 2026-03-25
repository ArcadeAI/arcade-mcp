#!/usr/bin/env python3
"""
Resources Example MCP Server

Comprehensive showcase of MCP resource features in arcade-mcp-server:

 1. @app.resource(uri) decorator        — register a resource with a handler
 2. app.add_resource(uri, handler=...)   — imperative registration
 3. app.add_text_resource(uri, text=...) — static text convenience
 4. app.add_file_resource(uri, path=...) — file-backed resource
 5. URI templates with {param}           — parameterized resources
 6. Wildcard templates {param*}          — greedy path matching
 7. Annotations(priority=...)            — resource annotations
 8. meta={...}                           — custom metadata
 9. Async handlers + return types        — bytes, dict, str
10. @app.tool(ui_resource_uri=...)       — MCP Apps (tool-to-UI linking)
"""

import asyncio
import json
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from arcade_mcp_server import Annotations, MCPApp

app = MCPApp(name="resources", version="1.0.0", log_level="DEBUG")


# ---------------------------------------------------------------------------
# In-memory data for the "Company Knowledge Base" demo
# ---------------------------------------------------------------------------

_KB_ARTICLES = {
    "getting-started": {
        "title": "Getting Started",
        "category": "onboarding",
        "author": "docs-team",
        "body": "Welcome to the company knowledge base! Start here to learn the basics.",
    },
    "api-guidelines": {
        "title": "API Design Guidelines",
        "category": "engineering",
        "author": "platform-team",
        "body": "All APIs must follow REST conventions and use JSON payloads.",
    },
    "security-policy": {
        "title": "Security Policy",
        "category": "compliance",
        "author": "security-team",
        "body": "All employees must use MFA and rotate credentials every 90 days.",
    },
}

_KB_CATEGORIES = {
    "onboarding": ["getting-started"],
    "engineering": ["api-guidelines"],
    "compliance": ["security-policy"],
}


# ===========================================================================
# 1. @app.resource decorator
# ===========================================================================
# The simplest way to register a resource with a handler function.
# The handler receives the URI as its first argument and returns content.


@app.resource(
    "kb://articles/index",
    name="Article Index",
    description="List of all knowledge base articles",
    mime_type="application/json",
)
def article_index(uri: str) -> str:
    """Return a JSON index of all articles."""
    index = [
        {"slug": slug, "title": a["title"], "category": a["category"]}
        for slug, a in _KB_ARTICLES.items()
    ]
    return json.dumps(index, indent=2)


# ===========================================================================
# 2. app.add_resource — imperative registration
# ===========================================================================
# Use this when you want to register a resource without a decorator,
# for example when the handler is defined elsewhere or generated dynamically.


def _serve_category_list(uri: str) -> str:
    """Return the list of categories as JSON."""
    return json.dumps(list(_KB_CATEGORIES.keys()))


app.add_resource(
    "kb://categories",
    name="Categories",
    description="List of all article categories",
    mime_type="application/json",
    handler=_serve_category_list,
)


# ===========================================================================
# 3. app.add_text_resource — static text convenience
# ===========================================================================
# One-liner for resources whose content is known at registration time.
# No handler function needed — the text is served directly.

app.add_text_resource(
    "kb://readme",
    text="Welcome to the Company Knowledge Base.\n\nBrowse articles by category or search by slug.",
    name="README",
    description="Knowledge base welcome text",
)


# ===========================================================================
# 4. app.add_file_resource — file-backed resource
# ===========================================================================
# Serves a file from disk. Text files are returned as TextResourceContents;
# binary files (detected via UnicodeDecodeError) as BlobResourceContents.

app.add_file_resource(
    "kb://config/pyproject",
    path=Path(__file__).resolve().parents[2] / "pyproject.toml",
    name="Project Config",
    description="The pyproject.toml for this example server",
    mime_type="text/plain",
)


# ===========================================================================
# 5. URI templates with {param}
# ===========================================================================
# When a URI contains {braces}, it is automatically registered as a
# ResourceTemplate. The handler receives extracted parameters as kwargs.


@app.resource(
    "kb://articles/{slug}",
    name="Article by Slug",
    description="Retrieve a specific article by its slug",
    mime_type="application/json",
)
def article_by_slug(uri: str, slug: str) -> str:
    """Return a single article as JSON. 'slug' is extracted from the URI."""
    article = _KB_ARTICLES.get(slug)
    if article is None:
        return json.dumps({"error": f"Article '{slug}' not found"})
    return json.dumps(article, indent=2)


# Multi-parameter template — both {category} and {slug} are extracted.
@app.resource(
    "kb://categories/{category}/articles/{slug}",
    name="Article by Category and Slug",
    description="Retrieve an article scoped to a category",
    mime_type="application/json",
)
def article_in_category(uri: str, category: str, slug: str) -> str:
    """Return an article only if it belongs to the given category."""
    if category not in _KB_CATEGORIES:
        return json.dumps({"error": f"Category '{category}' not found"})
    if slug not in _KB_CATEGORIES[category]:
        return json.dumps({"error": f"Article '{slug}' not in category '{category}'"})
    return json.dumps(_KB_ARTICLES[slug], indent=2)


# ===========================================================================
# 6. Wildcard templates {param*}
# ===========================================================================
# The {param*} syntax matches greedily across '/' separators, useful for
# nested paths like "guides/setup/linux".


@app.resource(
    "kb://docs/{path*}",
    name="Docs Tree",
    description="Retrieve documentation by nested path (e.g. 'guides/setup/linux')",
    mime_type="text/plain",
)
def docs_by_path(uri: str, path: str) -> str:
    """Wildcard match — 'path' captures everything including slashes."""
    return f"You requested documentation at path: {path}\n(In a real server, this would read from a docs tree.)"


# ===========================================================================
# 7. Annotations
# ===========================================================================
# Resource annotations let clients sort, filter, or prioritize resources.
# The Annotations model supports 'audience' and 'priority' fields.


@app.resource(
    "kb://announcements/pinned",
    name="Pinned Announcement",
    description="The current pinned company announcement",
    mime_type="text/plain",
    annotations=Annotations(
        audience=["user"],
        priority=1.0,
    ),
)
def pinned_announcement(uri: str) -> str:
    """A high-priority resource. Clients can use annotations to sort/filter."""
    return "All-hands meeting this Friday at 3 PM."


# ===========================================================================
# 8. Custom metadata (meta)
# ===========================================================================
# Arbitrary metadata attached to a resource, visible to clients in
# resources/list responses under the _meta field.


@app.resource(
    "kb://articles/api-guidelines/metadata",
    name="API Guidelines Metadata",
    description="Article with custom metadata tags",
    mime_type="application/json",
    meta={"tags": ["api", "engineering", "standards"], "version": 2, "reviewed": True},
)
def article_metadata(uri: str) -> str:
    """Resource with custom _meta fields. Clients see these in resources/list."""
    return json.dumps(_KB_ARTICLES["api-guidelines"], indent=2)


# ===========================================================================
# 9. Async handlers + return types
# ===========================================================================
# Handlers can be async. Return types are automatically coerced:
#   - str  → TextResourceContents
#   - bytes → BlobResourceContents (base64-encoded)
#   - dict with "text" key → TextResourceContents
#   - dict with "blob" key → BlobResourceContents


@app.resource(
    "kb://branding/logo",
    name="Company Logo",
    description="A small PNG logo (async handler returning bytes)",
    mime_type="image/png",
)
async def company_logo(uri: str) -> bytes:
    """Async handler returning bytes → auto-converted to BlobResourceContents.

    Generates a 32×32 pixel-art "KB" logo PNG from scratch using only stdlib
    (struct + zlib). No Pillow or other imaging libraries needed.
    """
    size = 32
    # Color palette (R, G, B)
    BG = (30, 41, 59)  # slate-800
    FG = (59, 130, 246)  # blue-500
    HI = (147, 197, 253)  # blue-300

    # 32×32 pixel grid — draw a stylized "KB" monogram
    # fmt: off
    pixels = [[BG] * size for _ in range(size)]

    # "K" shape (columns 4-14)
    for y in range(6, 26):
        pixels[y][5] = pixels[y][6] = FG             # vertical stroke
    for i in range(8):
        pixels[6 + i][7 + i] = pixels[6 + i][8 + i] = HI     # upper diagonal ↘
        pixels[25 - i][7 + i] = pixels[25 - i][8 + i] = FG    # lower diagonal ↗

    # "B" shape (columns 17-27)
    for y in range(6, 26):
        pixels[y][18] = pixels[y][19] = FG            # vertical stroke
    for x in range(20, 26):
        pixels[6][x] = pixels[7][x] = HI              # top bar
        pixels[15][x] = pixels[16][x] = FG            # middle bar
        pixels[24][x] = pixels[25][x] = HI            # bottom bar
    for y in range(8, 15):
        pixels[y][25] = pixels[y][26] = HI            # upper right stroke
    for y in range(17, 24):
        pixels[y][25] = pixels[y][26] = FG            # lower right stroke
    # fmt: on

    # Encode as a minimal PNG (IHDR + IDAT + IEND)
    def _make_png(w: int, h: int, rows: list[list[tuple[int, int, int]]]) -> bytes:
        def chunk(ctype: bytes, data: bytes) -> bytes:
            c = ctype + data
            return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

        ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
        raw = b""
        for row in rows:
            raw += b"\x00"  # filter byte: None
            for r, g, b in row:
                raw += struct.pack("BBB", r, g, b)
        idat = zlib.compress(raw)

        return (
            b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
        )

    return _make_png(size, size, pixels)


@app.resource(
    "kb://status",
    name="Server Status",
    description="Server health status (async handler returning dict)",
    mime_type="application/json",
)
async def server_status(uri: str) -> dict:
    """Async handler returning dict with 'text' key → TextResourceContents."""
    await asyncio.sleep(0)  # simulate async I/O
    status = {
        "healthy": True,
        "article_count": len(_KB_ARTICLES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return {"text": json.dumps(status, indent=2)}


# ===========================================================================
# 10. MCP Apps — tool-to-UI resource linking
# ===========================================================================
# Tools can declare a ui_resource_uri to link them to an interactive HTML
# resource. MCP Apps hosts render the HTML in a sandboxed iframe and the UI
# can call tools back on the server via postMessage JSON-RPC.
#
# See: https://modelcontextprotocol.io/extensions/apps/build

APP_RESOURCE_URI = "ui://resources/mcp-app.html"


@app.tool(ui_resource_uri=APP_RESOURCE_URI)
def get_server_time() -> str:
    """Return the current server time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@app.tool(ui_resource_uri=APP_RESOURCE_URI)
def convert_temperature(
    value: Annotated[float, "The temperature value to convert"],
    from_unit: Annotated[str, "Source unit: 'celsius' or 'fahrenheit'"],
) -> str:
    """Convert a temperature between Celsius and Fahrenheit."""
    from_unit = from_unit.lower().strip()
    if from_unit in ("celsius", "c"):
        converted = value * 9 / 5 + 32
        return f"{value}°C = {converted:.1f}°F"
    elif from_unit in ("fahrenheit", "f"):
        converted = (value - 32) * 5 / 9
        return f"{value}°F = {converted:.1f}°C"
    else:
        return f"Unknown unit '{from_unit}'. Use 'celsius' or 'fahrenheit'."


MCP_APP_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>MCP Apps Demo</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    background: #f8fafc; color: #1e293b;
    padding: 1.5rem; max-width: 480px; margin: 0 auto;
  }
  h1 { font-size: 1.25rem; margin-bottom: 1rem; }
  .card {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 0.5rem;
    padding: 1rem; margin-bottom: 1rem;
  }
  .card h2 { font-size: 1rem; margin-bottom: 0.75rem; color: #475569; }
  button {
    background: #3b82f6; color: #fff; border: none; border-radius: 0.375rem;
    padding: 0.5rem 1rem; cursor: pointer; font-size: 0.875rem;
  }
  button:hover { background: #2563eb; }
  button:disabled { background: #94a3b8; cursor: not-allowed; }
  .result {
    margin-top: 0.75rem; padding: 0.5rem; background: #f1f5f9;
    border-radius: 0.25rem; font-family: monospace; font-size: 0.875rem;
    min-height: 1.5rem;
  }
  label { display: block; font-size: 0.8125rem; color: #64748b; margin-bottom: 0.25rem; }
  input, select {
    width: 100%; padding: 0.375rem 0.5rem; border: 1px solid #cbd5e1;
    border-radius: 0.25rem; font-size: 0.875rem; margin-bottom: 0.5rem;
  }
  .row { display: flex; gap: 0.5rem; }
  .row > * { flex: 1; }
</style>
</head>
<body>
<h1>MCP Apps Demo</h1>

<!-- Server Time card -->
<div class="card">
  <h2>Server Time</h2>
  <button id="time-btn">Get Server Time</button>
  <div class="result" id="time-result">Press the button to fetch the time.</div>
</div>

<!-- Temperature Converter card -->
<div class="card">
  <h2>Temperature Converter</h2>
  <div class="row">
    <div>
      <label for="temp-value">Value</label>
      <input id="temp-value" type="number" value="100" step="any" />
    </div>
    <div>
      <label for="temp-unit">From</label>
      <select id="temp-unit">
        <option value="celsius">Celsius</option>
        <option value="fahrenheit">Fahrenheit</option>
      </select>
    </div>
  </div>
  <button id="convert-btn">Convert</button>
  <div class="result" id="convert-result">Enter a value and click Convert.</div>
</div>

<script type="module">
// Minimal JSON-RPC 2.0 over postMessage client for MCP Apps.
// In production, use: import { App } from "@modelcontextprotocol/ext-apps";
// This shim implements just enough of the protocol for the demo.

const JSONRPC_VERSION = "2.0";
const UI_PROTOCOL_VERSION = "2026-01-26";
let nextId = 1;
const pending = {};

// Listen for JSON-RPC messages from the host
window.addEventListener("message", (e) => {
  const msg = e.data;
  if (!msg || typeof msg !== "object" || msg.jsonrpc !== JSONRPC_VERSION) return;

  // JSON-RPC response (has id + result/error)
  if (msg.id !== undefined && pending[msg.id]) {
    pending[msg.id](msg);
    delete pending[msg.id];
  }

  // JSON-RPC notification (has method, no id)
  if (msg.method === "ui/notifications/tool-input") {
    const text = msg.params?.arguments
      ? JSON.stringify(msg.params.arguments)
      : null;
    if (text) {
      document.getElementById("time-result").textContent = text;
    }
  }
  if (msg.method === "ui/notifications/tool-result") {
    const content = msg.params?.result?.content;
    const text = content?.find((c) => c.type === "text")?.text;
    if (text) {
      document.getElementById("time-result").textContent = text;
    }
  }
});

// Send a JSON-RPC request and return a promise for the response
function rpcRequest(method, params) {
  return new Promise((resolve, reject) => {
    const id = nextId++;
    pending[id] = (msg) => {
      if (msg.error) reject(new Error(msg.error.message || "RPC error"));
      else resolve(msg.result);
    };
    window.parent.postMessage(
      { jsonrpc: JSONRPC_VERSION, id, method, params },
      "*"
    );
  });
}

// Send a JSON-RPC notification (no response expected)
function rpcNotify(method, params) {
  window.parent.postMessage(
    { jsonrpc: JSONRPC_VERSION, method, params },
    "*"
  );
}

// Perform the MCP Apps initialization handshake
async function initialize() {
  try {
    await rpcRequest("ui/initialize", {
      appInfo: { name: "MCP Apps Demo", version: "1.0.0" },
      protocolVersion: UI_PROTOCOL_VERSION,
      capabilities: {},
    });
    // Send initialized notification
    rpcNotify("ui/notifications/initialized", {});
  } catch (err) {
    console.error("MCP Apps init failed:", err);
  }
}

await initialize();

const timeBtn = document.getElementById("time-btn");
const timeResult = document.getElementById("time-result");
const convertBtn = document.getElementById("convert-btn");
const convertResult = document.getElementById("convert-result");

// Call a server tool via the host using standard MCP tools/call
async function callServerTool(name, args) {
  const result = await rpcRequest("tools/call", { name, arguments: args });
  return result;
}

// Get Server Time button
timeBtn.addEventListener("click", async () => {
  timeBtn.disabled = true;
  timeResult.textContent = "Loading...";
  try {
    const result = await callServerTool("Resources_GetServerTime", {});
    const text = result?.content?.find((c) => c.type === "text")?.text;
    timeResult.textContent = text || "[no result]";
  } catch (err) {
    timeResult.textContent = "Error: " + err.message;
  } finally {
    timeBtn.disabled = false;
  }
});

// Convert Temperature button
convertBtn.addEventListener("click", async () => {
  convertBtn.disabled = true;
  convertResult.textContent = "Converting...";
  try {
    const value = parseFloat(document.getElementById("temp-value").value);
    const unit = document.getElementById("temp-unit").value;
    const result = await callServerTool(
      "Resources_ConvertTemperature",
      { value, from_unit: unit }
    );
    const text = result?.content?.find((c) => c.type === "text")?.text;
    convertResult.textContent = text || "[no result]";
  } catch (err) {
    convertResult.textContent = "Error: " + err.message;
  } finally {
    convertBtn.disabled = false;
  }
});
</script>
</body>
</html>
"""


@app.resource(APP_RESOURCE_URI, name="MCP App UI", mime_type="text/html;profile=mcp-app")
def serve_app_ui(uri: str) -> str:
    """Serve the self-contained MCP App HTML."""
    return MCP_APP_HTML


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Get transport from command line argument, default to "stdio"
    # - "stdio" (default): Standard I/O for Claude Desktop, CLI tools, etc.
    # - "http": HTTPS streaming for Cursor, VS Code, etc.
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
