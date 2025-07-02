from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Slack
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.constants import MAX_PAGINATION_TIMEOUT_SECONDS
from arcade_slack.models import (
    SlackPaginationNextCursor,
    SlackUser,
)
from arcade_slack.utils import (
    async_paginate,
    extract_basic_user_info,
    get_available_users_prompt,
    get_users_by_email,
    get_users_by_id,
    get_users_by_username,
    is_user_a_bot,
    is_user_deleted,
)


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_users_info(
    context: ToolContext,
    user_ids: Annotated[list[str], "The IDs of the users to get"],
    usernames: Annotated[list[str], "The usernames of the users to get"],
    emails: Annotated[list[str], "The emails of the users to get"],
) -> Annotated[dict[str, Any], "The users' information"]:
    """Get the information of one or more users in Slack by ID, username, or email.

    Provide one of user_ids, usernames, or emails, not multiple.
    """
    set_args = sum(bool(arg) for arg in [user_ids, usernames, emails])

    if set_args == 0:
        raise ToolExecutionError("At least one of user_ids, usernames, or emails must be provided")
    if set_args > 1:
        raise ToolExecutionError("Only one of user_ids, usernames, or emails can be provided")

    if user_ids:
        return await get_users_by_id(context, user_ids=user_ids)

    if usernames:
        return await get_users_by_username(context, usernames=usernames)

    return await get_users_by_email(context, emails=emails)


# NOTE: This tool is kept here for backwards compatibility.
# Use the `Slack.GetUsersInfo` tool instead.
@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_user_info_by_id(
    context: ToolContext,
    user_id: Annotated[str, "The ID of the user to get"],
) -> Annotated[dict[str, Any], "The user's information"]:
    """Get the information of a user in Slack."""
    slackClient = AsyncWebClient(token=context.get_auth_token_or_empty())

    try:
        response = await slackClient.users_info(user=user_id)
    except SlackApiError as e:
        if e.response.get("error") == "user_not_found":
            additional_prompt_content = await get_available_users_prompt(context)

            raise RetryableToolError(
                "User not found",
                developer_message=f"User with ID '{user_id}' not found.",
                additional_prompt_content=additional_prompt_content,
                retry_after_ms=500,
            )

    user_dict_raw: dict[str, Any] = response.get("user", {}) or {}
    user_dict = cast(SlackUser, user_dict_raw)
    user = SlackUser(**user_dict)
    return dict(**extract_basic_user_info(user))


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def list_users(
    context: ToolContext,
    exclude_bots: Annotated[
        bool | None, "Whether to exclude bots from the results. Defaults to True."
    ] = True,
    limit: Annotated[
        int | None,
        "The maximum number of users to return. Defaults to 200. Maximum is 500.",
    ] = 200,
    next_cursor: Annotated[str | None, "The next cursor token to use for pagination."] = None,
) -> Annotated[dict, "The users' info"]:
    """List all users in the authenticated user's Slack team."""
    limit = max(1, min(limit, 500))
    slackClient = AsyncWebClient(token=context.get_auth_token_or_empty())

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
