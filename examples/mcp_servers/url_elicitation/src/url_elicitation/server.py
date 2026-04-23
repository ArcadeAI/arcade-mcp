#!/usr/bin/env python3
"""url_elicitation MCP server.

Demonstrates URL-mode elicitation (SEP-1036, MCP 2025-11-25):

- Tool calls ``context.ui.elicit(message="…", mode="url", url="…", elicitation_id="…")``.
- The server sends an ``elicitation/create`` request with ``mode: "url"`` to
  the client. The client opens the URL (in-process webview, system browser,
  ...) and observes the user's interaction.
- When the user finishes, the client returns an ``ElicitResult`` to the
  server. For URL flows the ``action`` is typically ``"accept"`` /
  ``"decline"`` / ``"cancel"`` and ``content`` is often empty — the actual
  result of the interaction lives on the URL provider's side (e.g. a
  verification service, an OAuth provider, a signing portal).

The example includes a tiny **companion webapp** bound to a different port
that serves the verification page. It's useful for running the demo
end-to-end without an external IdP.

For form-mode elicitation, see the separate ``user_elicitation/`` example.
For the handshake error type (when a tool requires URL-mode but the client
doesn't support it), see ``URLElicitationRequiredError`` below.
"""

import asyncio
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Annotated

from arcade_mcp_server import (
    Context,
    MCPApp,
    URLElicitationRequiredError,
)
from arcade_mcp_server.types import ClientCapabilities

# -----------------------------------------------------------------------------
# Companion webapp — stdlib only, no FastAPI dep. Bound to a different port
# from the main MCP HTTP server so both can run in the same process.
# -----------------------------------------------------------------------------

COMPANION_HOST = "127.0.0.1"
COMPANION_PORT = 8001


_PAGE_HTML = """\
<!doctype html>
<html>
<head><title>Identity verification</title></head>
<body style="font-family: sans-serif; margin: 4rem auto; max-width: 32rem;">
  <h1>Are you really {user}?</h1>
  <p>Verification id: <code>{elicit_id}</code></p>
  <form method="POST" action="/verify/{elicit_id}">
    <button name="answer" value="yes" style="padding: 0.6rem 1.4rem;">Yes, I'm me</button>
    <button name="answer" value="no"  style="padding: 0.6rem 1.4rem;">No, cancel</button>
  </form>
</body>
</html>
"""

_SUCCESS_HTML = "<!doctype html><html><body><h1>Thanks — you can close this tab.</h1></body></html>"


class _CompanionHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/verify/"):
            elicit_id = self.path.removeprefix("/verify/")
            user = "the user"
            body = _PAGE_HTML.format(user=user, elicit_id=elicit_id).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/verify/"):
            elicit_id = self.path.removeprefix("/verify/")
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode()
            # rudimentary form parsing
            answer = "yes" if "answer=yes" in body else "no"
            _mark_completed(elicit_id, answer)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_SUCCESS_HTML.encode())
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002, D401
        # Silence default stderr logging to keep stdio transport clean.
        return


_completions: dict[str, asyncio.Future[str]] = {}
_loop_ref: asyncio.AbstractEventLoop | None = None


def _mark_completed(elicit_id: str, answer: str) -> None:
    """Called by the companion HTTP thread when the user clicks a button."""
    fut = _completions.get(elicit_id)
    if fut is None:
        return
    if _loop_ref is None:
        return

    def _set() -> None:
        if not fut.done():
            fut.set_result(answer)

    _loop_ref.call_soon_threadsafe(_set)


def _start_companion() -> None:
    """Start the companion webapp on a background thread."""
    server = ThreadingHTTPServer((COMPANION_HOST, COMPANION_PORT), _CompanionHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="companion-webapp")
    thread.start()


# -----------------------------------------------------------------------------
# MCPApp
# -----------------------------------------------------------------------------


app = MCPApp(
    name="url_elicitation",
    version="1.0.0",
    log_level="DEBUG",
    instructions=(
        f"Before calling tools, make sure the companion verification webapp is up at "
        f"http://{COMPANION_HOST}:{COMPANION_PORT}. The MCP server starts it automatically."
    ),
)


# -----------------------------------------------------------------------------
# 1. URL-mode elicitation — the main feature
# -----------------------------------------------------------------------------


