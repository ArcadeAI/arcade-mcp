# 06 - Tool Organization

This example demonstrates the power of direct Python server execution by showing how to organize tools across multiple files and packages.

## Running the Example

- **Run HTTP**: `uv run 06_tool_organization.py`
- **Run stdio**: `uv run 06_tool_organization.py stdio`

## Project Structure

The example demonstrates this recommended project structure:

```
my_server/
├── .env
├── server.py          # Main MCPApp
├── tools/
│   ├── __init__.py
│   ├── math_tools.py  # @tool decorated functions
│   └── text_tools.py  # @tool decorated functions
├── pyproject.toml
└── README.md
```

## Source Code

```python
--8<-- "docs/examples/06_tool_organization.py"
```

## Key Concepts

### 1. Modular Tool Organization

Define tools in separate files using the `@tool` decorator:

```python
# tools/math_tools.py
from arcade_mcp_server import tool
from typing import Annotated

@tool
def add(a: Annotated[int, "First number"], b: Annotated[int, "Second number"]) -> int:
    """Add two numbers together."""
    return a + b
```

### 2. Importing Tools from Files

Import tools from your local files and add them explicitly:

```python
# server.py
from tools_math import add, multiply
from tools_text import capitalize_string, word_count

app.add_tool(add)
app.add_tool(multiply)
app.add_tool(capitalize_string)
app.add_tool(word_count)
```

### 3. Importing Tools from Packages

You can also import tools from Arcade packages:

```python
# Import tools from other Arcade packages
from arcade_gmail.tools import list_emails
from arcade_google.tools import search_web

app.add_tool(list_emails)
app.add_tool(search_web)
```

### 4. Mixed Approaches

Combine imported tools with direct tool definitions:

```python
# Import tools from files
from tools_math import add
app.add_tool(add)

# Define tools directly
@app.tool
def server_info() -> dict:
    """Return information about this server."""
    return {"name": "My Server", "version": "1.0.0"}
```

## Benefits of This Approach

### Explicit Control
- Choose exactly which tools to include
- No auto-discovery surprises
- Clear dependency management

### Standard Python Patterns
- Use normal Python imports
- Follow Python packaging conventions
- Leverage existing Python tools (uv, poetry, etc.)

### Flexible Organization
- Tools can be in separate files
- Tools can be in separate packages
- Easy to test individual tools

### Development Workflow
- Use `uv run server.py` for fast iteration
- Standard Python debugging tools work
- Easy to add CLI arguments for configuration

## Running Your Own Organized Server

### 1. Create Your Project Structure

```
my_server/
├── .env
├── server.py
├── tools/
│   ├── __init__.py
│   ├── email_tools.py
│   ├── file_tools.py
│   └── api_tools.py
└── pyproject.toml
```

### 2. Create Tool Files

```python
# tools/email_tools.py
from arcade_mcp_server import tool

@tool
def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email."""
    # Implementation here
    return {"status": "sent", "to": to}
```

### 3. Build Your Server

```python
# server.py
import sys
from arcade_mcp_server import MCPApp
from tools.email_tools import send_email
from tools.file_tools import read_file, write_file

app = MCPApp(name="my_server", version="1.0.0")

# Add imported tools
app.add_tool(send_email)
app.add_tool(read_file)
app.add_tool(write_file)

# Add direct tools
@app.tool
def server_status() -> str:
    return "Server is running"

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"
    app.run(transport=transport)
```

### 4. Run Your Server

```bash
# Run with uv
uv run server.py

# Run with stdio for Claude Desktop
uv run server.py stdio
```

## Comparison with CLI Approach

| Feature | Direct Python | CLI Auto-discovery |
|---------|---------------|-------------------|
| Tool Selection | Explicit with `app.add_tool()` | Automatic discovery |
| File Organization | Your choice | Directory-based |
| Import Control | Full control | Limited |
| Deployment | Standard Python | Custom CLI needed |
| Testing | Standard Python tools | Mix Python + CLI |
| Debugging | Python debuggers work | Limited |

The direct Python approach gives you full control and follows standard Python patterns, making it ideal for production servers and complex tool organization.
