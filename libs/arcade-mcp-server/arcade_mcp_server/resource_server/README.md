# MCP Resource Server Authentication

OAuth 2.1-compliant Resource Server authentication for securing HTTP-based MCP servers.

## Overview

The MCP server acts as an OAuth 2.1 **Resource Server**, validating Bearer tokens on **every HTTP request** before processing MCP protocol messages. This enables:

1. **Secure HTTP Transport** - Protect your MCP server with OAuth 2.1
2. **Tool-Level Authorization** - Enable tools requiring end-user OAuth on HTTP transport
3. **OAuth Discovery** - MCP clients automatically discover authentication requirements via OAuth Protected Resource Metadata (RFC 9728)
4. **User Context** - Tools receive authenticated resource owner identity from the Authorization Server

MCP servers can accept tokens from one or more authorization servers. Accepting tokens from multiple authorization servers supports scenarios like regional endpoints, multiple identity providers, or migrating between auth systems.

**Note:** The MCP server (Resource Server) doesn't need to know how MCP clients are registered with the Authorization Server (for example, Dynamic Client Registration, static client secrets, etc.) - that's the authorization server's concern. The MCP server simply validates tokens and advertises the AS URLs.

## Environment Variable Configuration

`ResourceServerAuth` supports environment variable configuration for production deployments. This is the **recommended approach for production**.

**Note:** `JWKSTokenValidator` does not support environment variables and requires explicit programmatic parameters to its initializer

### Supported Environment Variables

| Environment Variable | Type | Description | Required |
|---------------------|------|-------------|----------|
| `MCP_RESOURCE_SERVER_CANONICAL_URL` | string | MCP server canonical URL | Yes |
| `MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS` | JSON array | Authorization server entries | Yes |

The `MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS` must be a JSON array of entry objects. Each object should include:
- `authorization_server_url`: Authorization server URL
- `issuer`: Expected token issuer
- `jwks_uri`: JWKS endpoint URL
- `algorithm`: (Optional) JWT algorithm, defaults to RS256
- `expected_audiences`: (Optional) list of expected audience claim values. If not provided, defaults to the canonical_url. Use this when your auth server returns a different aud claim (e.g., client_id).
- `validation_options`: (Optional) dict with optional `verify_exp`, `verify_iat`, `verify_iss`, `verify_nbf`, and `leeway` (int, seconds). All verify flags default to True.

### Precedence Rules

**Explicit parameters take precedence over environment variables:**

```python
from arcade_mcp_server import MCPApp
from arcade_mcp_server.resource_server import (
    AuthorizationServerEntry,
    ResourceServerAuth,
)

# Explicit parameters override env vars (if both are provided)
resource_server_auth = ResourceServerAuth(
    canonical_url="http://127.0.0.1:8000/mcp",  # used even if env var is set
    authorization_servers=[  # used even if env var is set
        AuthorizationServerEntry(
            authorization_server_url="https://your-workos.authkit.app",
            issuer="https://your-workos.authkit.app",
            jwks_uri="https://your-workos.authkit.app/oauth2/jwks",
            algorithm="RS256",
            # Override expected aud if auth server returns different audience (e.g., client_id)
            expected_audiences=["my-authkit-client-id"],
        )
    ],
)
app = MCPApp(name="Protected", auth=resource_server_auth)

# If no parameters provided, env vars are used as fallback
resource_server_auth = ResourceServerAuth()  # Uses MCP_RESOURCE_SERVER_* env vars
```

### Example .env File

#### Single Authorization Server

```bash
# Resource Server Configuration
MCP_RESOURCE_SERVER_CANONICAL_URL=https://mcp.example.com/mcp
MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS='[
  {
    "authorization_server_url": "https://auth.example.com",
    "issuer": "https://auth.example.com",
    "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
    "algorithm": "RS256"
  }
]'
```

#### Single Authorization Server (Custom Audience)

When your auth server returns a different `aud` claim (e.g., client_id instead of canonical URL):

```bash
MCP_RESOURCE_SERVER_CANONICAL_URL=https://mcp.example.com/mcp
MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS='[
  {
    "authorization_server_url": "https://auth.example.com",
    "issuer": "https://auth.example.com",
    "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
    "algorithm": "RS256",
    "expected_audiences": ["my-client-id"]
  }
]'
```

#### Multiple Authorization Servers (Shared Keys)

```bash
# Regional endpoints with shared keys
MCP_RESOURCE_SERVER_CANONICAL_URL=https://mcp.example.com/mcp
MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS='[
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
# Multi-IdP configuration with custom audiences
MCP_RESOURCE_SERVER_CANONICAL_URL=https://mcp.example.com/mcp
MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS='[
  {
    "authorization_server_url": "https://workos.authkit.app",
    "issuer": "https://workos.authkit.app",
    "jwks_uri": "https://workos.authkit.app/oauth2/jwks",
    "expected_audiences": ["my-workos-client-id"]
  },
  {
    "authorization_server_url": "http://localhost:8080/realms/mcp-test",
    "issuer": "http://localhost:8080/realms/mcp-test",
    "jwks_uri": "http://localhost:8080/realms/mcp-test/protocol/openid-connect/certs",
    "expected_audiences": ["my-keycloak-client-id"]
  }
]'
```

### How It Works

1. **Resource Server validates tokens** - Extracts user identity from validated token's `sub` claim
2. **User ID flows to ToolContext** - Used for tool-level OAuth via Arcade platform
3. **Transport restriction lifted** - HTTP is now safe for tools requiring auth/secrets
4. **Separate authorization layers** - Resource Server auth != tool OAuth (but building a protected server enables tool authorization)

## Vendor-Specific Implementations

The `ResourceServerAuth` class is designed to be subclassed for vendor-specific implementations:

```python
# Your vendor-specific implementations
class ArcadeResourceServerAuth(ResourceServerAuth): ...
class WorkOSResourceServerAuth(ResourceServerAuth): ...
class Auth0ResourceServerAuth(ResourceServerAuth): ...
class DescopeResourceServerAuth(ResourceServerAuth): ...
```
