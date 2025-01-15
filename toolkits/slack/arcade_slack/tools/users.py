from typing import Annotated, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Slack
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.utils import extract_basic_user_info, is_user_a_bot, is_user_deleted


@tool(
    requires_auth=Slack(
        scopes=["users:read", "users:read.email"],
    )
)
async def get_user_info_by_id(
    context: ToolContext,
    user_id: Annotated[str, "The ID of the user to get"],
) -> Annotated[dict, "The user's information"]:
    """Get the information of a user in Slack."""

    slackClient = AsyncWebClient(token=context.authorization.token)
    response = await slackClient.users_info(user=user_id)

    return extract_basic_user_info(response.get("user", {}))


@tool(
    requires_auth=Slack(
        scopes=["users:read", "users:read.email"],
    )
)
async def list_users(
    context: ToolContext,
    exclude_bots: Annotated[Optional[bool], "Whether to exclude bots from the results"] = True,
    limit: Annotated[
        Optional[int], "The maximum number of users to return. Defaults to -1 (no limit)"
    ] = -1,
) -> Annotated[dict, "The users' info"]:
    """List all users in the authenticated user's Slack team."""

    slackClient = AsyncWebClient(token=context.authorization.token)
    users = []
    next_page_token = None

    while limit == -1 or len(users) < limit:
        iteration_limit = (
            200 if limit == -1 else min(limit - len(users), 200)
        )  # Slack recommends max 200 results at a time
        response = await slackClient.users_list(cursor=next_page_token, limit=iteration_limit)
        if response.get("ok"):
            for user in response.get("members", []):
                if not is_user_deleted(user) and (not exclude_bots or not is_user_a_bot(user)):
                    users.append(extract_basic_user_info(user))

        next_page_token = response.get("response_metadata", {}).get("next_cursor")

        if not next_page_token:
            break

    return {"users": users}
