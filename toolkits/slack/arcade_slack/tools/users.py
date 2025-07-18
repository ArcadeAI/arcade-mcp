from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Slack
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.constants import MAX_PAGINATION_TIMEOUT_SECONDS
from arcade_slack.models import (
    SlackPaginationNextCursor,
)
from arcade_slack.user_retrieval import get_users_by_id_username_or_email
from arcade_slack.utils import (
    async_paginate,
    extract_basic_user_info,
    is_user_a_bot,
    is_user_deleted,
)


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_users_info(
    context: ToolContext,
    user_ids: Annotated[list[str] | None, "The IDs of the users to get"] = None,
    usernames: Annotated[
        list[str] | None,
        "The usernames of the users to get. Prefer retrieving by user_ids and/or emails, "
        "when available, since the performance is better.",
    ] = None,
    emails: Annotated[list[str] | None, "The emails of the users to get"] = None,
) -> Annotated[dict[str, Any], "The users' information"]:
    """Get the information of one or more users in Slack by ID, username, and/or email.

    Provide any combination of user_ids, usernames, and/or emails. If you need to retrieve
    data about multiple users, DO NOT CALL THE TOOL MULTIPLE TIMES. Instead, call it once
    with all the user_ids, usernames, and/or emails. IF YOU CALL THIS TOOL MULTIPLE TIMES
    UNNECESSARILY, YOU WILL RELEASE MORE CO2 IN THE ATMOSPHERE AND CONTRIBUTE TO GLOBAL WARMING.

    If you need to get metadata or messages of a conversation, use the
    `Slack.GetConversationMetadata` or `Slack.GetMessages` tool instead. These
    tools accept user_ids, usernames, and/or emails. Do not retrieve users' info first,
    as it is inefficient, releases more CO2 in the atmosphere, and contributes to climate change.
    """
    users = await get_users_by_id_username_or_email(context, user_ids, usernames, emails)
    return {"users": users}


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def list_users(
    context: ToolContext,
    exclude_bots: Annotated[
        bool | None, "Whether to exclude bots from the results. Defaults to True."
    ] = True,
    limit: Annotated[
        int,
        # The user object is relatively small, so we allow a higher limit than the default of 200.
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
    slack_client = AsyncWebClient(token=context.get_auth_token_or_empty())

    users, next_cursor = await async_paginate(
        func=slack_client.users_list,
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
    users = await get_users_info(context, user_ids=[user_id])
    return cast(dict[str, Any], users["users"][0])
