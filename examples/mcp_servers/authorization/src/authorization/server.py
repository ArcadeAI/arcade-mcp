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

# Option 1: Single authorization server — Arcade's intermediate AS
# Use expected_audiences when your auth server returns a non-standard audience (aud) claim
# (e.g., client_id instead of canonical_url). Arcade's intermediate AS issues tokens whose
# aud claim is "urn:arcade:mcp"; including the canonical_url here keeps acceptance tolerant
# of clients that bind tokens to the resource URL instead.
_canonical_url = "https://5afc-50-189-121-137.ngrok-free.app/mcp"
resource_server_auth = ResourceServerAuth(
    canonical_url=_canonical_url,
    authorization_servers=[
        AuthorizationServerEntry(  # Arcade intermediate AS configuration
            authorization_server_url="https://cloud.arcade.dev/oauth2",
            issuer="https://cloud.arcade.dev/oauth2",
            jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
            algorithm="Ed25519",
            expected_audiences=[
                "urn:arcade:mcp",
                _canonical_url,
            ],
        )
    ],
    # SEP-835 surface split: the MCP 2025-11-25 spec treats two scope
    # surfaces as independent.
    #
    # ``scopes_supported``        (RFC 9728 PRM): documented baseline.
    # ``default_challenge_scopes`` (RFC 6750 entry-401): what the server
    #                              is asking the client to acquire RIGHT
    #                              NOW.
    #
    # RECOMMENDED baseline: both surfaces advertise the same minimum
    # scope set. Tools that need elevated scopes raise
    # ``InsufficientScopeError`` at dispatch time, producing a 403
    # step-up challenge. Aligns with the MCP security best practices
    # section Scope Minimization (minimal initial set, incremental
    # step-up, precise challenges).
    #
    # The vocabulary here is the AS's vocabulary, i.e. what the MCP
    # client sends in its authorization request to
    # ``authorization_server_url``. NOT the downstream provider scope.
    # With Arcade's intermediate AS the scope chain is split:
    #
    #   MCP client  --[scope=mcp]----->  cloud.arcade.dev/oauth2   (AS)
    #     Arcade    --[scope=read]---->  Reddit                    (provider)
    #
    # ``Reddit(scopes=["read"])`` on ``get_posts_in_subreddit`` configures
    # the second hop, which Arcade handles internally after token
    # exchange. The MCP client only ever requests scopes from the first
    # hop; advertising provider scopes here would be rejected as
    # ``invalid_scope`` by the intermediate AS.
    #
    # Arcade's AS publishes its vocabulary at the RFC 8414 path-suffixed
    # metadata URL. To verify or discover scopes for a different AS:
    #
    #   curl https://cloud.arcade.dev/.well-known/oauth-authorization-server/oauth2 \
    #     | jq .scopes_supported
    #
    # Returns: ["mcp", "offline_access"]
    #   - ``mcp``            resource access for the MCP server
    #   - ``offline_access`` request a refresh token (avoid re-auth
    #                        mid-session)
    scopes_supported=["mcp", "offline_access"],
    default_challenge_scopes=["mcp", "offline_access"],
    #
    # Alternative A: Challenge for an unadvertised scope.
    # PRM advertises only the baseline; the entry-401 challenge asks the
    # client for an additional scope ("vendor:write") that operators do
    # NOT want surfaced in PRM (e.g., gated rollout, internal-only).
    # Spec-permitted: "scopes included in the WWW-Authenticate challenge
    # MAY ... be an alternative collection that is neither a strict
    # subset nor superset" of scopes_supported.
    #
    # scopes_supported=["mcp"],
    # default_challenge_scopes=["mcp", "vendor:write"],
    #
    # Alternative B: Eager-grant tradeoff.
    # The entry-401 challenge advertises the full server-wide scope
    # superset, so the client acquires every scope on the entry token
    # without 403 step-ups. Spec-permitted (the challenge MAY be a
    # superset of PRM), but counter to the MCP security best practices
    # Scope Minimization guidance ("emit precise scope challenges; avoid
    # returning the full catalog"). Prefer the recommended baseline
    # above unless the client-side step-up handling is incomplete.
    #
    # scopes_supported=["mcp"],
    # default_challenge_scopes=["mcp", "offline_access", "vendor:write"],
)

# Option 1 (alternative): WorkOS Authkit instead of Arcade's intermediate AS
# resource_server_auth = ResourceServerAuth(
#     canonical_url=_canonical_url,
#     authorization_servers=[
#         AuthorizationServerEntry(  # WorkOS Authkit example configuration
#             authorization_server_url="https://your-workos.authkit.app",
#             issuer="https://your-workos.authkit.app",
#             jwks_uri="https://your-workos.authkit.app/oauth2/jwks",
#             expected_audiences=["your-authkit-client-id"],  # Override expected aud claim
#         ),
#     ],
# )

# Option 2: Multiple authorization servers with different keys (e.g., multi-IdP)
# resource_server_auth = ResourceServerAuth(
#     canonical_url=_canonical_url,
#     authorization_servers=[
#         AuthorizationServerEntry(  # Arcade intermediate AS configuration
#             authorization_server_url="https://cloud.arcade.dev/oauth2",
#             issuer="https://cloud.arcade.dev/oauth2",
#             jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
#             algorithm="Ed25519",
#             expected_audiences=["urn:arcade:mcp", _canonical_url],
#         ),
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
#     "authorization_server_url": "https://cloud.arcade.dev/oauth2",
#     "issuer": "https://cloud.arcade.dev/oauth2",
#     "jwks_uri": "https://cloud.arcade.dev/.well-known/jwks/oauth2",
#     "algorithm": "Ed25519",
#     "expected_audiences": ["urn:arcade:mcp", "http://127.0.0.1:8000/mcp"]
#   }
# ]'
# ```
# Or, equivalently, with WorkOS Authkit:
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
