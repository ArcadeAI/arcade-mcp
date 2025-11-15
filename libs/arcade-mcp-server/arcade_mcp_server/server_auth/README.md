# Front-Door Authentication for Arcade MCP Server

OAuth 2.1-compliant front-door authentication for securing HTTP-based MCP servers.

## Overview

Front-door authentication validates Bearer tokens on **every HTTP request** before processing MCP protocol messages. This enables:

1. **Secure HTTP Transport** - Protect your MCP server with OAuth 2.1
2. **Tool-Level Authorization** - Enable tools requiring end-user OAuth on HTTP transport
3. **OAuth Discovery** - MCP clients automatically discover authentication requirements
4. **User Context** - Tools receive authenticated user identity for personalization

## Quick Start

### Basic JWT Verification

```python
from arcade_mcp_server import MCPApp, JWTVerifier

auth = JWTVerifier(
    jwks_uri="https://auth.example.com/.well-known/jwks.json",
    issuer="https://auth.example.com",
    audience="https://mcp.example.com",  # Your server's canonical URL
)

app = MCPApp(
    name="my_server",
    auth=auth,
    canonical_url="https://mcp.example.com",
)
```

### WorkOS AuthKit (Recommended)

```python
from arcade_mcp_server import MCPApp
from arcade_mcp_server.server_auth.providers.authkit import AuthKitProvider

auth = AuthKitProvider(
    authkit_domain="https://your-app.authkit.app",
    canonical_url="https://mcp.example.com",
)

app = MCPApp(
    name="my_server",
    auth=auth,
)
```

### Generic OAuth Provider

```python
from arcade_mcp_server import MCPApp, RemoteOAuthProvider

auth = RemoteOAuthProvider(
    jwks_uri="https://auth.example.com/.well-known/jwks.json",
    issuer="https://auth.example.com",
    canonical_url="https://mcp.example.com",
    authorization_server="https://auth.example.com",
)

app = MCPApp(
    name="my_server",
    auth=auth,
)
```

## Authentication Providers

### JWTVerifier

**Use when:** You have an existing JWT-based auth system and just need token validation.

**Features:**
- JWT signature verification
- Expiration checking
- Issuer validation
- **Audience validation (critical security feature)**
- JWKS caching (1-hour TTL)

**Does NOT provide:**
- OAuth discovery endpoints
- MCP client auto-discovery

**Configuration:**

```python
JWTVerifier(
    jwks_uri="https://auth.example.com/.well-known/jwks.json",
    issuer="https://auth.example.com",
    audience="https://mcp.example.com",
    algorithms=["RS256"],  # Optional, defaults to ["RS256"]
    cache_ttl=3600,  # Optional, JWKS cache TTL in seconds
)
```

### RemoteOAuthProvider

**Use when:** Integrating with external identity providers that support Dynamic Client Registration.

**Features:**
- Everything in JWTVerifier
- OAuth 2.0 Protected Resource Metadata (RFC 9728)
- Points clients to external authorization server
- Enables MCP client auto-discovery

**Providers with DCR support:**
- WorkOS (use AuthKitProvider instead)
- Descope
- Auth0 (with proper configuration)
- Custom OAuth servers with DCR

**Configuration:**

```python
RemoteOAuthProvider(
    jwks_uri="https://auth.example.com/.well-known/jwks.json",
    issuer="https://auth.example.com",
    canonical_url="https://mcp.example.com",
    authorization_server="https://auth.example.com",
    algorithms=["RS256"],  # Optional
    cache_ttl=3600,  # Optional
)
```

### AuthKitProvider

**Use when:** Using WorkOS AuthKit as your identity provider (recommended for production).

**Features:**
- Everything in RemoteOAuthProvider
- Automatic JWT configuration for AuthKit
- Authorization server metadata forwarding
- Native DCR support
- Simple setup (just domain + canonical URL)

**Configuration:**

```python
AuthKitProvider(
    authkit_domain="https://your-app.authkit.app",
    canonical_url="https://mcp.example.com",
    cache_ttl=3600,  # Optional
)
```

**Setup requirements:**
1. Enable Dynamic Client Registration in WorkOS dashboard
2. Add your MCP server URL to redirect URIs in WorkOS

**Note on Audience Validation:**

WorkOS AuthKit does not implement RFC 8707 (Resource Indicators) by default, so tokens don't include an audience (`aud`) claim. The AuthKitProvider disables audience validation and relies on issuer validation and signature verification instead. This is appropriate for AuthKit's architecture where tokens are scoped to the AuthKit domain rather than individual resources.

## How It Works

### Token Validation Flow

