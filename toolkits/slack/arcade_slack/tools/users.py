from typing import Annotated, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Slack
from arcade.sdk.errors import RetryableToolError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.constants import MAX_PAGINATION_TIMEOUT_SECONDS
from arcade_slack.utils import (
    async_paginate,
    extract_basic_user_info,
    is_user_a_bot,
    is_user_deleted,
)


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

    try:
        response = await slackClient.users_info(user=user_id)
    except SlackApiError as e:
        if e.response.get("error") == "user_not_found":
            users = await list_users(context)
            available_users = ", ".join(f"{user['id']} ({user['name']})" for user in users["users"])

            raise RetryableToolError(
                "User not found",
                developer_message=f"User with ID '{user_id}' not found.",
                additional_prompt_content=f"Available users: {available_users}",
                retry_after_ms=500,
            )

    return extract_basic_user_info(response.get("user", {}))


@tool(
    requires_auth=Slack(
        scopes=["users:read", "users:read.email"],
    )
)
async def list_users(
    context: ToolContext,
    exclude_bots: Annotated[Optional[bool], "Whether to exclude bots from the results"] = True,
    limit: Annotated[Optional[int], "The maximum number of users to return."] = None,
    next_cursor: Annotated[Optional[str], "The next cursor token to use for pagination."] = None,
) -> Annotated[dict, "The users' info"]:
    """List all users in the authenticated user's Slack team."""

    slackClient = AsyncWebClient(token=context.authorization.token)

    users, next_cursor = await async_paginate(
        func=slackClient.users_list,
        response_key="members",
        max_pagination_timeout_seconds=MAX_PAGINATION_TIMEOUT_SECONDS,
        next_cursor=next_cursor,
    )

    users = [
        extract_basic_user_info(user)
        for user in users
        if not is_user_deleted(user) and (not exclude_bots or not is_user_a_bot(user))
    ]

    return {"users": users, "next_cursor": next_cursor}
