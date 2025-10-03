# 07 - OAuth Tools

Learn how to create tools that require OAuth

## Prerequisites

Before running this example, you need to authenticate with Arcade:

```bash
# Install the Arcade CLI (if not already installed)
uv pip install arcade-mcp

# Login to Arcade
arcade login
```

## Running the Example

- **Run HTTP**: `uv run examples/07_auth.py`
- **Run stdio**: `uv run examples/07_auth.py stdio`

## Source Code

```python
--8<-- "docs/examples/07_auth.py"
```

## OAuth Authentication Features

### 1. Requiring Authentication

Use the `requires_auth` parameter with an auth provider to require OAuth:

```python
from arcade_mcp_server.auth import Reddit

@app.tool(requires_auth=Reddit(scopes=["read"]))
async def get_posts_in_subreddit(
    context: Context,
    subreddit: Annotated[str, "The name of the subreddit"]
) -> dict:
    """Get posts from a specific subreddit."""
    # OAuth token is automatically injected into context
    oauth_token = context.get_auth_token_or_empty()
    # Use the token to make authenticated API requests
```

### 2. Specifying OAuth Scopes

Different tools may require different scopes:

```python
# Read-only access
@app.tool(requires_auth=Reddit(scopes=["read"]))
async def read_only_tool(context: Context) -> dict:
    """Tool that only reads data."""
    pass

# Multiple scopes for more permissions
@app.tool(requires_auth=Reddit(scopes=["read", "identity"]))
async def identity_tool(context: Context) -> dict:
    """Tool that accesses user identity."""
    pass
```

### 3. Accessing OAuth Tokens

OAuth tokens are securely injected into the context at runtime:

```python
# Get the token (returns empty string if not authenticated)
oauth_token = context.get_auth_token_or_empty()

# Use token in API requests
headers = {
    "Authorization": f"Bearer {oauth_token}",
    "User-Agent": "my-app",
}
```

### 4. Making Authenticated API Requests

Use the OAuth token with httpx or other HTTP clients:

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://oauth.reddit.com/api/endpoint",
        headers={"Authorization": f"Bearer {oauth_token}"}
    )
    response.raise_for_status()
    return response.json()
```

## Available Auth Providers

The `arcade_mcp_server.auth` module provides several OAuth providers:

## Authentication Flow

1. **User runs `arcade login`**: Authenticates with Arcade and stores credentials
2. **Tool is called**: MCP client calls a tool that requires authentication
3. **Authorization Required**: If the user has not authorized the required scopes, then they are prompted to go through an OAuth flow
3. **Token injection**: Arcade injects the OAuth token into the tool's context
4. **API request**: Tool uses the token to make authenticated API requests
5. **Response**: Tool returns data to the MCP client

The LLM and MCP clients never see the OAuth tokens - they are securely injected server-side.

## Security Best Practices

1. **Never log tokens**: OAuth tokens should never be logged or exposed
2. **Use appropriate scopes**: Request only the scopes your tool actually needs

## Key Concepts

- **OAuth Integration**: Arcade handles OAuth flows and token management
- **Secure Token Injection**: Tokens are injected into context at runtime
- **Scope Management**: Specify exactly which permissions your tool needs
- **Provider Support**: Multiple OAuth providers available out of the box
- **User Privacy**: LLMs and MCP clients never see OAuth tokens
