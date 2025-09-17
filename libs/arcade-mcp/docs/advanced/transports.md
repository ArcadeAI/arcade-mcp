# Transport Modes

MCP servers can communicate with clients through different transport mechanisms. Each transport is optimized for specific use cases and client types.

## stdio Transport

The stdio (standard input/output) transport is used for direct client connections.

### Characteristics
- Communicates via standard input/output streams
- Logs go to stderr to avoid interfering with protocol messages
- Ideal for desktop applications and command-line tools
- Used by Claude Desktop and similar clients

### Usage

```bash
# Run with stdio transport
python -m arcade_mcp stdio

# Or with MCPApp
app.run(transport="stdio")
```

### Client Configuration

For Claude Desktop, configure in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-tools": {
      "command": "python",
      "args": ["-m", "arcade_mcp", "stdio"],
      "cwd": "/path/to/your/tools"
    }
  }
}
```

## HTTP Transport

The HTTP transport provides REST/SSE endpoints for web-based clients.

### Characteristics
- RESTful API with Server-Sent Events (SSE) for streaming
- Supports hot reload for development
- Includes health checks and API documentation
- Can be deployed behind reverse proxies
- Suitable for web applications and services

### Usage

```bash
# Run with HTTP transport (default)
python -m arcade_mcp

# With specific host and port
python -m arcade_mcp --host 0.0.0.0 --port 8080

# Or with MCPApp
app.run(transport="http", host="0.0.0.0", port=8080)
```

### Endpoints

When running in HTTP mode, the server provides:

- `GET /health` - Health check endpoint
- `GET /mcp` - SSE endpoint for MCP protocol
- `GET /docs` - Swagger UI documentation (debug mode)
- `GET /redoc` - ReDoc documentation (debug mode)

### Development Features

```bash
# Enable hot reload and debug mode
python -m arcade_mcp --reload --debug

# This enables:
# - Automatic restart on code changes
# - Detailed error messages
# - API documentation endpoints
# - Verbose logging
```

## Choosing a Transport

### Use stdio when:
- Integrating with desktop applications (Claude Desktop, VS Code)
- Building command-line tools
- You need simple, direct communication
- Running in environments without network access

### Use HTTP when:
- Building web applications
- Deploying to cloud environments
- You need to support multiple concurrent clients
- Integrating with existing web services
- You want API documentation and testing tools

## Transport Configuration

### Environment Variables

Both transports respect common environment variables:

```bash
# Server identification
MCP_SERVER_NAME="My MCP Server"
MCP_SERVER_VERSION="1.0.0"

# Logging
MCP_DEBUG=true
MCP_LOG_LEVEL=DEBUG

# HTTP-specific
MCP_HTTP_HOST=0.0.0.0
MCP_HTTP_PORT=8080
```

### Programmatic Configuration

When using MCPApp:

```python
from arcade_mcp import MCPApp

app = MCPApp(
    name="my-server",
    version="1.0.0",
    log_level="DEBUG"
)

# Run with specific transport
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        app.run(transport="stdio")
    else:
        app.run(transport="http", host="0.0.0.0", port=8080)
```

## Security Considerations

### stdio Transport
- Inherits security context of the parent process
- No network exposure
- Suitable for trusted environments

### HTTP Transport
- Exposes network endpoints
- Should use authentication in production
- Consider using HTTPS with reverse proxy
- Implement rate limiting for public deployments

## Advanced Transport Features

### Custom Middleware (HTTP)

Add custom middleware to HTTP transports:

```python
from arcade_mcp import MCPApp

app = MCPApp(name="my-server")

# Add custom middleware
@app.middleware("http")
async def add_custom_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Custom-Header"] = "value"
    return response
```

### Transport Events

Listen to transport lifecycle events:

```python
@app.on_event("startup")
async def startup_handler():
    print("Server starting up...")

@app.on_event("shutdown")
async def shutdown_handler():
    print("Server shutting down...")
```
