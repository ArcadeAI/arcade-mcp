#!/usr/bin/env python3
"""simple_server MCP server"""

import sys
from typing import Annotated

import httpx
from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.auth import Reddit

app = MCPApp(name="simpleserver", version="1.0.0", log_level="DEBUG")


@app.tool
def greet(name: dict) -> str:
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
        "User-Agent": "simple_server-mcp-server",
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
    # Get transport from command line argument, default to "http"
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"

    # Run the server
    # - "http" (default): HTTPS streaming for Cursor, VS Code, etc.
    # - "stdio": Standard I/O for Claude Desktop, CLI tools, etc.
    app.run(transport=transport, host="127.0.0.1", port=8000)
