# 02 - Building Apps

Build and run an MCP server programmatically using the FastAPI-like `MCPApp` interface.

## Running the Example

- **Run HTTP**: `python examples/02_building_apps.py`
- **Run stdio**: `python examples/02_building_apps.py stdio`

## Source Code

```python
--8<-- "docs/examples/02_building_apps.py"
```

## MCPApp Features

### 1. Creating an App

```python
from arcade_mcp import MCPApp

app = MCPApp(
    name="my_server",
    version="1.0.0",
    title="My MCP Server",
    instructions="This server provides utility tools",
    log_level="INFO"
)
```

### 2. Adding Tools

Use the `@app.tool` decorator to add tools:
```python
@app.tool
def my_tool(param: Annotated[str, "Description"]) -> str:
    """Tool description."""
    return f"Result: {param}"
```

### 3. Running the Server

```python
# Default HTTP transport
app.run()

# Specify options
app.run(
    host="0.0.0.0",
    port=8080,
    reload=True,  # Auto-reload on code changes
    transport="http"
)

# For stdio transport (Claude Desktop)
app.run(transport="stdio")
```

### 4. Using Context

Tools can access runtime context:
```python
@app.tool
async def context_aware(context: Context, value: str) -> dict:
    """Tool that uses context features."""
    # Access user info
    user_id = context.user_id
    
    # Use MCP features if available
    if context.mcp:
        await context.mcp.log("info", f"Processing for user: {user_id}")
    
    # Access secrets
    secret_keys = list(context.secrets.keys())
    
    return {
        "user": user_id,
        "value": value,
        "available_secrets": secret_keys
    }
```

## Key Concepts

- **FastAPI-like Interface**: Familiar decorator-based API design
- **Programmatic Control**: Build servers without CLI dependency
- **Transport Flexibility**: Support for both HTTP and stdio transports
- **Context Integration**: Access to user info, logging, and secrets
- **Development Features**: Hot reload, debug logging, and more