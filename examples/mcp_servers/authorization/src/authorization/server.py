#!/usr/bin/env python3
"""authorization MCP server"""

from typing import Annotated

import httpx
from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.auth import Reddit
from arcade_mcp_server.resource_server import (
    AuthorizationServerEntry,
    ResourceServerAuth,
)

# Option 1: Single authorization server with custom audience
# Use expected_audiences when your auth server returns a non-standard audience (aud) claim
# (e.g., client_id instead of canonical_url)
resource_server_auth = ResourceServerAuth(
    canonical_url="http://127.0.0.1:8000/mcp",
    authorization_servers=[
        AuthorizationServerEntry(  # WorkOS Authkit example configuration
            authorization_server_url="https://your-workos.authkit.app",
            issuer="https://your-workos.authkit.app",
            jwks_uri="https://your-workos.authkit.app/oauth2/jwks",
            expected_audiences=["your-authkit-client-id"],  # Override expected aud claim
        ),
    ],
)

# Option 2: Multiple authorization servers with different keys (e.g., multi-IdP)
# resource_server_auth = ResourceServerAuth(
#     canonical_url="http://127.0.0.1:8000/mcp",
#     authorization_servers=[
#         AuthorizationServerEntry(  # WorkOS Authkit example configuration
#             authorization_server_url="https://your-workos.authkit.app",
#             issuer="https://your-workos.authkit.app",
#             jwks_uri="https://your-workos.authkit.app/oauth2/jwks",
#             expected_audiences=["your-authkit-client-id"],
#         ),
#         AuthorizationServerEntry(  # Keycloak example configuration
#             authorization_server_url="http://localhost:8080/realms/mcp-test",
#             issuer="http://localhost:8080/realms/mcp-test",
#             jwks_uri="http://localhost:8080/realms/mcp-test/protocol/openid-connect/certs",
#             algorithm="RS256",
#             expected_audiences=["your-keycloak-client-id"],
#         )
#     ],
# )

# Option 3: Authorization via env vars (place in your .env file)
# ```bash
# MCP_RESOURCE_SERVER_CANONICAL_URL=http://127.0.0.1:8000/mcp
# MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS='[
#   {
#     "authorization_server_url": "https://your-workos.authkit.app",
#     "issuer": "https://your-workos.authkit.app",
#     "jwks_uri": "https://your-workos.authkit.app/oauth2/jwks",
#     "algorithm": "RS256",
#     "expected_audiences": ["your-authkit-client-id"]
#   }
# ]'
# ```
# resource_server_auth = ResourceServerAuth()

app = MCPApp(name="authorization", version="1.0.0", log_level="DEBUG", auth=resource_server_auth)


@app.tool
def greet(name: Annotated[str, "The name of the person to greet"]) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"


@app.tool(requires_secrets=["MY_SECRET_KEY"])
def whisper_secret(context: Context) -> Annotated[str, "The last 4 characters of the secret"]:
    """Reveal the last 4 characters of a secret"""
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
    subreddit = subreddit.lower().replace("r/", "").replace(" ", "")
    oauth_token = context.get_auth_token_or_empty()
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "User-Agent": "authorization-mcp-server",
    }
    params = {"limit": 5}
    url = f"https://oauth.reddit.com/r/{subreddit}/hot"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()

        return response.json()


if __name__ == "__main__":
    app.run(transport="http", host="127.0.0.1", port=8000)
