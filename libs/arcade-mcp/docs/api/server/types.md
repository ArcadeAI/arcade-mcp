### Types

Core Pydantic models and enums for the MCP protocol shapes.

::: arcade_mcp.types

#### Examples

```python
# Constructing a JSON-RPC request and response model
from arcade_mcp.types import JSONRPCRequest, JSONRPCResponse

req = JSONRPCRequest(id=1, method="ping", params={})
res = JSONRPCResponse(id=req.id, result={})
print(req.model_dump_json())
print(res.model_dump_json())
```

```python
# Building a tools/call request and examining result shape
from arcade_mcp.types import CallToolRequest, CallToolResult

call = CallToolRequest(
    id=2,
    method="tools/call",
    params={
        "name": "Toolkit.tool",
        "arguments": {"text": "hello"},
    },
)
# Result would typically be produced by the server:
result = CallToolResult(content=[{"type": "text", "text": "Echo: hello"}], isError=False)
```
