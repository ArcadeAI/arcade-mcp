# Arcade MCP

<p align="center">
  <img src="https://docs.arcade.dev/images/logo/arcade-logo.png" alt="Arcade Logo" width="200"/>
</p>

Arcade MCP (Model Context Protocol) enables AI assistants and development tools to interact with your Arcade tools through a standardized protocol. Build, deploy, and integrate your MCP servers seamlessly across different AI platforms.

## Quick Links

- **[Quickstart Guide](getting-started/quickstart.md)** - Get up and running in minutes
- **[Walkthrough](examples/README.md)** - Learn by example
- **[API Reference](api/mcp_app.md)** - MCPApp API documentation

## Features

- 🚀 **FastAPI-like Interface** - Simple, intuitive API with `MCPApp`
- 🔧 **Tool Discovery** - Automatic discovery of tools in your project
- 🔌 **Multiple Transports** - Support for stdio and HTTP/SSE
- 🤖 **Multi-Client Support** - Works with Claude, Cursor, VS Code, and more
- 📦 **Package Integration** - Load installed Arcade packages
- 🔐 **Built-in Security** - Environment-based configuration and secrets
- 🔄 **Hot Reload** - Development mode with automatic reloading
- 📊 **Production Ready** - Deploy with Docker, systemd, PM2, or cloud platforms

## Getting Started

### Installation

We recommend installing the `arcade-mcp` CLI package, which includes `arcade-mcp-server` and provides a streamlined development workflow:

```bash
uv pip install arcade-mcp
```

Or install just the server library if you prefer a direct Python approach:

```bash
uv pip install arcade-mcp-server
```

### Quick Start: Create a New Server (Recommended)

The fastest way to get started is with the `arcade new` command, which creates a starter MCP server with example tools:

```bash
# Create a new server project
arcade new my_server

# Navigate to the project
cd my_server

# Run the server
arcade mcp
```

The generated server includes three example tools:
- **Simple tool** - A basic function to get you started
- **Secret-based tool** - Shows how to use environment secrets
- **OAuth tool** - Demonstrates how to use a OAuth tool (requires `arcade login`)

### Manual Setup: Create Your First Tool

If you prefer to create tools manually, you can use the `MCPApp` interface:

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

### Running Your Server

**Recommended: Use the Arcade CLI**

```bash
# Run HTTP server (default)
arcade mcp

# Run stdio server (for Claude Desktop, Cursor, etc.)
arcade mcp stdio

# Run with debug logging and hot reload
arcade mcp --debug --reload
```

**Alternative: Direct Python execution**

```bash
# Run your server.py file directly
python server.py
```

### Configure MCP Clients

Once your server is running, connect it to your favorite AI assistant:

```bash
# Configure Claude Desktop (configures for stdio)
arcade configure claude --from-local

# Configure Cursor (configures for http streamable)
arcade configure cursor --from-local

# Configure VS Code (configures for http streamable)
arcade configure vscode --from-local
```


## Client Integration

Connect your MCP server with AI assistants and development tools:

- **[Claude Desktop](clients/claude.md)** - Native MCP support in Claude
- **[Cursor IDE](clients/cursor.md)** - Enhanced AI coding with MCP tools
- **[VS Code](clients/vscode.md)** - Integrate with Visual Studio Code
- **[MCP Inspector](clients/inspector.md)** - Debug and test your tools


## Learn More

- **[Walkthrough](examples/README.md)** - Comprehensive examples and tutorials
- **[API Reference](api/mcp_app.md)** - Detailed API documentation
- **[Transport Modes](advanced/transports.md)** - stdio and HTTP transport details

## Community

- [GitHub Repository](https://github.com/ArcadeAI/arcade-mcp)
- [Discord Community](https://discord.com/invite/GUZEMpEZ9p)
- [Documentation](https://docs.arcade.dev)

## License

Arcade MCP server is open source software licensed under the MIT license.
