# Quick Start

The `arcade_mcp_server` package provides powerful ways to run MCP servers with your Arcade tools. **We recommend using `arcade new`** from the `arcade-mcp` CLI to create your server project with all necessary files and dependencies.

## Recommended: Create with arcade new

### 1. Install the CLI

```bash
uv pip install arcade-mcp
```

The `arcade-mcp` package includes the CLI tools and the `arcade-mcp-server` library.

### 2. Create Your Server

```bash
arcade new my_server
cd my_server
```

This generates a complete project with:

- **server.py** - Main server file with MCPApp and example tools

- **pyproject.toml** - Dependencies and project configuration

- **.env.example** - Example `.env` file containing a secret required by one of the generated tools in `server.py`

The generated `server.py` includes proper structure with command-line argument handling:

```python
#!/usr/bin/env python3
import sys
from typing import Annotated
from arcade_mcp_server import MCPApp

app = MCPApp(name="my_server", version="1.0.0")

@app.tool
def greet(name: Annotated[str, "Name to greet"]) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"
    app.run(transport=transport, host="127.0.0.1", port=8000)
```

### 3. Run Your Server

```bash
# Run with uv (recommended)
uv run server.py

# Run with HTTP transport (default)
uv run server.py http

# Run with stdio transport (for Claude Desktop)
uv run server.py stdio
```

You should see output like:

```text
INFO | Starting server v1.0.0 (my_server)
INFO | Added tool: greet
INFO | Added tool: add_numbers
INFO | Starting MCP server on http://127.0.0.1:8000
```

For HTTP transport, view your server's API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 4. Configure MCP Clients

Connect your server to AI assistants:

```bash
# Configure Claude Desktop
arcade configure claude --from-local

# Configure Cursor IDE
arcade configure cursor --from-local

# Configure VS Code
arcade configure vscode --from-local
```

That's it! Your MCP server is running and connected to your AI assistant.


## Building MCP Servers

The simplest way to create an MCP server programmatically is using `MCPApp`, which provides a FastAPI-like interface:

```python
from arcade_mcp_server import MCPApp
from typing import Annotated

app = MCPApp(
    name="my_serve_",
    version="1.0.0",
    instructions="Custom MCP server with specialized tools"
)

@app.tool
def calculate(
    expression: Annotated[str, "Mathematical expression to evaluate"]
) -> Annotated[float, "The result of the calculation"]:
    """Safely evaluate a mathematical expression."""
    # Safe evaluation logic here
    return eval(expression, {"__builtins__": {}}, {})

@app.tool
def fetch_data(
    url: Annotated[str, "URL to fetch data from"]
) -> Annotated[dict, "The fetched data"]:
    """Fetch data from an API endpoint."""
    import requests
    return requests.get(url).json()

# Run the server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, reload=True)
```



## Secrets

Define your tool secrets in an environment file `.env` in the same directory as your `MCPApp`, or export as environment variables

```bash
# Tool secrets (available to tools via context)
MY_API_KEY="secret-value"
DATABASE_URL="postgresql://..."
```

## Development Tips

### Hot Reload
Use the `reload=True` parameter for development to automatically restart on code changes:

```python
app.run(host="127.0.0.1", port=8000, reload=True)
```

### Logging
- Set `log_level="DEBUG"` in MCPApp for verbose logging
- In stdio mode, logs go to stderr
- In HTTP mode, logs go to stdout

### Docs for your MCP Server
With HTTP transport, access API documentation at:

- http://localhost:8000/docs (Swagger UI)

- http://localhost:8000/redoc (ReDoc)

## Next Steps

- Check out the [Examples](../examples/README.md) for detailed tutorials
- Learn about [Client Integration](../clients/claude.md) with Claude Desktop, Cursor, and VS Code
- Explore the [MCPApp API](../api/mcp_app.md) for advanced server customization
- Read about [Transport Modes](../advanced/transports.md) (stdio vs HTTP)
