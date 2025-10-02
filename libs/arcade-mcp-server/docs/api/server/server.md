

# Server

### Low-level Server

Low-level server for hosting Arcade tools over MCP.

::: arcade_mcp_server.server.MCPServer

#### Examples

```python
# Basic server with tool catalog and stdio transport
import asyncio
from arcade_mcp_server.server import MCPServer
from arcade_core.catalog import ToolCatalog
from arcade_mcp_server.transports.stdio import StdioTransport

async def main():
    catalog = ToolCatalog()
    server = MCPServer(catalog=catalog, name="example", version="1.0.0")
    await server._start()
    try:
        # Run stdio transport loop
        transport = StdioTransport()
        await transport.run(server)
    finally:
        await server._stop()

if __name__ == "__main__":
    asyncio.run(main())
```

```python
# Handling a single HTTP streamable connection
import asyncio
from arcade_mcp_server.server import MCPServer
from arcade_core.catalog import ToolCatalog
from arcade_mcp_server.transports.http_streamable import HTTPStreamableTransport

async def run_http():
    catalog = ToolCatalog()
    server = MCPServer(catalog=catalog)
    await server._start()
    try:
        transport = HTTPStreamableTransport(host="0.0.0.0", port=8000)
        await transport.run(server)
    finally:
        await server._stop()

asyncio.run(run_http())
```
