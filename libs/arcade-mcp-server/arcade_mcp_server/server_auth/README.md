# Front-Door Authentication for Arcade MCP Server

OAuth 2.1-compliant front-door authentication for securing HTTP-based MCP servers.

## Overview

Front-door auth validates Bearer tokens on **every HTTP request** before processing MCP protocol messages. This enables:

1. **Secure HTTP Transport** - Protect your MCP server with OAuth 2.1
2. **Tool-Level Authorization** - Enable tools requiring end-user OAuth on HTTP transport
3. **OAuth Discovery** - MCP clients automatically discover authentication requirements
4. **User Context** - Tools receive authenticated user identity from the Auth Server for personalization


MCP servers can accept tokens from one or more authorization servers. Accepting tokens from more than one authorization servers supports scenarios like regional endpoints, multiple identity providers, or migrating between auth systems.

**Note:** The MCP server (Resource Server) doesn't need to know whether authorization servers support Dynamic Client Registration (DCR) or not. That's the authorization server's concern. The MCP server simply validates tokens and advertises the AS URLs.

## Environment Variable Configuration

`RemoteOAuthProvider` supports environment variable configuration for production deployments. This is the **recommended approach for production**.

**Note:** `JWTVerifier` does not support environment variables and requires explicit parameters.

### Supported Environment Variables

| Environment Variable | Type | Description | Required |
|---------------------|------|-------------|----------|
| `MCP_SERVER_AUTH_CANONICAL_URL` | string | MCP server canonical URL | Yes |
| `MCP_SERVER_AUTH_AUTHORIZATION_SERVERS` | JSON array | Authorization server configurations | Yes |

The `MCP_SERVER_AUTH_AUTHORIZATION_SERVERS` must be a JSON array of configuration objects. Each object should include:
- `authorization_server_url`: Authorization server URL
- `issuer`: Expected token issuer
- `jwks_uri`: JWKS endpoint URL
- `algorithm`: (Optional) JWT algorithm, defaults to RS256
- `verify_options`: (Optional) dict with optional `verify_aud`, `verify_exp`, `verify_iat`, `verify_iss` verification flags. Defaults to all flags being True

### Precedence Rules

**Environment variables take precedence over parameters:**

```python
from arcade_mcp_server import MCPApp
from arcade_mcp_server.server_auth import (
    AuthorizationServerConfig,
    JWTVerifyOptions,
    RemoteOAuthProvider,
)
# Parameters are ignored if env vars are set
auth = RemoteOAuthProvider(
    canonical_url="http://127.0.0.1:8000/mcp", # overridden by env var
    authorization_servers=[ # overriden by env var
        AuthorizationServerConfig(
            authorization_server_url="https://your-workos.authkit.app",
            issuer="https://your-workos.authkit.app",
            jwks_uri="https://your-workos.authkit.app/oauth2/jwks",
            algorithm="RS256",
            verify_options=JWTVerifyOptions(
                verify_aud=False,
            ),
        )
    ],
)
app = MCPApp(name="Protected", auth=auth)
```

### Example .env File

#### Single Authorization Server

```bash
# Auth Provider Configuration
MCP_SERVER_AUTH_CANONICAL_URL=https://mcp.example.com
MCP_SERVER_AUTH_AUTHORIZATION_SERVERS='[
  {
    "authorization_server_url": "https://auth.example.com",
    "issuer": "https://auth.example.com",
    "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
    "algorithm": "RS256"
  }
]'
```

#### Multiple Authorization Servers (Shared Keys)

```bash
# Regional endpoints with shared keys
MCP_SERVER_AUTH_CANONICAL_URL=https://mcp.example.com
MCP_SERVER_AUTH_AUTHORIZATION_SERVERS='[
  {
    "authorization_server_url": "https://auth-us.example.com",
    "issuer": "https://auth.example.com",
    "jwks_uri": "https://auth.example.com/.well-known/jwks.json"
  },
  {
    "authorization_server_url": "https://auth-eu.example.com",
    "issuer": "https://auth.example.com",
    "jwks_uri": "https://auth.example.com/.well-known/jwks.json"
  }
]'
```

#### Multiple Authorization Servers (Different Keys)

```bash
# Multi-IdP configuration
MCP_SERVER_AUTH_CANONICAL_URL=https://mcp.example.com
MCP_SERVER_AUTH_AUTHORIZATION_SERVERS='[
  {
    "authorization_server_url": "https://workos.authkit.app",
    "issuer": "https://workos.authkit.app",
    "jwks_uri": "https://workos.authkit.app/oauth2/jwks"
  },
  {
    "authorization_server_url": "https://github.com/login/oauth",
    "issuer": "https://github.com",
    "jwks_uri": "https://token.actions.githubusercontent.com/.well-known/jwks",
    "verify_aud": false
  }
]'
```

### How It Works

1. **Front-door auth provides user identity** - Extracted from validated token's `sub` claim
2. **User ID flows to ToolContext** - Used for tool-level OAuth via Arcade platform
3. **Transport restriction lifted** - HTTP is now safe for tools requiring auth/secrets
4. **Separate authorization layers** - Front-door auth != tool OAuth (but enables it)
