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
from arcade_slack.user_retrieval import get_users_by_id_username_or_email
from arcade_slack.utils import (
    async_paginate,
    extract_basic_user_info,
    get_available_users_prompt,
    is_user_a_bot,
    is_user_deleted,
)


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_users_info(
    context: ToolContext,
    user_ids: Annotated[list[str] | None, "The IDs of the users to get"] = None,
    usernames: Annotated[list[str] | None, "The usernames of the users to get"] = None,
    emails: Annotated[list[str] | None, "The emails of the users to get"] = None,
) -> Annotated[dict[str, Any], "The users' information"]:
    """Get the information of one or more users in Slack by ID, username, and/or email.

    Provide any combination of user_ids, usernames, and/or emails. If you need to retrieve
    data about multiple users, DO NOT CALL THE TOOL MULTIPLE TIMES. Instead, call it once
    with all the user_ids, usernames, and/or emails. IF YOU CALL THIS TOOL MULTIPLE TIMES
    UNNECESSARILY, YOU WILL RELEASE MORE CO2 IN THE ATMOSPHERE AND CONTRIBUTE TO GLOBAL WARMING.

    If you need to get metadata or messages of a conversation, use the
    `Slack.GetConversationMetadata` tool or `Slack.GetMessages` tool instead. These
    tools accept a user_id, username, and/or email. Do not retrieve users' info first,
    as it is inefficient and releases more CO2 in the atmosphere, contributing to climate change.
    """
    return {"users": await get_users_by_id_username_or_email(context, user_ids, usernames, emails)}


# NOTE: This tool is kept here for backwards compatibility.
# Use the `Slack.GetUsersInfo` tool instead.
@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_user_info_by_id(
    context: ToolContext,
    user_id: Annotated[str, "The ID of the user to get"],
) -> Annotated[dict[str, Any], "The user's information"]:
    """Get the information of a user in Slack.

    This tool is deprecated. Use the `Slack.GetUsersInfo` tool instead.
    """
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
        else:
            raise ToolExecutionError(
                message="There was an error getting the user info.",
                developer_message=(
                    "Error getting the user info: "
                    f"{e.response.get('error', 'Unknown Slack API error')}"
                ),
            ) from e

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
    """List all users in the authenticated user's Slack team.

    If you need to get metadata or messages of a conversation, use the
    `Slack.GetConversationMetadata` tool or `Slack.GetMessages` tool instead. These
    tools accept a user_id, username, and/or email. Do not use this tool to first retrieve user(s),
    as it is inefficient and releases more CO2 in the atmosphere, contributing to climate change.
    """
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