```
HTTP Request with "Authorization: Bearer <token>"
  ↓
ASGI Auth Middleware
  ↓ Extract token from header
  ↓ Validate on THIS request (no caching)
  ↓   - Verify signature (JWKS)
  ↓   - Check expiration
  ↓   - Validate issuer
  ↓   - Validate audience (critical!)
  ↓ Store AuthenticatedUser in scope
  ↓
HTTPStreamableTransport
  ↓ Extract authenticated_user from scope
  ↓ Create SessionMessage(message, authenticated_user)
  ↓
ServerSession
  ↓ Extract from SessionMessage
  ↓ Store for THIS request only
  ↓ Create Context with authenticated_user
  ↓ Process MCP request
  ↓ Clear authenticated_user after response
```

### OAuth Discovery Flow

When a provider supports OAuth discovery (RemoteOAuthProvider, AuthKitProvider):

1. **Client Discovery:**
   ```
   Client: GET /mcp (no auth)
   Server: 401 Unauthorized
           WWW-Authenticate: Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"
   ```

2. **Resource Metadata:**
   ```
   Client: GET /.well-known/oauth-protected-resource
   Server: {
             "resource": "https://mcp.example.com",
             "authorization_servers": ["https://auth.example.com"]
           }
   ```

3. **Authorization Server Metadata:**
   ```
   Client: GET /.well-known/oauth-authorization-server
   Server: { ... OAuth endpoints ... }
   ```

4. **Client performs OAuth flow, obtains token, makes authenticated requests**

## Security Guarantees

### MCP Specification Compliance

✅ **Token validated on every request** - No session caching (prevents session hijacking)
✅ **Audience claim validation** - Prevents cross-service token reuse
✅ **WWW-Authenticate header** - RFC 6750 + RFC 9728 compliant
✅ **Error responses** - Include error and error_description
✅ **Well-known endpoints** - Served at server root
✅ **Canonical URL** - Explicitly configured, not inferred
✅ **PKCE required** - Client responsibility (MCP spec requirement)
✅ **HTTPS required** - Production deployment requirement

### Token Validation

Every token is validated for:

1. **Signature** - Verified against JWKS public keys
2. **Expiration** - `exp` claim checked
3. **Issuer** - `iss` claim must match expected authorization server
4. **Audience** - `aud` claim must match this MCP server's canonical URL
5. **Subject** - `sub` claim must exist (becomes user_id)

### No Session-Based Auth

Per MCP specification security requirements:

> "MCP Servers MUST NOT use sessions for authentication."

Our implementation:
- Validates token on **every HTTP request**
- Does NOT cache validation results
- Stores authenticated user **only for the current request**
- Clears authenticated user after response

## Tool Authorization Integration

Front-door authentication enables tool-level authorization on HTTP transport:

### Before Front-Door Auth

```python
@app.tool(authorization=ToolAuthorization(...))
async def github_tool() -> str:
    """Blocked on HTTP transport - requires authenticated transport"""
    pass
```

Result: `Tool cannot be executed over unauthenticated HTTP transport`

### After Front-Door Auth

```python
auth = AuthKitProvider(...)
app = MCPApp(auth=auth, canonical_url="...")

@app.tool(authorization=ToolAuthorization(...))
async def github_tool(ctx) -> str:
    """Allowed on HTTP - user identity available"""
    user_id = ctx.user_id  # From front-door auth token
    # Tool can now safely request user's GitHub authorization
    return "Success"
```

Result: ✅ Tool executes successfully

### How It Works

1. **Front-door auth provides user identity** - Extracted from validated token's `sub` claim
2. **User ID flows to ToolContext** - Used for tool-level OAuth via Arcade platform
3. **Transport restriction lifted** - HTTP is now safe for tools requiring auth/secrets
4. **Separate authorization layers** - Front-door auth ≠ tool OAuth (but enables it)

## Context Access

Authenticated user information is available in tool contexts:

```python
from arcade_mcp_server import Context, tool

@tool
async def my_tool(ctx: Context) -> str:
    # Server-level authenticated user (from front-door auth)
    if ctx.authenticated_user:
        user_id = ctx.authenticated_user.user_id
        email = ctx.authenticated_user.email
        claims = ctx.authenticated_user.claims

        return f"Authenticated as: {email}"

    return "Not authenticated"
```

## Configuration

### Programmatic Configuration

```python
from arcade_mcp_server import MCPApp
from arcade_mcp_server.server_auth.providers.authkit import AuthKitProvider

auth = AuthKitProvider(
    authkit_domain="https://your-app.authkit.app",
    canonical_url="https://mcp.example.com",
)

app = MCPApp(
    name="my_server",
    auth=auth,
    canonical_url="https://mcp.example.com",
)
```

