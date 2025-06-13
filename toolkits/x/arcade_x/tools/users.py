from typing import Annotated

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import X
from arcade_tdk.errors import RetryableToolError

from arcade_x.tools.utils import (
    expand_urls_in_user_description,
    expand_urls_in_user_url,
    get_headers_with_token,
)

# Users Lookup Tools. See developer docs for additional available query parameters:
# https://developer.x.com/en/docs/x-api/users/lookup/api-reference


@tool(requires_auth=X(scopes=["users.read", "tweet.read"]))
async def lookup_single_user_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the X (Twitter) user to look up"],
) -> Annotated[dict, "User information including id, name, username, and description"]:
    """Look up a user on X (Twitter) by their username."""

    headers = get_headers_with_token(context)

    user_fields = ",".join([
        "created_at",
        "description",
        "id",
        "location",
        "most_recent_tweet_id",
        "name",
        "pinned_tweet_id",
        "profile_image_url",
        "protected",
        "public_metrics",
        "url",
        "username",
        "verified",
        "verified_type",
        "withheld",
        "entities",
    ])
    url = f"https://api.x.com/2/users/by/username/{username}?user.fields={user_fields}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            # User not found
            raise RetryableToolError(
                "User not found",
                developer_message=f"User with username '{username}' not found.",
                additional_prompt_content="Please check the username and try again.",
                retry_after_ms=500,  # Play nice with X API rate limits
            )
        response.raise_for_status()
    # Parse the response JSON
    user_data = response.json()["data"]

    user_data = expand_urls_in_user_description(user_data, delete_entities=False)
    user_data = expand_urls_in_user_url(user_data, delete_entities=True)

    return {"data": user_data}
