### Middleware

Base interfaces and built-in middleware.

::: arcade_mcp_server.middleware.base.Middleware

::: arcade_mcp_server.middleware.base.MiddlewareContext

::: arcade_mcp_server.middleware.base.compose_middleware

#### Built-ins

::: arcade_mcp_server.middleware.logging.LoggingMiddleware

::: arcade_mcp_server.middleware.error_handling.ErrorHandlingMiddleware

#### Examples

```python
# Implement a custom middleware
from arcade_mcp_server.middleware.base import Middleware, MiddlewareContext

class TimingMiddleware(Middleware):
    async def __call__(self, context: MiddlewareContext, call_next):
        import time
        start = time.perf_counter()
        try:
            return await call_next(context)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            # Attach timing info to context metadata
            context.metadata["elapsed_ms"] = round(elapsed_ms, 2)
```

```python
# Compose middleware and create a server
from arcade_mcp_server.middleware.base import compose_middleware
from arcade_mcp_server.middleware.logging import LoggingMiddleware
from arcade_mcp_server.middleware.error_handling import ErrorHandlingMiddleware
from arcade_mcp_server.server import MCPServer
from arcade_core.catalog import ToolCatalog

middleware = compose_middleware([
    ErrorHandlingMiddleware(mask_error_details=False),
    LoggingMiddleware(log_level="INFO"),
    TimingMiddleware(),
])

server = MCPServer(catalog=ToolCatalog(), middleware=[middleware])
```
