"""Example: Email-to-Slack compound tool using typed tool composition.

This MCP server exposes a single tool that reads unread Gmail messages
and forwards them as Slack messages to a specified channel.

It demonstrates:
  - `context.tools.execute()` for strongly-typed cross-tool calls
  - `OnMissing.ALLOW_NULL` for resilient field extraction
  - Pydantic models as the "contract" between tools with different response shapes

Usage:
    uv run python examples/mcp_servers/email_to_slack.py stdio
    uv run python examples/mcp_servers/email_to_slack.py http
"""

import logging
import sys
from typing import Annotated

from arcade_mcp_server import Context, ExecuteOptions, MCPApp, OnMissing
from arcade_mcp_server.resource_server import AuthorizationServerEntry, ResourceServerAuth
from pydantic import BaseModel

logger = logging.getLogger(__name__)

resource_server_auth = ResourceServerAuth(
    canonical_url="http://127.0.0.1:8000/mcp",
    authorization_servers=[
        AuthorizationServerEntry(
            authorization_server_url="https://cloud.arcade.dev/oauth2",
            issuer="https://cloud.arcade.dev/oauth2",
            jwks_uri="https://cloud.arcade.dev/.well-known/jwks/oauth2",
            algorithm="Ed25519",
        )
    ],
)

app = MCPApp(name="email_to_slack", version="1.0.0", auth=resource_server_auth)


# ---------------------------------------------------------------------------
# Response models — these define the shape we *want*, regardless of what
# Gmail or Slack actually return. The structuring layer handles the mapping.
# ---------------------------------------------------------------------------


class EmailSummary(BaseModel):
    """A single email extracted from Gmail's response."""

    subject: str
    sender: str
    snippet: str


class EmailList(BaseModel):
    """The shape we expect from Gmail.ListEmails."""

    emails: list[EmailSummary] = []


class SlackResponse(BaseModel):
    """The shape we expect back from Slack.SendMessage."""

    ok: bool
    channel: str
    ts: str


class ForwardedEmail(BaseModel):
    """A single email that was forwarded to Slack."""

    sender: str
    snippet: str
    sent_to_slack: bool


class ForwardResult(BaseModel):
    """Result of the forward operation."""

    forwarded: int
    total: int
    emails: list[ForwardedEmail]


# ---------------------------------------------------------------------------
# Default options — resilient to upstream response changes
# ---------------------------------------------------------------------------

DEFAULT_OPTIONS = ExecuteOptions(
    on_missing=OnMissing.ALLOW_NULL,
    timeout_seconds=30,
    max_retries=2,
)


# ---------------------------------------------------------------------------
# Compound tool
# ---------------------------------------------------------------------------


@app.tool(
    request_scopes_from=["Gmail.ListEmails", "Slack.SendMessage"],
)
async def forward_emails_to_slack(
    context: Context,
    channel_name: Annotated[str, "Slack channel to post emails to (e.g. '#general')"],
    max_emails: Annotated[int, "Maximum number of emails to forward"] = 5,
) -> ForwardResult:
    """Read recent emails from Gmail and forward them as Slack messages."""

    # Step 1: Fetch emails
    logger.warning("Fetching emails with n_emails=%d", max_emails)
    email_data = await context.tools.execute(
        EmailList,
        "Gmail.ListEmails",
        {"n_emails": max_emails},
        options=DEFAULT_OPTIONS,
    )
    logger.warning("Gmail response: %s", email_data.model_dump())

    if not email_data.emails:
        return ForwardResult(forwarded=0, total=0, emails=[])

    # Step 2: Send each email as a Slack message
    results: list[ForwardedEmail] = []
    for email in email_data.emails:
        message = f"*From:* {email.sender}\n*Subject:* {email.subject}\n> {email.snippet}"

        slack_result = await context.tools.execute(
            SlackResponse,
            "Slack.SendMessage",
            {
                "message": message,
                "channel_name": channel_name,
            },
            options=DEFAULT_OPTIONS,
        )
        results.append(
            ForwardedEmail(
                sender=email.sender,
                snippet=email.snippet,
                sent_to_slack=bool(slack_result.ok),
            )
        )

    forwarded = sum(1 for r in results if r.sent_to_slack)
    return ForwardResult(
        forwarded=forwarded,
        total=len(results),
        emails=results,
    )


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
