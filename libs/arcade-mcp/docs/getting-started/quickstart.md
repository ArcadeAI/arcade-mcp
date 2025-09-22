# Quick Start

The `arcade_mcp` package provides powerful ways to run MCP servers with your Arcade tools.

## Getting Started

### Install

```bash
uv pip install arcade-mcp
```


```bash
uv run python -m arcade_mcp
```

### Write a tool


```python
from arcade_mcp import tool

@tool
def greet(Annotated[str, "The name to greet"]) -> Annotated[str, "The greeting"]:
    return f"Hello, {name}!"
```

### Run MCP Server

```bash
uv run python -m arcade_mcp
```

You should see the following output:

```text
INFO     | 03:32:05 | Auto-discovering tools from current directory
INFO     | 03:32:05 | Found 1 tool(s) in 00_hello_world.py: greet
INFO:     Started server process
INFO:     Waiting for application startup.
INFO     | 03:32:05 | Starting MCP server with HTTP transport on 127.0.0.1:7777
INFO     | 03:32:05 | Starting MCP server: ArcadeMCP
INFO     | 03:32:05 | HTTP session manager started
INFO     | 03:32:05 | MCP server started and ready for connections
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:7777 (Press CTRL+C to quit)
```

View the docs at http://127.0.0.1:7777/docs.

That's it! You've created an MCP server with a tool.

Check out the [CLI](../api/cli.md) for more options and [Clients](../clients/README.md) for how to use the server with different clients like Claude Desktop, Cursor, and VSCode.


## Building MCP Servers

The simplest way to create an MCP server programmatically is using `MCPApp`, which provides a FastAPI-like interface:

```python
from arcade_mcp import MCPApp
from typing import Annotated

app = MCPApp(
    name="my-tools",
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

## `arcade_mcp` CLI

The `arcade_mcp` CLI is a simple tool for running MCP servers automatically discovering tools, creating a server for you, and running it.

This is primarily used for development, and running mcp servers locally for desktop clients with stdio.

### Auto-Discovery Mode

The simplest way to run is to let arcade_mcp discover tools in your current directory:

```bash
# Auto-discover @tool decorated functions
python -m arcade_mcp

# With stdio transport for Claude Desktop
python -m arcade_mcp stdio
```

### Loading Installed Packages

Load specific arcade packages or discover all installed ones:

```bash
# Load a specific arcade package
python -m arcade_mcp --tool-package github
python -m arcade_mcp -p slack

# Discover all installed arcade packages
python -m arcade_mcp --discover-installed

# Show which packages are being loaded
python -m arcade_mcp --discover-installed --show-packages
```

### Development Mode

For active development with hot reload:

```bash
# Run with hot reload and debug logging
python -m arcade_mcp --reload --debug

# Specify host and port
python -m arcade_mcp --host 0.0.0.0 --port 8080

# Load environment variables
python -m arcade_mcp --env-file .env
```


## Environment Variables

Configure the server using environment variables:

```bash
# Server settings
MCP_SERVER_NAME="My MCP Server"
MCP_SERVER_VERSION="1.0.0"

# Arcade integration
ARCADE_API_KEY="your-api-key"
ARCADE_API_URL="https://api.arcade.dev"
ARCADE_USER_ID="user@example.com"

# Development settings
ARCADE_AUTH_DISABLED=true
MCP_DEBUG=true

# Tool secrets (available to tools via context)
MY_API_KEY="secret-value"
DATABASE_URL="postgresql://..."
```

## Development Tips

### Hot Reload
Use `--reload --debug` for development to automatically restart on code changes:

```bash
python -m arcade_mcp --reload --debug
```

### Logging
- Use `--debug` for verbose logging
- In stdio mode, logs go to stderr
- In HTTP mode, logs go to stdout

### Testing Tools
With HTTP transport and debug mode, access API documentation at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)
