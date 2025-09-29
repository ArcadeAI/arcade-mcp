### Types

Core Pydantic models and enums for the MCP protocol shapes.

::: arcade_mcp_server.types

#### Examples

```python
# Constructing a JSON-RPC request and response model
from arcade_mcp_server.types import JSONRPCRequest, JSONRPCResponse

req = JSONRPCRequest(id=1, method="ping", params={})
res = JSONRPCResponse(id=req.id, result={})
print(req.model_dump_json())
print(res.model_dump_json())
```

```python
# Building a tools/call request and examining result shape
from arcade_mcp_server.types import CallToolRequest, CallToolResult, TextContent

call = CallToolRequest(
    id=2,
    method="tools/call",
    params={
        "name": "Toolkit.tool",
        "arguments": {"text": "hello"},
    },
)
# Result would typically be produced by the server:
result = CallToolResult(
    content=[TextContent(type="text", text="Echo: hello")],
    structuredContent={"result": "Echo: hello"},
    isError=False
)
```
