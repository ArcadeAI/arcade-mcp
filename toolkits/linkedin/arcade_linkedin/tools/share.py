from typing import Annotated

import httpx

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import LinkedIn
from arcade.sdk.errors import ToolExecutionError

LINKEDIN_BASE_URL = "https://api.linkedin.com/v2"


async def _send_linkedin_request(
    context: ToolContext,
    method: str,
    endpoint: str,
    params: dict | None = None,
    json_data: dict | None = None,
) -> httpx.Response:
    """
    Send an asynchronous request to the LinkedIn API.

    Args:
        context: The tool context containing the authorization token.
        method: The HTTP method (GET, POST, PUT, DELETE, etc.).
        endpoint: The API endpoint path (e.g., "/ugcPosts").
        params: Query parameters to include in the request.
        json_data: JSON data to include in the request body.

    Returns:
        The response object from the API request.

    Raises:
        ToolExecutionError: If the request fails for any reason.
    """
    url = f"{LINKEDIN_BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {context.authorization.token}"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method, url, headers=headers, params=params, json=json_data
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            raise ToolExecutionError(f"Failed to send request to LinkedIn API: {e}")

    return response


def _handle_linkedin_api_error(response: httpx.Response):
    """
    Handle errors from the LinkedIn API by mapping common status codes to ToolExecutionErrors.

    Args:
        response: The response object from the API request.

    Raises:
        ToolExecutionError: If the response contains an error status code.
    """
    status_code_map = {
        401: ToolExecutionError("Unauthorized: Invalid or expired token"),
        403: ToolExecutionError("Forbidden: User does not have Spotify Premium"),
        429: ToolExecutionError("Too Many Requests: Rate limit exceeded"),
    }

    if response.status_code in status_code_map:
        raise status_code_map[response.status_code]
    elif response.status_code >= 400:
        raise ToolExecutionError(f"Error: {response.status_code} - {response.text}")


@tool(
    requires_auth=LinkedIn(
        scopes=["w_member_social"],
    )
)
async def create_text_post(
    context: ToolContext,
    text: Annotated[str, "The text content of the post"],
) -> Annotated[str, "URL of the shared post"]:
    """Share a new text post to LinkedIn."""
    endpoint = "/ugcPosts"

    # The LinkedIn user ID is required to create a post, even though we're using the user's access token.
    # Arcade Engine gets the current user's info from LinkedIn and automatically populates context.authorization.user_info.
    # LinkedIn calls the user ID "sub" in their user_info data payload. See:
    # https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2#api-request-to-retreive-member-details
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

    response = await _send_linkedin_request(context, "POST", endpoint, json_data=payload)
    if response.status_code >= 200 and response.status_code < 300:
        share_id = response.json().get("id")
        return f"https://www.linkedin.com/feed/update/{share_id}/"
    else:
        _handle_linkedin_api_error(response)
