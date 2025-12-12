from typing import Any

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError


def get_headers(context: ToolContext) -> dict[str, str]:
    """Build headers for Mastodon API requests."""
    token = context.get_auth_token_or_empty()
    if not token:
        raise ToolExecutionError(message="No Mastodon token found")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_url(
    context: ToolContext,
    endpoint: str,
    api_version: str = "v1",
) -> str:
    """Build the full URL for a Mastodon API endpoint."""
    try:
        return f"{context.get_secret('MASTODON_SERVER_URL')}/api/{api_version}/{endpoint}"
    except ValueError as e:
        raise ToolExecutionError(
            message="MASTODON_SERVER_URL is not set in the secrets",
        ) from e


def parse_status(status: dict[str, Any]) -> dict[str, Any]:
    """Filter out unnecessary fields from the status object."""
    return {
        "id": status["id"],
        "url": status["url"],
        "content": status["content"],
        "created_at": status["created_at"],
        "tags": status["tags"],
        "media_attachments": status["media_attachments"],
        "account_id": status["account"]["id"],
        "account_username": status["account"]["username"],
        "account_display_name": status["account"]["display_name"],
        "favourites_count": status["favourites_count"],
    }


def parse_statuses(statuses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out unnecessary fields from the statuses object."""
    return [parse_status(status) for status in statuses]
