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
from arcade_mcp_server import MCPApp

app = MCPApp(
    name="my_server",
    version="1.0.0",
    title="My MCP Server",
    instructions="This server provides utility tools",
    log_level="INFO"
)
```

### 2. Adding Tools

#### Method 1: Direct Tool Definition
Use the `@app.tool` decorator to define tools directly:
```python
@app.tool
def my_tool(param: Annotated[str, "Description"]) -> str:
    """Tool description."""
    return f"Result: {param}"
```

#### Method 2: Importing Tools from Files
Import tools from other files and add them explicitly:
```python
from my_tools import calculate, process_data

# Add imported tools to the app
app.add_tool(calculate)
app.add_tool(process_data)
```

#### Method 3: Importing from Packages
Import tools from Arcade packages:
```python
from arcade_gmail.tools import list_emails

# Add package tools to the app
app.add_tool(list_emails)
```

This approach gives you explicit control over which tools are loaded and allows for modular organization.

**For a comprehensive example of tool organization, see [06_tool_organization.md](06_tool_organization.md).**

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
    if context:
        await context.log.info(f"Processing for user: {user_id}")

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
