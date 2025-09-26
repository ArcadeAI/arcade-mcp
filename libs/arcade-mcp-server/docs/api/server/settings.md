### Settings

Global configuration and environment-driven settings.

::: arcade_mcp_server.settings.MCPSettings

#### Sub-settings

::: arcade_mcp_server.settings.ServerSettings

::: arcade_mcp_server.settings.MiddlewareSettings

::: arcade_mcp_server.settings.NotificationSettings

::: arcade_mcp_server.settings.TransportSettings

::: arcade_mcp_server.settings.ArcadeSettings

::: arcade_mcp_server.settings.ToolEnvironmentSettings

#### Examples

```python
from arcade_mcp_server.settings import MCPSettings

settings = MCPSettings(
    debug=True,
    middleware=MCPSettings.middleware.__class__(
        enable_logging=True,
        mask_error_details=False,
    ),
    server=MCPSettings.server.__class__(
        title="My MCP Server",
        instructions="Use responsibly",
    ),
    transport=MCPSettings.transport.__class__(
        http_host="0.0.0.0",
        http_port=8000,
    ),
)
```

```python
# Loading from environment
from arcade_mcp_server.settings import MCPSettings

# Values like ARCADE_MCP_DEBUG, ARCADE_MCP_HTTP_PORT, etc. are parsed
settings = MCPSettings()
```
