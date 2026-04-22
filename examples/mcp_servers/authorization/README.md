# authorization

Demonstrates **OAuth 2.1 Resource Server Auth** for an MCP server running on
the HTTP transport — one of the two tracks through which 2025-11-25 protects
`/mcp/*` endpoints (the other being the Arcade-managed deploy path).

## What this example shows

- `ResourceServerAuth(canonical_url=..., authorization_servers=[...])` —
  the single entry point for configuring front-door token validation.
- `AuthorizationServerEntry(...)` — per-IdP configuration: JWKS URL,
  issuer, expected audience, signing algorithm.
- Multi-IdP mode — pass multiple `AuthorizationServerEntry` objects to
  trust several authorization servers at once. Useful for multi-tenant
  servers or migration windows.
- Env-var configuration — all of the above can be read from
  `MCP_RESOURCE_SERVER_CANONICAL_URL` and
  `MCP_RESOURCE_SERVER_AUTHORIZATION_SERVERS`.

Tools on the server either require a secret (`@app.tool(requires_secrets=[...])`)
or require OAuth (`@app.tool(requires_auth=Reddit(scopes=[...]))`). On the
HTTP transport, both paths need the caller to present a valid Bearer token.

## Running

```bash
uv sync
uv run python src/authorization/server.py
```

See [`docker/README.md`](docker/README.md) for the Docker variant.

## MCP 2025-11-25 features this example already covers

### OAuth Protected Resource Metadata discovery (RFC 9728, SEP-985)

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

### Incremental scope consent (SEP-835)

When a caller presents a Bearer token with valid signature but insufficient
scope for the tool they're calling, the server returns:

```
HTTP/1.1 403 Forbidden
WWW-Authenticate: Bearer error="insufficient_scope",
                  scope="gmail.readonly calendar.write",
                  resource_metadata="http://127.0.0.1:8000/.well-known/oauth-protected-resource"
```

The JSON-RPC error also carries `code: -32010` with the required and
granted scopes in `error.data`, so the client can kick off a *targeted*
re-authorisation for just the missing scopes instead of repeating the full
initial consent flow.

See `MCPServer._handle_call_tool` (the "OAuth scope sufficiency check"
branch) for the server-side logic.

### Multi-IdP support

The commented "Option 2" block in `server.py` shows how to configure
multiple `AuthorizationServerEntry` objects. Each incoming token is
validated against every entry and accepted if any match, so a single server
can accept tokens from (say) WorkOS *and* Keycloak during a migration
window.

## What's NOT implemented here (but spec-adjacent)

- **OpenID Connect Discovery 1.0** (PR #797) — the spec now allows
  authorization servers to expose `.well-known/openid-configuration`. This
  repo doesn't fetch / honour OIDC discovery yet; configure `jwks_uri`
  explicitly on `AuthorizationServerEntry`.
- **OAuth Client ID Metadata Documents** (SEP-991) — not implemented.
- **Dynamic Client Registration** (RFC 7591) — not implemented; clients
  must be pre-registered with the authorization server.

## Related SEPs / RFCs

- **SEP-985** — OAuth Protected Resource Metadata discovery (RFC 9728).
- **SEP-835** — Incremental scope consent via `WWW-Authenticate` /
  `error="insufficient_scope"`.
- **PR #797** — OpenID Connect Discovery 1.0 (not implemented in this
  repo).
- **SEP-991** — OAuth Client ID Metadata Documents (not implemented).
