import asyncio
from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Slack
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.constants import MAX_CONCURRENT_REQUESTS, MAX_PAGINATION_TIMEOUT_SECONDS
from arcade_slack.exceptions import UsernameNotFoundError
from arcade_slack.models import (
    FindMultipleUsersByUsernameSentinel,
    FindUserByUsernameSentinel,
    SlackPaginationNextCursor,
    SlackUser,
)
from arcade_slack.utils import (
    async_paginate,
    extract_basic_user_info,
    is_user_a_bot,
    is_user_deleted,
    is_valid_email,
    short_human_users_info,
    short_user_info,
)


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
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


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def list_users(
    context: ToolContext,
    exclude_bots: Annotated[bool | None, "Whether to exclude bots from the results"] = True,
    limit: Annotated[
        int | None,
        "The maximum number of users to return. If a limit is not provided, the tool "
        "will paginate until it gets all users or a timeout threshold is reached.",
    ] = None,
    next_cursor: Annotated[str | None, "The next cursor token to use for pagination."] = None,
) -> Annotated[dict, "The users' info"]:
    """List all users in the authenticated user's Slack team."""
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


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_user_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the user (case-insensitive match)."],
) -> Annotated[dict, "The user's info"]:
    """Get a single user by their username.

    This tool will paginate the list of all users until it finds the user or a timeout threshold
    is reached. If you have a user email, use the `Slack.GetUserByEmail` tool instead, which is
    more efficient.
    """
    if not username:
        raise ToolExecutionError("No username provided")

    slackClient = AsyncWebClient(token=context.get_auth_token_or_empty())

    users, _ = await async_paginate(
        slackClient.users_list,
        "members",
        max_pagination_timeout_seconds=MAX_PAGINATION_TIMEOUT_SECONDS,
        sentinel=FindUserByUsernameSentinel(username=username),
    )

    for user in users:
        if user["name"].casefold() == username.casefold():
            return {"user": extract_basic_user_info(user)}

    raise UsernameNotFoundError(
        username=username,
        available_users=short_human_users_info(users),
    )


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_multiple_users_by_username(
    context: ToolContext,
    usernames: Annotated[list[str], "The usernames of the users (case-insensitive match)."],
) -> Annotated[dict, "The users' info"]:
    """Get multiple users by their usernames.

    This tool will paginate the list of all users until it finds the users or a timeout threshold
    is reached. If you have the users' email addresses, use the `Slack.GetMultipleUsersByEmail` tool
    instead, which is more efficient.
    """
    if not usernames:
        raise ToolExecutionError("No usernames provided")

    slackClient = AsyncWebClient(token=context.get_auth_token_or_empty())

    users, _ = await async_paginate(
        slackClient.users_list,
        "members",
        max_pagination_timeout_seconds=MAX_PAGINATION_TIMEOUT_SECONDS,
        sentinel=FindMultipleUsersByUsernameSentinel(usernames=usernames),
    )

    users_found = []
    usernames_pending = set(usernames)
    usernames_lower = {username.casefold() for username in usernames}
    available_users = []

    for user in users:
        if not isinstance(user.get("name"), str):
            continue
        if user["name"].casefold() in usernames_lower:
            users_found.append(extract_basic_user_info(user))
            usernames_pending.remove(user["name"])
        elif not is_user_a_bot(user):
            available_users.append(short_user_info(user))

    response: dict[str, Any] = {"users": users_found}

    if usernames_pending:
        response["usernames_not_found"] = list(usernames_pending)
        response["other_available_users"] = available_users

    return response


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_user_by_email(
    context: ToolContext,
    email: Annotated[str, "The email of the user to get"],
) -> Annotated[dict, "The user's info"]:
    """Get a user by their email address."""
    if not is_valid_email(email):
        raise ToolExecutionError(f"Invalid email address: {email}")

    slackClient = AsyncWebClient(token=context.get_auth_token_or_empty())

    try:
        response = await slackClient.users_lookupByEmail(email=email)
    except SlackApiError as e:
        if e.response.get("error") in ["user_not_found", "users_not_found"]:
            users = await list_users(context)
            available_users = [
                {"name": user["name"], "id": user["id"], "email": user.get("email")}
                for user in users["users"]
                if user.get("name")
            ]
            err_msg = f"User with email '{email}' not found."
            raise RetryableToolError(
                err_msg,
                developer_message=err_msg,
                additional_prompt_content=f"Available users: {available_users}",
                retry_after_ms=500,
            )
        else:
            raise
    else:
        return {"user": cast(dict, extract_basic_user_info(SlackUser(**response["user"])))}


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_multiple_users_by_email(
    context: ToolContext,
    emails: Annotated[list[str], "The emails of the users to get"],
) -> Annotated[dict, "The users' info"]:
    """Get multiple users by their email addresses."""
    if not emails:
        raise ToolExecutionError("No emails provided")

    for email in emails:
        if not is_valid_email(email):
            raise ToolExecutionError(f"Invalid email address: {email}")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def safe_get_user_by_email(email: str) -> dict[str, Any]:
        async with semaphore:
            try:
                result = await get_user_by_email(context=context, email=email)
                return {"email": email, "user": result["user"]}
            except RetryableToolError:
                return {"email": email, "user": None}

    results = await asyncio.gather(*[safe_get_user_by_email(email) for email in emails if email])

    users = []
    emails_not_found = []

    for result in results:
        if result["user"]:
            users.append(result["user"])
        else:
            emails_not_found.append(result["email"])

    response: dict[str, Any] = {"users": users}

    if emails_not_found:
        response["emails_not_found"] = emails_not_found

    return response
