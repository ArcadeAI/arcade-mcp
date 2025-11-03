"""Utility functions for Mailchimp Marketing API toolkit."""

from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from arcade_tdk import ToolContext


async def get_base_url(context: "ToolContext", http_client: httpx.AsyncClient) -> str:
    """Get Mailchimp API base URL from OAuth token.

    Args:
        context: The ToolContext containing the auth token
        http_client: The httpx AsyncClient to use for the request

    Returns:
        The full Mailchimp API base URL (e.g., "https://us1.api.mailchimp.com/3.0")
    """
    auth_token = context.get_auth_token_or_empty()
    response = await http_client.request(
        url="https://login.mailchimp.com/oauth2/metadata",
        method="GET",
        headers={"Authorization": f"OAuth {auth_token}"},
    )
    response.raise_for_status()
    metadata = response.json()
    dc = metadata.get("dc", "")
    subdomain = str(dc) if dc else ""
    return f"https://{subdomain}.api.mailchimp.com/3.0"