@app.tool
async def verify_identity(
    context: Context,
    user: Annotated[str, "User display name to show on the verification page"],
) -> Annotated[str, "A status string — verified, declined, or cancelled"]:
    """Ask the user to verify their identity out-of-band.

    Triggers a URL-mode elicitation: the client opens the verification URL,
    the user clicks "Yes, I'm me" or "No, cancel" on a page hosted by this
    example's companion webapp. The server correlates the button click with
    the elicitation via ``elicitation_id`` and returns the result.

    If the client does not support URL elicitation, the tool returns a
    graceful error instead of crashing.
    """
    # 1. Client capability check — MCP 2025-11-25 clients should declare
    #    ``capabilities.elicitation.url`` during initialize. Bail out cleanly
    #    on older or unsupportive clients.
    caps: ClientCapabilities | None = getattr(context._session, "_client_capabilities", None)
    elicit_caps = caps.elicitation if caps and caps.elicitation else {}
    if not isinstance(elicit_caps, dict) or not elicit_caps.get("url"):
        # This is the wire error code -32042 (URLElicitationRequiredError).
        # Re-raising it means the orchestrator's LLM sees the error explicitly.
        err = URLElicitationRequiredError(
            message=(
                "This tool requires URL-mode elicitation, but the connected client "
                "did not declare `capabilities.elicitation.url` at initialize. "
                "Upgrade to an MCP 2025-11-25 client."
            ),
        )
        raise ValueError(err.message)

    elicit_id = f"elicit_{uuid.uuid4().hex}"
    url = f"http://{COMPANION_HOST}:{COMPANION_PORT}/verify/{elicit_id}"

    # 2. Prepare a completion future. The companion webapp will resolve it
    #    when the user clicks a button. Register it INSIDE a try/finally so
    #    the _completions slot is always released -- otherwise a failure in
    #    ``context.ui.elicit`` (step 3) would leak the future entry.
    global _loop_ref
    _loop_ref = asyncio.get_running_loop()
    _completions[elicit_id] = _loop_ref.create_future()

    try:
        await context.log.info(f"Sending URL elicitation {elicit_id} -> {url}")

        # 3. Issue the URL-mode elicitation to the client. The client opens
        #    the URL and blocks on the user's answer. While that's happening,
        #    we also wait for the companion webapp to report the button click.
        result = await context.ui.elicit(
            message=f"Please verify you are {user}.",
            mode="url",
            url=url,
            elicitation_id=elicit_id,
        )

        # 4. (Optional) Wait up to 60s for the companion webapp to tell us
        #    which button the user clicked — purely a server-side convenience
        #    so we can log it. The authoritative result is still ``result``
        #    from the client.
        try:
            companion_answer = await asyncio.wait_for(_completions[elicit_id], timeout=1.0)
            await context.log.info(f"Companion webapp saw answer={companion_answer!r}")
        except asyncio.TimeoutError:
            await context.log.warning(
                "Companion webapp did not report a button click — the client may have "
                "rendered its own verification UI without hitting our URL."
            )

        return {
            "accept": f"Verified identity for {user}.",
            "decline": f"User declined to verify identity for {user}.",
            "cancel": f"User cancelled the verification for {user}.",
        }.get(result.action, f"Unknown elicit action: {result.action}")
    finally:
        # Always drop the _completions entry so a tool error above cannot
        # accumulate stale futures across repeated invocations.
        _completions.pop(elicit_id, None)


# -----------------------------------------------------------------------------
# 2. Form-mode fallback — illustrates that the two modes share one call site
# -----------------------------------------------------------------------------


@app.tool
async def upload_signature(context: Context) -> str:
    """Collect a freeform signature string via form-mode elicitation.

    Same ``context.ui.elicit`` call, no ``mode=`` kwarg — defaults to
    ``"form"``. Useful side-by-side comparison to the URL mode above.
    """
    result = await context.ui.elicit(
        "Please type your signature (your name):",
        schema={
            "type": "object",
            "properties": {
                "signature": {"type": "string"},
            },
            "required": ["signature"],
        },
    )
    if result.action != "accept":
        return f"Signature collection {result.action}ed."
    return f"Got signature: {result.content['signature']}"


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"

    # Start the companion webapp so the URL tool has something to point at.
    _start_companion()

    app.run(transport=transport, host="127.0.0.1", port=8000)
