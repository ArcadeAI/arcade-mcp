### Exceptions

Domain-specific error types raised by the MCP server and components.

::: arcade_mcp_server.exceptions

#### Examples

```python
from arcade_mcp_server.exceptions import (
    MCPError,
    NotFoundError,
    DuplicateError,
    ValidationError,
    ToolError,
)

# Raising a not-found when a resource is missing
async def read_resource_or_fail(uri: str) -> str:
    if not await exists(uri):
        raise NotFoundError(f"Resource not found: {uri}")
    return await read(uri)

# Validating input
def validate_age(age: int) -> None:
    if age < 0:
        raise ValidationError("age must be non-negative")

# Handling tool execution errors in middleware or handlers
async def call_tool_safely(call):
    try:
        return await call()
    except ToolError as e:
        # Convert to an error result or re-raise
        raise MCPError(f"Tool failed: {e}")
```
