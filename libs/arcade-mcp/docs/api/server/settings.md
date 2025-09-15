### Settings

Global configuration and environment-driven settings.

::: arcade_mcp.settings.MCPSettings

#### Sub-settings

::: arcade_mcp.settings.ServerSettings

::: arcade_mcp.settings.MiddlewareSettings

::: arcade_mcp.settings.NotificationSettings

::: arcade_mcp.settings.TransportSettings

::: arcade_mcp.settings.ArcadeSettings

::: arcade_mcp.settings.ToolEnvironmentSettings

#### Examples

```python
from arcade_mcp.settings import MCPSettings

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
        http_port=7777,
    ),
)
```

```python
# Loading from environment
from arcade_mcp.settings import MCPSettings

# Values like ARCADE_MCP_DEBUG, ARCADE_MCP_HTTP_PORT, etc. are parsed
settings = MCPSettings()
```
