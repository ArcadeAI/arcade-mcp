# authorization

Demonstrates **OAuth 2.1 Resource Server Auth** for an MCP server running on
the HTTP transport — one of the two tracks through which 2025-11-25 protects
`/mcp/*` endpoints (the other being the Arcade-managed deploy path).

This is **server-level (front-door) auth**: every HTTP request to `/mcp/*`
must carry a valid Bearer token issued by one of the configured authorization
servers. The Bearer token authenticates the *caller* to the MCP server.

It is independent of **tool-level** auth — e.g.
`@app.tool(requires_auth=Reddit(scopes=["read"]))` or
`@app.tool(requires_secrets=[...])`. Tool-level auth is a separate runtime
concern handled by the tool execution layer when a tool actually runs (the
provider OAuth flow, secret resolution, etc.). This example does not
configure or demonstrate tool-level auth — only the server-level Bearer
token check at the front door.

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
