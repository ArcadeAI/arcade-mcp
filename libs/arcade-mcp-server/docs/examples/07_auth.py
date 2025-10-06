#!/usr/bin/env python3
"""
07_auth.py - Using tools with OAuth

This example demonstrates how to create and use tools that require OAuth.
Tools that require auth will automatically prompt users to authorize the action when called.

Prerequisites:
    1. Install arcade-mcp: uv pip install arcade-mcp
    2. Login to Arcade: arcade login
    3. Run this server: uv run 07_auth.py

To run:
    uv run examples/07_auth.py
    uv run examples/07_auth.py stdio  # For Claude Desktop
"""

import sys
from typing import Annotated

import httpx
from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.auth import Reddit

# Create the app
app = MCPApp(name="auth_example", version="1.0.0", log_level="DEBUG")


# To use this tool, you need to use the Arcade CLI (uv pip install arcade-mcp)
# and run 'arcade login' to authenticate.
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
        "User-Agent": "mcp_server-mcp-server",
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

    print(f"Starting auth example server with {transport} transport")
    print("Prerequisites:")
    print("  1. Install: uv pip install arcade-mcp")
    print("  2. Login: arcade login")
    print("")

    # Run the server
    # - "http" (default): HTTP streaming for Cursor, VS Code, etc.
    # - "stdio": Standard I/O for Claude Desktop, CLI tools, etc.
    app.run(transport=transport, host="127.0.0.1", port=8000)
