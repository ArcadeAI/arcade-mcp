from typing import Annotated

import httpx

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import OAuth2


@tool(
    requires_auth=OAuth2(
        provider_id="linkedin",
        authority="https://www.linkedin.com",
        scopes=["w_member_social"],
    )
)
async def share_text_post(
    context: ToolContext,
    text: Annotated[str, "The text content of the post"],
) -> Annotated[str, "URL of the shared post"]:
    """Share a post to LinkedIn."""
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {context.authorization.token}",
        "Content-Type": "application/json",
    }

    user_id = context.authorization.user_info.get("sub")
    if not user_id:
        raise ToolExecutionError(
            "User ID not found.",
            developer_message="User ID not found in `context.authorization.user_info.sub`",
        )

    author_id = f"urn:li:person:{user_id}"
    payload = {
        "author": author_id,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.RequestError as e:
            raise ToolExecutionError(f"Failed to share post to LinkedIn: {e}") from e

    if response.status_code == 201:
        share_id = response.json().get("id")
        return f"https://www.linkedin.com/feed/update/{share_id}/"
    elif response.status_code == 401:
        raise ToolExecutionError("Unauthorized: Invalid or expired token")
    elif response.status_code == 403:
        raise ToolExecutionError("Forbidden: Access denied")
    elif response.status_code == 429:
        raise ToolExecutionError("Too Many Requests: Rate limit exceeded")
    else:
        raise ToolExecutionError(f"Error: {response.status_code} - {response.text}")
