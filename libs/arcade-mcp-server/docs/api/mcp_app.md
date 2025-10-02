### MCPApp

A FastAPI-like interface for building MCP servers with lazy initialization.

MCPApp provides a clean, minimal API for building MCP servers programmatically. It handles tool collection, server configuration, and transport setup with a developer-friendly interface.

#### Basic Usage

```python
from arcade_mcp_server import MCPApp

app = MCPApp(name="my_server", version="1.0.0")

@app.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

app.run(host="127.0.0.1", port=8000)
```

#### Class Reference

::: arcade_mcp_server.mcp_app.MCPApp

#### Examples

```python
# --- server.py ---
# Programmatic server creation with a simple tool and HTTP transport

from arcade_mcp_server import MCPApp

app = MCPApp(name="example_server", version="1.0.0")

@app.tool
def echo(text: str) -> str:
    return f"Echo: {text}"

if __name__ == "__main__":
    # Start an HTTP server (good for local development/testing)
    app.run(host="0.0.0.0", port=8000, reload=False, debug=True)
```

```bash
# then run the server
python server.py
```
