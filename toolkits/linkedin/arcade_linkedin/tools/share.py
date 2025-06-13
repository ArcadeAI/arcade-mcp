from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import LinkedIn
from arcade_tdk.errors import ToolExecutionError

from arcade_linkedin.tools.utils import _handle_linkedin_api_error, _send_linkedin_request


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

    # The LinkedIn user ID is required to create a post, even though we're using
    # the user's access token.
    # Arcade Engine gets the current user's info from LinkedIn and automatically
    # populates context.authorization.user_info.
    # LinkedIn calls the user ID "sub" in their user_info data payload. See:
    # https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2#api-request-to-retreive-member-details
    user_id = context.authorization.user_info.get("sub") if context.authorization else None

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

    _handle_linkedin_api_error(response)

    return ""
