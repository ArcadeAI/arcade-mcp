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

We recommend installing the `arcade-mcp-server` library for direct Python development:

```bash
uv pip install arcade-mcp-server
```

Or install the `arcade-mcp` CLI package for additional tooling and streamlined development workflow:

```bash
uv pip install arcade-mcp
```

### Quick Start: Create a New Server (Recommended)

The fastest way to get started is with the `arcade new` command, which creates a complete MCP server project:

```bash
# Install the CLI
uv pip install arcade-mcp

# Create a new server project
arcade new my_server

# Navigate to the project
cd my_server
```

This generates a complete project with:

- **server.py** - Main server file with MCPApp and example tools

- **pyproject.toml** - Dependencies and project configuration

- **.env.example** - Example `.env` file containing a secret required by one of the generated tools in `server.py`

The generated `server.py` includes proper command-line argument handling:

```python
#!/usr/bin/env python3
import sys
from typing import Annotated
from arcade_mcp_server import MCPApp

app = MCPApp(name="my_server", version="1.0.0")

@app.tool
def greet(name: Annotated[str, "Name to greet"]) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"
    app.run(transport=transport, host="127.0.0.1", port=8000)
```

This approach gives you:
- **Complete Project Setup** - Everything you need in one command

- **Best Practices** - Proper dependency management with pyproject.toml

- **Example Code** - Learn from working examples of common patterns

- **Production Ready** - Structured for growth and deployment

### Running Your Server

Run your server directly with Python:

```bash
# Run with HTTP transport (default)
uv run server.py

# Run with stdio transport (for Claude Desktop)
uv run server.py stdio

# Or use python directly
python server.py http
python server.py stdio
```

Your server will start and listen for connections. With HTTP transport, you can access the API docs at http://127.0.0.1:8000/docs.

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
