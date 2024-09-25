from typing import Annotated

import requests

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import X


# Users Lookup Tools. See developer docs for additional available query parameters: https://developer.x.com/en/docs/x-api/users/lookup/api-reference
@tool(requires_auth=X(scopes=["users.read", "tweet.read"]))
def lookup_single_user_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the X (Twitter) user to look up"],
) -> Annotated[str, "User information including id, name, username, and description"]:
    """Look up a user on X (Twitter) by their username."""

    headers = {
        "Authorization": f"Bearer {context.authorization.token}",
    }
    url = f"https://api.x.com/2/users/by/username/{username}?user.fields=created_at,description,id,location,most_recent_tweet_id,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,verified_type,withheld"

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise ToolExecutionError(
            f"Failed to look up user during execution of '{lookup_single_user_by_username.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    """
    Example response.text structure:
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
    return response.text
