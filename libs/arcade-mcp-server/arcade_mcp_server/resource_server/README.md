# MCP Resource Server Authentication

OAuth 2.1-compliant Resource Server authentication for securing HTTP-based MCP servers.

## Overview

The MCP server acts as an OAuth 2.1 **Resource Server**, validating Bearer tokens on **every HTTP request** before processing MCP protocol messages. This enables:

1. **Secure HTTP Transport** - Protect your MCP server with OAuth 2.1
2. **Tool-Level Authorization** - Enable tools requiring end-user OAuth on HTTP transport
3. **OAuth Discovery** - MCP clients automatically discover authentication requirements via RFC 9728
4. **User Context** - Tools receive authenticated resource owner identity from the Authorization Server

MCP servers can accept tokens from one or more authorization servers. Accepting tokens from multiple authorization servers supports scenarios like regional endpoints, multiple identity providers, or migrating between auth systems.

**Note:** The MCP server (Resource Server) doesn't need to know whether authorization servers support Dynamic Client Registration (DCR) or not. That's the authorization server's concern. The MCP server simply validates tokens and advertises the AS URLs.

## Environment Variable Configuration

`ResourceServer` supports environment variable configuration for production deployments. This is the **recommended approach for production**.

**Note:** `JWKSTokenValidator` does not support environment variables and requires explicit parameters.

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
- `validation_options`: (Optional) dict with optional `verify_aud`, `verify_exp`, `verify_iat`, `verify_iss` flags. Defaults to all flags being True

### Precedence Rules

**Environment variables take precedence over parameters:**

```python
from arcade_mcp_server import MCPApp
from arcade_mcp_server.resource_server import (
    AccessTokenValidationOptions,
    AuthorizationServerEntry,
    ResourceServer,
)

# Parameters are ignored if env vars are set
resource_server = ResourceServer(
    canonical_url="http://127.0.0.1:8000/mcp",  # overridden by env var
    authorization_servers=[  # overridden by env var
        AuthorizationServerEntry(
            authorization_server_url="https://your-workos.authkit.app",
            issuer="https://your-workos.authkit.app",
            jwks_uri="https://your-workos.authkit.app/oauth2/jwks",
            algorithm="RS256",
            validation_options=AccessTokenValidationOptions(
                verify_aud=False,
            ),
        )
    ],
)
app = MCPApp(name="Protected", auth=resource_server)
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
    "algorithm": "RS256",
    "validation_options": {
      "verify_aud": false
    }
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
    "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
    "validation_options": {
      "verify_aud": false
    }
  },
  {
    "authorization_server_url": "https://auth-eu.example.com",
    "issuer": "https://auth.example.com",
    "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
    "validation_options": {
      "verify_aud": false
    }
  }
]'
```

#### Multiple Authorization Servers (Different Keys)

```bash
# Multi-IdP configuration
MCP_RESOURCE_SERVER_CANONICAL_URL=https://mcp.example.com/mcp
MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS='[
  {
    "authorization_server_url": "https://workos.authkit.app",
    "issuer": "https://workos.authkit.app",
    "jwks_uri": "https://workos.authkit.app/oauth2/jwks",
    "validation_options": {
      "verify_aud": false
    }
  },
  {
    "authorization_server_url": "http://localhost:8080/realms/mcp-test",
    "issuer": "http://localhost:8080/realms/mcp-test",
    "jwks_uri": "http://localhost:8080/realms/mcp-test/protocol/openid-connect/certs",
    "validation_options": {
      "verify_aud": false
    }
  }
]'
```

### How It Works

1. **Resource Server validates tokens** - Extracts user identity from validated token's `sub` claim
2. **User ID flows to ToolContext** - Used for tool-level OAuth via Arcade platform
3. **Transport restriction lifted** - HTTP is now safe for tools requiring auth/secrets
4. **Separate authorization layers** - Resource Server auth != tool OAuth (but enables it)

## Vendor-Specific Implementations

The `ResourceServer` class is designed to be subclassed for vendor-specific implementations:

```python
# Future vendor-specific implementations
class ArcadeResourceServer(ResourceServer): ...
class WorkOSResourceServer(ResourceServer): ...
class Auth0ResourceServer(ResourceServer): ...
class DescopeResourceServer(ResourceServer): ...
```
