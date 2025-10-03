<h3 align="center">
  <a name="readme-top"></a>
  <img
    src="https://docs.arcade.dev/images/logo/arcade-logo.png"
    style="width: 400px;"
  >
</h3>
<div align="center">
    <a href="https://github.com/arcadeai/arcade-mcp/blob/main/LICENSE">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</a>
  <img src="https://img.shields.io/github/last-commit/ArcadeAI/arcade-mcp" alt="GitHub last commit">
<a href="https://github.com/arcadeai/arcade-mcp/actions?query=branch%3Amain">
<img src="https://img.shields.io/github/actions/workflow/status/arcadeai/arcade-mcp/main.yml?branch=main" alt="GitHub Actions Status">
</a>
<a href="https://img.shields.io/pypi/pyversions/arcade-mcp">
  <img src="https://img.shields.io/pypi/pyversions/arcade-mcp" alt="Python Version">
</a>
</div>
<div>
  <p align="center" style="display: flex; justify-content: center; gap: 10px;">
    <a href="https://x.com/TryArcade">
      <img src="https://img.shields.io/badge/Follow%20on%20X-000000?style=for-the-badge&logo=x&logoColor=white" alt="Follow on X" style="width: 125px;height: 25px; padding-top: .8px; border-radius: 5px;" />
    </a>
    <a href="https://www.linkedin.com/company/arcade-mcp" >
      <img src="https://img.shields.io/badge/Follow%20on%20LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="Follow on LinkedIn" style="width: 150px; padding-top: 1.5px;height: 22px; border-radius: 5px;" />
    </a>
    <a href="https://discord.com/invite/GUZEMpEZ9p">
      <img src="https://img.shields.io/badge/Join%20our%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join our Discord" style="width: 150px; padding-top: 1.5px; height: 22px; border-radius: 5px;" />
    </a>
  </p>
</div>

<p align="center" style="display: flex; justify-content: center; gap: 5px; font-size: 15px;">
    <a href="https://docs.arcade.dev/home" target="_blank">Documentation</a> •
    <a href="https://docs.arcade.dev/tools" target="_blank">Tools</a> •
    <a href="https://docs.arcade.dev/home/quickstart" target="_blank">Quickstart</a> •
    <a href="https://docs.arcade.dev/home/contact-us" target="_blank">Contact Us</a>

# Arcade MCP Server Framework

**To learn more about Arcade.dev, check out our [documentation](https://docs.arcade.dev/home).**

**To learn more about the Arcade MCP Server Framework, check out our [Arcade MCP documentation](https://python.mcp.arcade.dev/)**

_Pst. hey, you, give us a star if you like it!_

<a href="https://github.com/ArcadeAI/arcade-mcp">
  <img src="https://img.shields.io/github/stars/ArcadeAI/arcade-mcp.svg" alt="GitHub stars">
</a>

### Quick Start: Create a New Server

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

## Client Libraries

-   **[ArcadeAI/arcade-py](https://github.com/ArcadeAI/arcade-py):**
    The Python client for interacting with Arcade.

-   **[ArcadeAI/arcade-js](https://github.com/ArcadeAI/arcade-js):**
    The JavaScript client for interacting with Arcade.

-   **[ArcadeAI/arcade-go](https://github.com/ArcadeAI/arcade-go):**
    The Go client for interacting with Arcade.

## Support and Community

-   **Discord:** Join our [Discord community](https://discord.com/invite/GUZEMpEZ9p) for real-time support and discussions.
-   **GitHub:** Contribute or report issues on the [Arcade GitHub repository](https://github.com/ArcadeAI/arcade-mcp).
-   **Documentation:** Find in-depth guides and API references at [Arcade Documentation](https://docs.arcade.dev).
