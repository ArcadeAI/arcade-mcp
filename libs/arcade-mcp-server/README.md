# Arcade MCP Server

<p align="center">
  <img src="https://docs.arcade.dev/images/logo/arcade-logo.png" alt="Arcade Logo" width="200"/>
</p>

Arcade MCP (Model Context Protocol) Server enables AI assistants and development tools to interact with your Arcade tools through a standardized protocol. Build, deploy, and integrate MCP servers seamlessly across different AI platforms.

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

### Create Your First Server

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

## Community

- [GitHub Repository](https://github.com/ArcadeAI/arcade-mcp)
- [Discord Community](https://discord.gg/arcade-mcp)
- [Documentation](https://docs.arcade.dev)

## Analytics & Privacy

*Arcade MCP Server* collects anonymous usage data to help us improve the service and debug issues. We track "MCP server start" events to understand server usage patterns and reliability.

#### What We Track

When the server starts, we collect the following information:
- **Server configuration**: transport type (`http` or `stdio`), host, port
- **Server metadata**: tool count, server version
- **Runtime environment**: Python version, OS type and release
- **Timing**: device timestamp
- **Errors**: error messages (if startup fails)

#### Privacy

- For **anonymous users**: Events are tracked with an anonymous ID and no user profile is created
- For **authenticated users**: Events are linked to your account to help us provide better support
- **No sensitive data** (credentials, tool inputs/outputs, or personal information) is ever collected

#### Opt Out

To disable usage tracking, set the environment variable ARCADE_USAGE_TRACKING to 0.

## License

Arcade MCP Server is open source software licensed under the MIT license.
