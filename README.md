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
    <a href="https://docs.arcade.dev/en/resources/integrations" target="_blank">Prebuilt Tools</a> •
    <a href="https://docs.arcade.dev/en/resources/contact-us" target="_blank">Contact Us</a>

# Arcade MCP Server Framework

* **To see example servers built with Arcade MCP Server Framework (this repo), check out our [examples](examples/)**

* **To learn more about the Arcade MCP Server Framework (this repo), check out our [Arcade MCP documentation](https://docs.arcade.dev/en/guides/create-tools/tool-basics/build-mcp-server)**

* **To learn more about other offerings from Arcade.dev, check out our [documentation](https://docs.arcade.dev/en/home).**

_Pst. hey, you, give us a star if you like it!_

<a href="https://github.com/ArcadeAI/arcade-mcp">
  <img src="https://img.shields.io/github/stars/ArcadeAI/arcade-mcp.svg" alt="GitHub stars">
</a>

## Quick Start: Create a New Server

The fastest way to get started is with the `arcade new` CLI command, which creates a complete MCP server project:

```bash
# Install the CLI
uv tool install arcade-mcp

# Create a new server project
arcade new my_server

# Navigate to the project
cd my_server/src/my_server
```

This generates a project with:

- **server.py** - Main server file with MCPApp and example tools

- **pyproject.toml** - Dependencies and project configuration

- **.env.example** - Example `.env` file containing a secret required by one of the generated tools in `server.py`

The generated `server.py` includes proper command-line argument handling and three example tools:

```python
#!/usr/bin/env python3
"""simple_server MCP server"""

import sys
from typing import Annotated

import httpx
from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.auth import Reddit

app = MCPApp(name="simple_server", version="1.0.0", log_level="DEBUG")


@app.tool
def greet(name: Annotated[str, "The name of the person to greet"]) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"


# To use this tool locally, you need to either set the secret in the .env file or as an environment variable
@app.tool(requires_secrets=["MY_SECRET_KEY"])
def whisper_secret(context: Context) -> Annotated[str, "The last 4 characters of the secret"]:
    """Reveal the last 4 characters of a secret"""
    # Secrets are injected into the context at runtime.
    # LLMs and MCP clients cannot see or access your secrets
    # You can define secrets in a .env file.
    try:
        secret = context.get_secret("MY_SECRET_KEY")
    except Exception as e:
        return str(e)

    return "The last 4 characters of the secret are: " + secret[-4:]

# To use this tool locally, you need to install the Arcade CLI (uv tool install arcade-mcp)
# and then run 'arcade login' to authenticate.
@app.tool(requires_auth=Reddit(scopes=["read"]))
async def get_posts_in_subreddit(
    context: Context, subreddit: Annotated[str, "The name of the subreddit"]
) -> dict:
    """Get posts from a specific subreddit"""
    # Normalize the subreddit name
    subreddit = subreddit.lower().replace("r/", "").replace(" ", "")

    # Prepare the httpx request
    # OAuth token is injected into the context at runtime.
    # LLMs and MCP clients cannot see or access your OAuth tokens.
    oauth_token = context.get_auth_token_or_empty()
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "User-Agent": "{{ toolkit_name }}-mcp-server",
    }
    params = {"limit": 5}
    url = f"https://oauth.reddit.com/r/{subreddit}/hot"

    # Make the request
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()

        # Return the response
        return response.json()

# Run with specific transport
if __name__ == "__main__":
    # Get transport from command line argument, default to "stdio"
    # - "stdio" (default): Standard I/O for Claude Desktop, CLI tools, etc.
    #   Supports tools that require_auth or require_secrets out-of-the-box
    # - "http": HTTPS streaming for Cursor, VS Code, etc.
    #   Does not support tools that require_auth or require_secrets unless the server is deployed
    #   using 'arcade deploy' or added in the Arcade Developer Dashboard with 'Arcade' server type
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    # Run the server
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
# Run with stdio transport (default)
uv run server.py

# Run with http transport via command line argument
uv run server.py http

# Or use python directly
python server.py http
python server.py stdio
```

Your server will start and listen for connections. With HTTP transport, you can access the API docs at http://127.0.0.1:8000/docs.

### Configure MCP Clients

Once your server is running, connect it to your favorite AI assistant:

```bash
arcade configure claude # Configure Claude Desktop to connect to your stdio server in your current directory
arcade configure cursor --transport http --port 8080 # Configure Cursor to connect to your local HTTP server on port 8080
arcade configure vscode --entrypoint my_server.py # Configure VSCode to connect to your stdio server that will run when my_server.py is executed directly
```

## Installing this Repo from Source
```bash
git clone https://github.com/ArcadeAI/arcade-mcp.git && cd arcade-mcp && make install
```

## Support and Community

-   **Discord:** Join our [Discord community](https://discord.com/invite/GUZEMpEZ9p) for real-time support and discussions.
-   **GitHub:** Contribute or report issues on the [Arcade GitHub repository](https://github.com/ArcadeAI/arcade-mcp).
-   **Documentation:** Find in-depth guides and API references at [Arcade Documentation](https://docs.arcade.dev).
