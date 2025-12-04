"""
Simple example: Connect to MCP servers and create tool registry for evals.

Set environment variables before running:
    export ARCADE_API_KEY="arc_..."
    export ARCADE_USER_ID="user@example.com"
    export GITHUB_TOKEN="ghp_..."  # Optional, for GitHub MCP
"""

import os

from arcade_evals import MCPToolRegistry, load_arcade_cloud, load_from_http


def main():
    # =========================================================================
    # Option 1: Arcade Cloud MCP
    # =========================================================================
    tools = load_arcade_cloud(
        gateway_slug="your-gateway-slug",
        # Or pass explicitly:
        # arcade_api_key="arc_...",
        # arcade_user_id="user@example.com"
    )
    print(f"Arcade: {len(tools)} tools")

    # =========================================================================
    # Option 2: GitHub Copilot MCP (or any HTTP MCP with auth headers)
    # =========================================================================
    github_tools = load_from_http(
        url="https://api.githubcopilot.com/mcp/",
        headers={
            "Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}",
            "Accept": "application/json",
        },
    )
    print(f"GitHub: {len(github_tools)} tools")

    # =========================================================================
    # Create registry for evals
    # =========================================================================
    registry = MCPToolRegistry(tools)
    openai_tools = registry.list_tools_for_model("openai")
    print(f"Registry: {len(openai_tools)} tools ready for evals")

    return registry


if __name__ == "__main__":
    main()
