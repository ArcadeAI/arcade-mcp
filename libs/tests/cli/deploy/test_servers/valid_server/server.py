#!/usr/bin/env python3
"""simple_server MCP server"""

import sys
from typing import Annotated

import httpx
from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.auth import GitHub

app = MCPApp(name="simpleserver", version="1.0.0", log_level="DEBUG")


@app.tool
def greet(name: Annotated[str, "The name of the person to greet"]) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"


# To use this tool, you need to either set the secret in the .env file or as an environment variable
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


# To use this tool, you need to either set your ARCADE_API_KEY as an environment variable or
# use the Arcade CLI (uv pip install arcade-mcp) and run 'arcade login' to authenticate.
@app.tool(requires_auth=GitHub(scopes=["public_repo"]))
async def star_repo(
    context: Context,
    owner: Annotated[str, "GitHub owner (user or org). E.g. 'ArcadeAI'"],
    repo: Annotated[str, "GitHub repository name. E.g. 'arcade-mcp'"],
) -> Annotated[str, "Confirmation that the repository was starred"]:
    """Star a public GitHub repository on behalf of the authenticated user."""
    # OAuth token is injected into the context at runtime.
    # LLMs and MCP clients cannot see or access your OAuth tokens.
    oauth_token = context.get_auth_token_or_empty()
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "simple_server-mcp-server",
    }
    url = f"https://api.github.com/user/starred/{owner}/{repo}"

    async with httpx.AsyncClient() as client:
        response = await client.put(url, headers=headers)
        response.raise_for_status()

    return f"Starred {owner}/{repo}."


# Run with specific transport
if __name__ == "__main__":
    # Get transport from command line argument, default to "http"
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"

    # Run the server
    # - "http" (default): HTTPS streaming for Cursor, VS Code, etc.
    # - "stdio": Standard I/O for Claude Desktop, CLI tools, etc.
    app.run(transport=transport, host="127.0.0.1", port=8000)
