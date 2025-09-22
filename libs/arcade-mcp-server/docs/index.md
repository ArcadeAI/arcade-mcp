# Arcade MCP

<p align="center">
  <img src="https://docs.arcade.dev/images/logo/arcade-logo.png" alt="Arcade Logo" width="200"/>
</p>

Arcade MCP (Model Context Protocol) enables AI assistants and development tools to interact with your Arcade tools through a standardized protocol. Build, deploy, and integrate tools seamlessly across different AI platforms.

## Quick Links

- **[Quickstart Guide](getting-started/quickstart.md)** - Get up and running in minutes
- **[Walkthrough](examples/README.md)** - Learn by example
- **[API Reference](api/app.md)** - MCPApp API documentation

## Features

- 🚀 **FastAPI-like Interface** - Simple, intuitive API with `MCPApp`
- 🔧 **Tool Discovery** - Automatic discovery of tools in your project
- 🔌 **Multiple Transports** - Support for stdio and HTTP/SSE
- 🤖 **Multi-Client Support** - Works with Claude, Cursor, and more
- 📦 **Package Integration** - Load installed Arcade packages
- 🔐 **Built-in Security** - Environment-based configuration and secrets
- 🔄 **Hot Reload** - Development mode with automatic reloading
- 📊 **Production Ready** - Deploy with Docker, systemd, PM2, or cloud platforms

## Getting Started

### Installation

```bash
pip install arcade-mcp-server
```

### Create Your First Tool

```python
from arcade_mcp_server import MCPApp
from typing import Annotated

app = MCPApp(name="my-tools", version="1.0.0")

@app.tool
def greet(name: Annotated[str, "Name to greet"]) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    app.run()
```

### Run Your Server

```bash
# For development
python my_tools.py

# For Claude Desktop
python -m arcade_mcp_server stdio

# For HTTP clients
python -m arcade_mcp_server --host 0.0.0.0 --port 8080
```

## Client Integration

Connect your MCP server with AI assistants and development tools:

- **[Claude Desktop](clients/claude.md)** - Native MCP support in Claude
- **[Cursor IDE](clients/cursor.md)** - Enhanced AI coding with MCP tools
- **[VS Code](clients/vscode.md)** - Integrate with Visual Studio Code
- **[MCP Inspector](clients/inspector.md)** - Debug and test your tools


## Learn More

- **[Walkthrough](examples/README.md)** - Comprehensive examples and tutorials
- **[API Reference](api/app.md)** - Detailed API documentation
- **[Transport Modes](advanced/transports.md)** - stdio and HTTP transport details

## Community

- [GitHub Repository](https://github.com/ArcadeAI/arcade-mcp)
- [Discord Community](https://discord.gg/arcade-mcp)
- [Documentation](https://docs.arcade.dev)

## License

Arcade MCP server is open source software licensed under the MIT license.
