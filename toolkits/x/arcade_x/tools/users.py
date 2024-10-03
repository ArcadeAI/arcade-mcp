from typing import Annotated

import httpx

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import X


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

    # Resolve t.co links to their expanded URLs in the description
    description_urls = user_data.get("entities", {}).get("description", {}).get("urls", [])
    description = user_data.get("description", "")
    for url_info in description_urls:
        t_co_link = url_info["url"]
        expanded_url = url_info["expanded_url"]
        description = description.replace(t_co_link, expanded_url)
    user_data["description"] = description

    # Resolve t.co links to their expanded URLs in the url
    url_urls = user_data.get("entities", {}).get("url", {}).get("urls", [])
    url = user_data.get("url", "")
    for url_info in url_urls:
        t_co_link = url_info["url"]
        expanded_url = url_info["expanded_url"]
        url = url.replace(t_co_link, expanded_url)
    user_data["url"] = url

    # Entities is no longer needed now that we have expanded the t.co links
    user_data.pop("entities", None)

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
