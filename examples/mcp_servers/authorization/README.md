# authorization

Demonstrates **OAuth 2.1 Resource Server Auth** for an MCP server running on
the HTTP transport, one of the two tracks through which 2025-11-25 protects
`/mcp/*` endpoints (the other being the Arcade-managed deploy path).

This is **server-level (front-door) auth**: every HTTP request to `/mcp/*`
must carry a valid Bearer token issued by one of the configured authorization
servers. The Bearer token authenticates the *caller* to the MCP server.

It is independent of **tool-level** auth, e.g.
`@app.tool(requires_auth=Reddit(scopes=["read"]))` or
`@app.tool(requires_secrets=[...])`. Tool-level auth is a separate runtime
concern handled by the tool execution layer when a tool actually runs (the
provider OAuth flow, secret resolution, etc.). This example does not
configure or demonstrate tool-level auth, only the server-level Bearer
token check at the front door.

## What this example shows

- `ResourceServerAuth(canonical_url=..., authorization_servers=[...])`
  the single entry point for configuring front-door token validation.
- `AuthorizationServerEntry(...)` per-IdP configuration: JWKS URL,
  issuer, expected audience, signing algorithm.
- Multi-IdP mode: pass multiple `AuthorizationServerEntry` objects to
  trust several authorization servers at once. Useful for multi-tenant
  servers or migration windows.
- Two scope surfaces (PRM `scopes_supported` and entry-401 `scope=`)
  configured independently, with documented commented alternatives in
  `server.py` for the unadvertised-challenge and eager-grant patterns.
- Env-var configuration: all of the above can be read from
  `MCP_RESOURCE_SERVER_CANONICAL_URL`,
  `MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS`,
  `MCP_RESOURCE_SERVER_SCOPES_SUPPORTED`, and
  `MCP_RESOURCE_SERVER_DEFAULT_CHALLENGE_SCOPES`.

## Two scope surfaces: PRM vs WWW-Authenticate

The MCP 2025-11-25 spec (driven by SEP-835) treats two scope surfaces as
**independent**:

- **PRM `scopes_supported`** (RFC 9728): discoverable advertisement, the
  *minimum baseline* for basic functionality.
- **`WWW-Authenticate: scope=`** (RFC 6750): what the server is challenging
  the client to acquire RIGHT NOW.

The spec explicitly permits the entry-401 challenge to be a subset, superset,
or alternative collection of PRM. Behavior matrix:

| `scopes_supported` | `default_challenge_scopes` | PRM `scopes_supported` | Entry-401 `scope=` | Use case |
|---|---|---|---|---|
| `None` | `None` | omitted | omitted | Greenfield / no scope guidance. |
| `["files:read"]` | `None` | `["files:read"]` | omitted | "Document but don't challenge"; client falls back to PRM per spec selection strategy. |
| `["files:read"]` | `["files:read"]` | `["files:read"]` | `scope="files:read"` | **Recommended baseline.** Both surfaces advertise the minimum scope set required for entry. Tools that need additional scopes raise `InsufficientScopeError` at dispatch time, producing a 403 step-up challenge. Aligns with MCP security best practices (Scope Minimization). |
| `None` | `["files:read"]` | omitted | `scope="files:read"` | Challenge for an unadvertised scope (gated rollout, internal-only). Spec-permitted alternative collection. |
| `["files:read"]` | `["files:read", "files:write"]` | `["files:read"]` | `scope="files:read files:write"` | **Eager-grant tradeoff.** Operators accept a broader entry-token grant in exchange for fewer 403 step-up roundtrips. Spec-permitted but counter to Scope Minimization; prefer the recommended baseline unless client-side step-up handling is incomplete. |

## Step-up authorization (403 insufficient_scope)

When a tool requires a scope beyond the entry-token grant, raise
`InsufficientScopeError(["files:write"])` from the tool body (or use the
`enforce_scopes(scope, required)` helper from a custom Starlette route).
The middleware catches the exception and emits an RFC 6750 403 with a
`WWW-Authenticate` header advertising the operation-required scopes:

```http
HTTP/1.1 403 Forbidden
WWW-Authenticate: Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource/mcp", error="insufficient_scope", scope="files:write"
```

Sample step-up flow:

1. Client lands on entry-401 with the configured baseline scopes.
2. Client exchanges for a `files:read` token.
3. Client calls a write-scoped tool, gets a 403 with `scope="files:write"`.
4. Client re-exchanges for a token carrying the elevated scope.
5. Client retries the call, succeeds.

The 403 emit follows the spec-permitted "minimum approach" (operation-
required scopes only). `granted_scopes` on the exception is diagnostic-only
and never echoed to the wire.

## Canonical URL scheme: HTTPS with loopback exception

`ResourceServerAuth(canonical_url=...)` and the
`MCP_RESOURCE_SERVER_CANONICAL_URL` env var validate the URL at intake
against four layers:

1. RFC 6750 `error-char` grammar (no DQUOTE / backslash / CR / LF / CTLs /
   non-ASCII).
2. RFC 3986 URI structure with the RFC 9728 `https`-only scheme rule, plus
   a documented loopback exception. RFC 8252 Section 7.3 and OAuth 2.1
   draft Section 8.4.2 enumerate the loopback redirect URIs as
   `http://127.0.0.1` and `http://[::1]`; mainstream OAuth toolkits accept
   `localhost` as well via OS convention. So the loopback set is exactly:
   - `127.0.0.1`
   - `::1`
   - `localhost`
3. RFC 3986 character correctness (no unencoded whitespace, no malformed
   percent-escapes).
4. The MCP canonical-URI rule: no fragment component (RFC 8707 Section 2).

The example's default `http://127.0.0.1:8000/mcp` keeps working because
of the loopback carve-out. Production canonical URLs MUST be HTTPS per
RFC 9728. Deliberately excluded from the loopback set: `0.0.0.0`
(binds-all is not loopback), RFC 1918 private IPs, and mDNS `*.local`
names. For LAN testing use HTTPS via `mkcert` or a TLS-terminating
proxy.

## Running

```bash
uv sync
uv run python src/authorization/server.py
```

See [`docker/README.md`](docker/README.md) for the Docker variant.

## OAuth Protected Resource Metadata discovery (RFC 9728)

`ResourceServerAuth` automatically serves the Protected Resource Metadata
document at the RFC 9728-conformant path
(`/.well-known/oauth-protected-resource`), so any 2025-11-25 MCP client can
discover the accepted authorization servers without out-of-band config.

Inspect the metadata:

```bash
curl http://127.0.0.1:8000/.well-known/oauth-protected-resource | jq
```

```jsonc
{
  "resource": "http://127.0.0.1:8000/mcp",
  "authorization_servers": [
    "https://your-workos.authkit.app"
  ],
  "bearer_methods_supported": ["header"],
  "scopes_supported": ["..."]
}
```

A 2025-11-25 client fetches this document first, reads the
`authorization_servers` list, then initiates its own OAuth flow against the
listed authorization server.

## Multi-IdP support

The commented "Option 2" block in `server.py` shows how to configure
multiple `AuthorizationServerEntry` objects. Each incoming token is
validated against every entry and accepted if any match, so a single server
can accept tokens from (say) WorkOS *and* Keycloak during a migration
window.
