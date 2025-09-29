# Quick Start

The `arcade_mcp_server` package provides powerful ways to run MCP servers with your Arcade tools. While you can use the server library directly, **we recommend using the Arcade CLI** for a streamlined development experience.

## Recommended: Quick Start with Arcade CLI

### 1. Install the CLI

```bash
uv pip install arcade-mcp
```

The `arcade-mcp` package includes both the CLI tools and the `arcade-mcp-server` library.

### 2. Create a New Server

Start with a pre-configured server that includes example tools:

```bash
arcade new my_server
cd my_server
```

This creates a starter MCP server with three example tools:
- **Simple tool** - A basic greeting function
- **Secret-based tool** - Demonstrates using environment secrets
- **OAuth tool** - Shows user authentication flow (requires `arcade login`)

### 3. Run Your Server

```bash
# Run HTTP server (default, great for development)
arcade mcp

# Or run stdio server (for Claude Desktop, Cursor, etc.)
arcade mcp stdio
```

You should see output like:

```text
DEBUG    | 11:43:11 | arcade_mcp_server.mcp_app:169 | Added tool: greet
INFO     | 11:43:11 | arcade_mcp_server.mcp_app:211 | Starting server v1.0.0 with 3 tools
INFO:     Started server process [89481]
INFO:     Waiting for application startup.
INFO     | 11:43:12 | arcade_mcp_server.worker:69 | MCP server started and ready for connections
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

View your server's API docs at http://127.0.0.1:8000/docs.

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

## Alternative: Direct Python Approach

If you prefer to use the library directly without the CLI, you can install just the server package:

```bash
uv pip install arcade-mcp-server
```

### Write a Tool

```python
from arcade_mcp_server import tool
from typing import Annotated

@tool
def greet(name: Annotated[str, "The name to greet"]) -> Annotated[str, "The greeting"]:
    return f"Hello, {name}!"
```

### Run the Server

You can run the server directly with Python:

```bash
# Using the module directly
python -m arcade_mcp_server

# Or if you have a server.py file with MCPApp
python server.py
```

**Note:** While this approach works, we recommend using `arcade mcp` for a better development experience with features like easy client configuration and starter templates.


## Building MCP Servers

The simplest way to create an MCP server programmatically is using `MCPApp`, which provides a FastAPI-like interface:

```python
from arcade_mcp_server import MCPApp
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

## Using the `arcade mcp` Command

The `arcade mcp` command provides a simple interface for running MCP servers. It automatically discovers tools, creates a server, and runs it with your chosen transport.

### Auto-Discovery Mode

The simplest way to run is to let the server discover tools in your current directory:

```bash
# Auto-discover @tool decorated functions
arcade mcp

# With stdio transport for Claude Desktop
arcade mcp stdio
```

### Loading Installed Packages

Load specific arcade packages or discover all installed ones:

```bash
# Load a specific arcade package
arcade mcp --tool-package github
arcade mcp -p slack

# Discover all installed arcade packages
arcade mcp --discover-installed

# Show which packages are being loaded
arcade mcp --discover-installed --show-packages
```

### Development Mode

For active development with hot reload:

```bash
# Run with hot reload and debug logging
arcade mcp --reload --debug

# Specify host and port
arcade mcp --host 0.0.0.0 --port 8000

# Load environment variables
arcade mcp --env-file .env
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
arcade mcp --reload --debug
```

### Logging
- Use `--debug` for verbose logging
- In stdio mode, logs go to stderr
- In HTTP mode, logs go to stdout

### Testing Tools
With HTTP transport and debug mode, access API documentation at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Next Steps

- Check out the [Examples](../examples/README.md) for detailed tutorials
- Learn about [Client Integration](../clients/claude.md) with Claude Desktop, Cursor, and VS Code
- Explore the [MCPApp API](../api/mcp_app.md) for advanced server customization
- Read about [Transport Modes](../advanced/transports.md) (stdio vs HTTP)
