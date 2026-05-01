# url_elicitation

Demonstrates **URL-mode elicitation** — the out-of-band user interaction
primitive introduced in MCP 2025-11-25 (SEP-1036).

Instead of asking the user to fill in a form (like `user_elicitation/` does),
a URL-mode elicitation asks the MCP client to open a URL where the user
interacts with some external page: an IdP, a signing portal, a verification
service. The client observes the interaction (or gets told to dismiss the UI
via `notifications/elicitation/complete`) and returns an `ElicitResult`.

## What this example shows

| Tool | Mode | What happens |
|---|---|---|
| `verify_identity(user)` | URL | Tool asks the client to open `http://127.0.0.1:8001/verify/<id>`; companion webapp logs which button the user clicked; server returns the result. |
| `upload_signature()` | form (fallback) | Same `context.ui.elicit` call with no `mode=` kwarg — plain form elicitation. |

A tiny stdlib-only **companion webapp** runs on port `8001` alongside the
MCP server (`8000`), serving a "Yes, I'm me / No, cancel" page. It lives in
the same file; no extra dependency. In a real deployment this would be
replaced with whatever IdP / verifier you want.

## Running

```bash
uv sync
uv run python src/url_elicitation/server.py        # HTTP transport on :8000 + companion on :8001
uv run python src/url_elicitation/server.py stdio  # stdio MCP + companion still on :8001
```

Connect your MCP client to `http://127.0.0.1:8000/mcp`, call `verify_identity`,
and watch the companion webapp open in your browser. Click one of the two
buttons — the tool returns a corresponding status string.

## Wire shape of the URL elicitation

The server's `context.ui.elicit(mode="url", ...)` call produces this
outgoing request to the client:

```jsonc
{
  "method": "elicitation/create",
  "params": {
    "mode": "url",
    "url": "http://127.0.0.1:8001/verify/elicit_abc123",
    "elicitationId": "elicit_abc123",
    "message": "Please verify you are alice."
  }
}
```

The client is expected to open that URL and, when the user finishes, return:

```jsonc
{
  "action": "accept"  // or "decline" / "cancel"
  // content is typically absent — the URL interaction IS the payload
}
```

The server's `context.ui.elicit` call unblocks and returns an `ElicitResult`
with that action.

### The completion notification (optional)

The server has a second channel it can use to tell the client the URL flow
has finished, even if the client's webview can't detect it on its own:

```python
await context._session.send_elicitation_complete(elicit_id)
```

This emits `notifications/elicitation/complete` with the elicitation id. The
client is supposed to dismiss its URL UI (e.g., close the popup webview) when
it sees it. In this example we don't use it because the stdlib companion
app doesn't integrate with the session directly, but the hook is available.

## Client capability gating

The server checks `ClientCapabilities.elicitation.url` during tool execution.
If the client didn't declare it during `initialize`, the tool raises a
user-friendly error using the `URLElicitationRequiredError` type (wire error
code `-32042`) rather than making a call the client can't handle.

```python
if not client_caps.elicitation.get("url"):
    raise ValueError("…requires URL-mode elicitation…")
```

A 2025-11-25 MCP client's `initialize` params should include:

```jsonc
{
  "capabilities": {
    "elicitation": {"url": true}
  }
}
```

## Why no fake IdP?

Keeping the demo self-contained means we ship a single verification page with
two buttons. We *intentionally* don't try to simulate an OAuth dance — the
point is to show the `context.ui.elicit(mode="url", ...)` API call, not to
reinvent auth. For a real OAuth integration, see the `authorization/`
example and use `ResourceServerAuth`.

## Related SEPs

- **SEP-1036** — URL-mode elicitation and `URLElicitationRequiredError`.
- **SEP-1034** — Default values on elicitation primitive schemas (covered in
  `enum_elicitation/`; URL mode has no form schema to default).
- **SEP-1613** — JSON Schema 2020-12 (doesn't apply to URL mode, which has no
  schema).
