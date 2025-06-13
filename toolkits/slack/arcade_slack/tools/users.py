from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Slack
from arcade_tdk.errors import RetryableToolError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.constants import MAX_PAGINATION_TIMEOUT_SECONDS
from arcade_slack.models import SlackPaginationNextCursor, SlackUser
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
) -> Annotated[dict[str, Any], "The user's information"]:
    """Get the information of a user in Slack."""

    token = (
        context.authorization.token if context.authorization and context.authorization.token else ""
    )
    slackClient = AsyncWebClient(token=token)

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

    user_dict_raw: dict[str, Any] = response.get("user", {}) or {}
    user_dict = cast(SlackUser, user_dict_raw)
    user = SlackUser(**user_dict)
    return dict(**extract_basic_user_info(user))


@tool(
    requires_auth=Slack(
        scopes=["users:read", "users:read.email"],
    )
)
async def list_users(
    context: ToolContext,
    exclude_bots: Annotated[bool | None, "Whether to exclude bots from the results"] = True,
    limit: Annotated[int | None, "The maximum number of users to return."] = None,
    next_cursor: Annotated[str | None, "The next cursor token to use for pagination."] = None,
) -> Annotated[dict, "The users' info"]:
    """List all users in the authenticated user's Slack team."""

    token = (
        context.authorization.token if context.authorization and context.authorization.token else ""
    )
    slackClient = AsyncWebClient(token=token)

    users, next_cursor = await async_paginate(
        func=slackClient.users_list,
        response_key="members",
        limit=limit,
        next_cursor=cast(SlackPaginationNextCursor, next_cursor),
        max_pagination_timeout_seconds=MAX_PAGINATION_TIMEOUT_SECONDS,
    )

    users = [
        extract_basic_user_info(user)
        for user in users
        if not is_user_deleted(user) and (not exclude_bots or not is_user_a_bot(user))
    ]

    return {"users": users, "next_cursor": next_cursor}
