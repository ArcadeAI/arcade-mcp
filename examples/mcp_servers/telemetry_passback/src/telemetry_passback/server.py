"""Gmail MCP server with SEP-0000 telemetry passback.

Vendor-side reference implementation of cross-org distributed tracing:

* Advertises ``serverExecutionTelemetry`` via ``TelemetryPassbackMiddleware``.
* Gmail tools (list_emails, send_email) using Google OAuth via Arcade.
* Rich server-side instrumentation creates logical-phase spans
  (auth, API calls, formatting) that the middleware automatically collects.
* ``HTTPXClientInstrumentor`` auto-instruments Gmail API HTTP calls as child spans.
* Does NOT export spans externally — simulates a vendor with its own backend.
"""

import base64
import json
import logging
import sys
from email.mime.text import MIMEText
from pathlib import Path
from typing import Annotated, cast

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

import httpx
from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.auth import Google
from arcade_mcp_server.mcp_app import TransportType
from arcade_mcp_server.middleware.telemetry import TelemetryPassbackMiddleware
from arcade_mcp_server.resource_server import (
    AuthorizationServerEntry,
    ResourceServerAuth,
)
from arcade_mcp_server.resource_server.base import ResourceOwner
from opentelemetry import trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider

# ------------------------------------------------------------
# OpenTelemetry — server-internal only (no external exporter)
# ------------------------------------------------------------

provider = TracerProvider()
telemetry_mw = TelemetryPassbackMiddleware(
    service_name="mcp-gmail-server",
    tracer_provider=provider,
)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("mcp-gmail-server")
_log = logging.getLogger("mcp-gmail-server")


async def _async_request_hook(span, request):
    """Capture request method + URL with gen_ai semantic conventions."""
    method = request.method.decode() if isinstance(request.method, bytes) else str(request.method)
    url = str(request.url)
    endpoint = url.split("?")[0].split("/")[-1] or "/"
    span.update_name(f"{method} {endpoint}")
    span.set_attribute("gen_ai.system", "mcp")
    span.set_attribute("gen_ai.operation.name", "execute_tool")
    span.set_attribute("gen_ai.tool.name", f"{method} {endpoint}")
    span.set_attribute("gen_ai.tool.call.arguments", json.dumps({"method": method, "url": url}))


async def _async_response_hook(span, request, response):
    """Capture response status with gen_ai semantic conventions."""
    method = request.method.decode() if isinstance(request.method, bytes) else str(request.method)
    url = str(request.url)
    span.set_attribute("gen_ai.tool.call.result", json.dumps({
        "status": response.status_code,
        "url": url,
        "method": method,
    }))


HTTPXClientInstrumentor().instrument(
    async_request_hook=_async_request_hook,
    async_response_hook=_async_response_hook,
)

# -----------------------
# Arcade MCP application
# -----------------------

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

# --------------------------------------------
# Resource server auth (OAuth 2.1 via Arcade)
# --------------------------------------------

CANONICAL_URL = "http://127.0.0.1:8000/mcp"


class ArcadeResourceServerAuth(ResourceServerAuth):
    """ResourceServerAuth that uses the ``email`` claim as user_id.

    Arcade's tool authorization identifies users by email, but the default
    ``JWKSTokenValidator`` uses the ``sub`` claim (a UUID). This override
    swaps user_id to the email so Arcade can match the authorized user.
    """

    async def validate_token(self, token: str) -> ResourceOwner:
        owner = await super().validate_token(token)
        email = owner.claims.get("email")
        if email:
            owner.user_id = email
        return owner


resource_server_auth = ArcadeResourceServerAuth(
    canonical_url=CANONICAL_URL,
    authorization_servers=[
        AuthorizationServerEntry(
            authorization_server_url="https://cloud.arcade.dev/oauth2",
            issuer="https://cloud.arcade.dev/oauth2",
            jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
            algorithm="Ed25519",
            expected_audiences=[CANONICAL_URL],
        ),
    ],
)

app = MCPApp(
    name="mcp_gmail_server",
    version="0.1.0",
    instructions=(
        "Gmail server with cross-org observability "
        "via SEP-0000 serverExecutionTelemetry."
    ),
    auth=resource_server_auth,
    middleware=[telemetry_mw],
    extra_capabilities=telemetry_mw.get_capabilities(),
)

# ------
# Tools
# ------


