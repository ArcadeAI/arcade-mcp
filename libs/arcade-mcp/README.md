# arcade-mcp

Model Context Protocol (MCP) server framework for Arcade AI.

## Installation

```bash
pip install arcade-mcp
```

## Quick Start

Create a simple MCP server:

```python
from arcade_mcp import Server
from arcade_tdk import tool

@tool
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

server = Server()

if __name__ == "__main__":
    # Run with different transports
    server.run(transport="stream")  # Default - works with Claude Desktop, Cursor
    # server.run(transport="sse")    # Server-sent events for Cursor
    # server.run(transport="stdio")  # Standard I/O for VS Code
```

## Usage

Run your server:

```bash
# Default HTTPS stream transport
python server.py

# Specific transport
python server.py stdio
python server.py sse
python server.py stream
```

## Features

- Simple, pythonic API
- Support for all MCP transports (stdio, SSE, HTTPS stream)
- Automatic .env file loading
- Built-in auth support with Arcade Cloud
- Tool discovery and registration
- Compatible with all major MCP clients

## Documentation

See the [Arcade AI documentation](https://docs.arcade.ai) for more information.