### Settings-Based Configuration

Configure via MCPSettings:

```python
from arcade_mcp_server import MCPSettings

settings = MCPSettings()
settings.server_auth.enabled = True
settings.server_auth.canonical_url = "https://mcp.example.com"
```

## Testing

Run the included test suite:

```bash
pytest libs/tests/arcade_mcp_server/test_server_auth.py -v
```

Tests cover:
- Valid token validation
- Expired token rejection
- Wrong audience rejection (critical security test)
- Wrong issuer rejection
- Missing claims handling
- JWKS caching behavior
- WWW-Authenticate header format compliance
- OAuth discovery metadata format
- AuthKit automatic configuration

## Examples

See the `examples/mcp_servers/` directory:

- `server_with_auth/` - Generic OAuth provider example
- `server_with_authkit/` - WorkOS AuthKit example (recommended)

## Troubleshooting

### 401 Unauthorized with Valid Token

**Check audience claim:**
```python
# Token's 'aud' claim must match canonical_url
import jwt
decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded["aud"])  # Should match your canonical_url
```

**Check issuer:**
```python
print(decoded["iss"])  # Should match your auth provider's issuer
```

**Check expiration:**
```python
import time
print(decoded["exp"] > time.time())  # Should be True
```

### Tools Still Blocked on HTTP

**Verify authentication is working:**
```bash
# Should return 401
curl http://localhost:8000/mcp

# Should work with token
curl -H "Authorization: Bearer <token>" http://localhost:8000/mcp
```

**Check server logs:**
```
# Should see:
Context user_id set from front-door auth: user123
```

### OAuth Discovery Not Working

**Verify endpoints are accessible:**
```bash
curl http://localhost:8000/.well-known/oauth-protected-resource
curl http://localhost:8000/.well-known/oauth-authorization-server
```

**Check provider configuration:**
```python
# Provider must support discovery
assert auth.supports_oauth_discovery() is True
```

## Architecture Notes

### Why ASGI Middleware?

The authentication logic is implemented as ASGI middleware (not FastAPI middleware or transport-level logic) because:

1. **Framework-agnostic** - Works with any ASGI application
2. **Clean separation** - Auth is orthogonal to MCP protocol
3. **Early validation** - Tokens validated before any MCP processing
4. **Easy testing** - Middleware can be tested independently
5. **Standard pattern** - Well-understood ASGI pattern

### Why Per-Request Validation?

The MCP specification requires:

> "Authorization MUST be included in every HTTP request from client to server, even if they are part of the same logical session."

Benefits:
- Tokens can be revoked immediately (no stale sessions)
- Expiration checked on each request
- Prevents session hijacking attacks
- Aligns with OAuth 2.1 best practices

For JWT tokens, validation is fast (cryptographic signature check). For opaque tokens, consider adding a caching layer with short TTL (future enhancement).

### Why Separate from Tool Auth?

**Front-door auth** (this module):
- "Who can access this MCP server?"
- OAuth 2.1 Resource Server role
- Validates Bearer tokens
- Provides user identity

**Tool-level auth** (Arcade platform):
- "Does this user have GitHub OAuth connected?"
- End-user authorization for third-party APIs
- Managed by Arcade Engine
- Uses front-door auth's user_id

Both layers work together:
```
Front-door auth → Provides user_id → Tool auth uses user_id → Arcade Engine handles OAuth flow
```

## Future Enhancements

The following features are planned but not yet implemented:

- **OAuth Proxy** - Support for providers without DCR (GitHub, Google, Azure)
- **Opaque Token Support** - Token introspection via RFC 7662
- **Scope-Based Authorization** - Fine-grained access control
- **Environment-Based Config** - Configure providers via env vars
- **Per-User Rate Limiting** - Rate limits based on authenticated user
- **Audit Logging** - Detailed logging of authenticated requests
- **Multi-Auth Server Support** - Multiple authorization servers per resource

## References

- [MCP Authorization Specification](../../authorization/authorization.md)
- [OAuth 2.1 Draft](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1)
- [RFC 9728 - Protected Resource Metadata](https://www.rfc-editor.org/rfc/rfc9728.html)
- [RFC 8707 - Resource Indicators](https://www.rfc-editor.org/rfc/rfc8707.html)
- [RFC 7591 - Dynamic Client Registration](https://www.rfc-editor.org/rfc/rfc7591.html)
- [WorkOS AuthKit Documentation](https://workos.com/docs/authkit)
