from typing import Annotated

import httpx

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import X
from arcade.sdk.errors import ToolExecutionError
from arcade_x.tools.utils import expand_urls_in_user_description, expand_urls_in_user_url


# Users Lookup Tools. See developer docs for additional available query parameters: https://developer.x.com/en/docs/x-api/users/lookup/api-reference
@tool(requires_auth=X(scopes=["users.read", "tweet.read"]))
async def lookup_single_user_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the X (Twitter) user to look up"],
) -> Annotated[dict, "User information including id, name, username, and description"]:
    """Look up a user on X (Twitter) by their username."""

    headers = {
        "Authorization": f"Bearer {context.authorization.token}",
    }
    url = f"https://api.x.com/2/users/by/username/{username}?user.fields=created_at,description,id,location,most_recent_tweet_id,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,verified_type,withheld,entities"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=10)

    if response.status_code != 200:
        raise ToolExecutionError(
            f"Failed to look up user during execution of '{lookup_single_user_by_username.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    # Parse the response JSON
    user_data = response.json()["data"]

    expand_urls_in_user_description(user_data, delete_entities=False)
    expand_urls_in_user_url(user_data, delete_entities=True)

    """
    Example response["data"] structure:
    {
        "data": {
            "verified_type": str,
            "public_metrics": {
                "followers_count": int,
                "following_count": int,
                "tweet_count": int,
                "listed_count": int,
                "like_count": int
            },
            "id": str,
            "most_recent_tweet_id": str,
            "url": str,
            "verified": bool,
            "location": str,
            "description": str,
            "name": str,
            "username": str,
            "profile_image_url": str,
            "created_at": str,
            "protected": bool
        }
    }
    """
    return {"data": user_data}