@app.tool(requires_auth=Google(scopes=[GMAIL_READONLY_SCOPE]))
async def list_emails(
    context: Context,
    max_results: Annotated[int, "Maximum number of emails to return"] = 5,
    query: Annotated[str, "Gmail search query (e.g. 'is:unread')"] = "",
) -> Annotated[dict, "Dict with 'emails' key containing list of recent emails"]:
    """List recent emails from the user's Gmail inbox."""
    token = context.get_auth_token_or_empty()

    with tracer.start_as_current_span("auth.validate") as auth_span:
        auth_span.set_attribute("gen_ai.system", "mcp")
        auth_span.set_attribute("gen_ai.operation.name", "execute_tool")
        auth_span.set_attribute("gen_ai.tool.name", "auth.validate")
        auth_span.set_attribute("auth.method", "oauth2_bearer")

    params: dict = {"maxResults": min(max(max_results, 1), 20)}
    if query:
        params["q"] = query

    async with httpx.AsyncClient() as client:
        with tracer.start_as_current_span("gmail.list_messages") as list_span:
            list_span.set_attribute("gen_ai.system", "mcp")
            list_span.set_attribute("gen_ai.operation.name", "execute_tool")
            list_span.set_attribute("gen_ai.tool.name", "gmail.list_messages")
            list_span.set_attribute("gmail.max_results", params["maxResults"])
            list_resp = await client.get(
                f"{GMAIL_API}/messages",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            list_resp.raise_for_status()
            messages = list_resp.json().get("messages", [])
            list_span.set_attribute("gmail.message_count", len(messages))

        with tracer.start_as_current_span("gmail.fetch_details") as details_span:
            details_span.set_attribute("gen_ai.system", "mcp")
            details_span.set_attribute("gen_ai.operation.name", "execute_tool")
            details_span.set_attribute("gen_ai.tool.name", "gmail.fetch_details")
            details_span.set_attribute("gmail.fetch_count", len(messages))

            results = []
            for msg_ref in messages:
                detail_resp = await client.get(
                    f"{GMAIL_API}/messages/{msg_ref['id']}",
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "format": "metadata",
                        "metadataHeaders": ["Subject", "From"],
                    },
                )
                detail_resp.raise_for_status()
                msg = detail_resp.json()
                hdrs = {
                    h["name"]: h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }
                results.append({
                    "id": msg["id"],
                    "subject": hdrs.get("Subject", "(no subject)"),
                    "from": hdrs.get("From", "(unknown)"),
                    "snippet": msg.get("snippet", ""),
                })

    with tracer.start_as_current_span("format_response") as fmt_span:
        fmt_span.set_attribute("gen_ai.system", "mcp")
        fmt_span.set_attribute("gen_ai.operation.name", "execute_tool")
        fmt_span.set_attribute("gen_ai.tool.name", "format_response")
        fmt_span.set_attribute("email.count", len(results))

    return {"emails": results}


@app.tool(requires_auth=Google(scopes=[GMAIL_SEND_SCOPE]))
async def send_email(
    context: Context,
    to: Annotated[str, "Recipient email address"],
    subject: Annotated[str, "Email subject line"],
    body: Annotated[str, "Email body text"],
) -> Annotated[dict, "Send confirmation with message ID"]:
    """Send an email via the user's Gmail account."""
    token = context.get_auth_token_or_empty()

    with tracer.start_as_current_span("auth.validate") as auth_span:
        auth_span.set_attribute("gen_ai.system", "mcp")
        auth_span.set_attribute("gen_ai.operation.name", "execute_tool")
        auth_span.set_attribute("gen_ai.tool.name", "auth.validate")
        auth_span.set_attribute("auth.method", "oauth2_bearer")

    mime = MIMEText(body)
    mime["to"] = to
    mime["subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

    with tracer.start_as_current_span("gmail.send_message") as send_span:
        send_span.set_attribute("gen_ai.system", "mcp")
        send_span.set_attribute("gen_ai.operation.name", "execute_tool")
        send_span.set_attribute("gen_ai.tool.name", "gmail.send_message")
        send_span.set_attribute("gmail.recipient", to)
        send_span.set_attribute("gmail.subject", subject)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GMAIL_API}/messages/send",
                headers={"Authorization": f"Bearer {token}"},
                json={"raw": raw},
            )
            resp.raise_for_status()
            result = resp.json()

    with tracer.start_as_current_span("format_response") as fmt_span:
        fmt_span.set_attribute("gen_ai.system", "mcp")
        fmt_span.set_attribute("gen_ai.operation.name", "execute_tool")
        fmt_span.set_attribute("gen_ai.tool.name", "format_response")
        fmt_span.set_attribute("email.message_id", result.get("id", ""))

    return {"message_id": result.get("id", ""), "status": "sent"}


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "http"
    app.run(transport=cast(TransportType, transport), host="127.0.0.1", port=8000)
