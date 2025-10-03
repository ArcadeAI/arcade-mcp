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

**Recommended: Using Arcade CLI**

```bash
# Run with stdio transport
uv run server.py stdio
```

**Alternative: Direct Python**

```bash
# Run your server directly
uv run server.py stdio

# Or with python
app.run(transport="stdio")
```

### Client Configuration

For Claude Desktop, use the `arcade configure` command:

```bash
arcade configure claude --from-local
```

Or manually edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-tools": {
      "command": "arcade",
      "args": ["mcp", "stdio"],
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

**Recommended: Using Arcade CLI**

```bash
# Run with HTTP transport (default)
uv run server.py
uv run server.py http
```

**Alternative: Direct Python**

```bash
# Run your server directly
uv run server.py

# Or with python
app.run(transport="http", host="0.0.0.0", port=8080)
```

### Endpoints

When running in HTTP mode, the server provides:

- `GET /health` - Health check endpoint
- `GET /mcp` - SSE endpoint for MCP protocol
- `GET /docs` - Swagger UI documentation (debug mode)
- `GET /redoc` - ReDoc documentation (debug mode)

### Development Features

**With Arcade CLI:**

```python
# Enable hot reload and debug mode
app.run(host="127.0.0.1", port=8000, reload=True)

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
from arcade_mcp_server import MCPApp

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
from arcade_mcp_server import MCPApp

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
