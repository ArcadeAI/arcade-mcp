# Simple Tools Example

This example demonstrates basic Arcade tool patterns including:
- Simple functions with parameters
- Using ToolContext to access user information
- Returning different data types (strings, numbers, objects)

## Running the Example

1. Install Arcade:
```bash
pip install arcade-ai
```

2. Run the worker:
```bash
arcade serve
```

3. Test the tools:
```bash
# In another terminal
curl -X POST http://localhost:8002/worker/tools/HelloWorld \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice"}'

curl -X POST http://localhost:8002/worker/tools/AddNumbers \
  -H "Content-Type: application/json" \
  -d '{"a": 10, "b": 25}'

curl -X POST http://localhost:8002/worker/tools/ProcessList \
  -H "Content-Type: application/json" \
  -d '{"items": ["apple", "banana", "apple", "cherry"], "operation": "unique"}'
```

## Using with MCP

Run as an MCP server:
```bash
# stdio mode
arcade serve --local

# Server-Sent Events mode
arcade serve --sse --no-auth
```