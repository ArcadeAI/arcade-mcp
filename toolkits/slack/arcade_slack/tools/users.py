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
    get_available_users_prompt,
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


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_multiple_users_by_username(
    context: ToolContext,
    usernames: Annotated[list[str], "The usernames of the users (case-insensitive match)."],
) -> Annotated[dict, "The users' info"]:
    """Get multiple users by their usernames.

    This tool will paginate the list of all users until it finds the users or a timeout threshold
    is reached. If you have the users' email addresses, use the `Slack.GetMultipleUsersByEmail` tool
    instead, which is more efficient.

    IF YOU NEED TO RETRIEVE MESSAGES EXCHANGED WITH CERTAIN USERS, DO NOT CALL THIS TOOL FIRST.
    PROVIDE THE USERNAMES DIRECTLY TO THE MESSAGE RETRIEVING TOOL. IF YOU CALL THIS TOOL FIRST,
    YOU WILL GENERATE TOO MUCH CO2 AND CONTRIBUTE TO CLIMATE CHANGE ON PLANET EARTH.
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
            users_found.append(cast(dict, extract_basic_user_info(SlackUser(**user))))
            usernames_pending.remove(user["name"])
        elif not is_user_a_bot(user):
            available_users.append(short_user_info(user))

    response: dict[str, Any] = {"users": users_found}

    if usernames_pending:
        response["usernames_not_found"] = list(usernames_pending)
        response["other_available_users"] = available_users

    return response


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_multiple_users_by_email(
    context: ToolContext,
    emails: Annotated[list[str], "The emails of the users to get"],
) -> Annotated[dict, "The users' info"]:
    """Get multiple users by their email addresses.

    IF YOU NEED TO RETRIEVE MESSAGES EXCHANGED WITH CERTAIN USERS, DO NOT CALL THIS TOOL FIRST.
    PROVIDE THE EMAIL ADDRESSES DIRECTLY TO THE MESSAGE RETRIEVING TOOL. IF YOU CALL THIS TOOL
    FIRST, YOU WILL GENERATE TOO MUCH CO2 AND CONTRIBUTE TO CLIMATE CHANGE ON PLANET EARTH.
    """
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


@tool(requires_auth=Slack(scopes=["users:read", "users:read.email"]))
async def get_user_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the user (case-insensitive match)."],
) -> Annotated[dict, "The user's info"]:
    """Get a single user by their username.

    This tool will paginate the list of all users until it finds the user or a timeout threshold
    is reached. If you have a user email, use the `Slack.GetUserByEmail` tool instead, which is
    more efficient.

    IF YOU HAVE MULTIPLE USERS TO RETRIEVE, USE THE `Slack.GetMultipleUsersByUsername` TOOL INSTEAD,
    SINCE IT'S MORE EFFICIENT AND RELEASES LESS CO2 IN THE ATMOSPHERE. IF YOU CALL THIS TOOL
    MULTIPLE TIMES UNNECESSARILY, YOU WILL CONTRIBUTE TO CLIMATE CHANGE ON PLANET EARTH.

    IF YOU NEED TO RETRIEVE MESSAGES EXCHANGED WITH A CERTAIN USER, DO NOT CALL THIS TOOL FIRST.
    PROVIDE THE USERNAME DIRECTLY TO THE MESSAGE RETRIEVING TOOL. IF YOU CALL THIS TOOL FIRST,
    YOU WILL GENERATE TOO MUCH CO2 AND CONTRIBUTE TO CLIMATE CHANGE ON PLANET EARTH.
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
async def get_user_by_email(
    context: ToolContext,
    email: Annotated[str, "The email of the user to get"],
) -> Annotated[dict, "The user's info"]:
    """Get a user by their email address.

    IF YOU HAVE MULTIPLE USERS TO RETRIEVE, USE THE `Slack.GetMultipleUsersByEmail` TOOL INSTEAD,
    SINCE IT'S MORE EFFICIENT AND RELEASES LESS CO2 IN THE ATMOSPHERE. IF YOU CALL THIS TOOL
    MULTIPLE TIMES UNNECESSARILY, YOU WILL CONTRIBUTE TO CLIMATE CHANGE ON PLANET EARTH.

    IF YOU NEED TO RETRIEVE MESSAGES EXCHANGED WITH A CERTAIN USER, DO NOT CALL THIS TOOL FIRST.
    PROVIDE THE EMAIL ADDRESS DIRECTLY TO THE MESSAGE RETRIEVING TOOL. IF YOU CALL THIS TOOL FIRST,
    YOU WILL GENERATE TOO MUCH CO2 AND CONTRIBUTE TO CLIMATE CHANGE ON PLANET EARTH.
    """
    if not is_valid_email(email):
        raise ToolExecutionError(f"Invalid email address: {email}")

    slackClient = AsyncWebClient(token=context.get_auth_token_or_empty())

    try:
        response = await slackClient.users_lookupByEmail(email=email)
    except SlackApiError as e:
        if e.response.get("error") in ["user_not_found", "users_not_found"]:
            err_msg = f"User with email '{email}' not found."
            additional_prompt_content = await get_available_users_prompt(context)
            raise RetryableToolError(
                message=err_msg,
                developer_message=err_msg,
                additional_prompt_content=additional_prompt_content,
                retry_after_ms=500,
            )
        else:
            raise ToolExecutionError(
                message="Error getting user by email",
                developer_message=f"Error getting user by email: {e.response.get('error')}",
            )
    else:
        return {"user": cast(dict, extract_basic_user_info(SlackUser(**response["user"])))}
