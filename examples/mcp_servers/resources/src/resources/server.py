#!/usr/bin/env python3
"""
MCP Apps example server.

Demonstrates the MCP Apps extension (https://modelcontextprotocol.io/extensions/apps/build)
which lets MCP servers expose interactive web UIs alongside tools.

This server registers:
  - A tool ("get_server_time") with _meta.ui.resourceUri pointing to a ui:// resource
  - A resource at that ui:// URI that serves a self-contained HTML app
  - A second tool ("convert_temperature") also linked to the same UI

When a host that supports MCP Apps calls one of these tools, it fetches the
linked HTML resource and renders it in a sandboxed iframe. The UI can then
call tools back on the server via the @modelcontextprotocol/ext-apps client.
"""

import sys
from datetime import datetime, timezone
from typing import Annotated

from arcade_mcp_server import MCPApp

app = MCPApp(name="resources", version="1.0.0", log_level="DEBUG")

# The ui:// URI that both tools will link to
APP_RESOURCE_URI = "ui://resources/mcp-app.html"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# UI Resource — self-contained HTML served as an MCP resource
# ---------------------------------------------------------------------------

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
