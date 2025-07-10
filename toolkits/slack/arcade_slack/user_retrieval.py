import asyncio
from typing import Any, cast

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.constants import MAX_CONCURRENT_REQUESTS, MAX_PAGINATION_TIMEOUT_SECONDS
from arcade_slack.models import (
    FindMultipleUsersByIdSentinel,
    FindMultipleUsersByUsernameSentinel,
    GetUserByEmailCaller,
)
from arcade_slack.utils import (
    async_paginate,
    build_multiple_users_retrieval_response,
    cast_user_dict,
    gather_with_concurrency_limit,
    is_user_a_bot,
    is_valid_email,
    short_user_info,
)


async def get_users_by_id_username_or_email(
    context: ToolContext,
    user_ids: str | list[str] | None = None,
    usernames: str | list[str] | None = None,
    emails: str | list[str] | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> list[dict[str, Any]]:
    """Get the metadata of a user by their ID, username, or email.

    Provide any combination of user_ids, usernames, and/or emails. Always prefer providing user_ids
    and/or emails, when available, since the performance is better.
    """
    if isinstance(user_ids, str):
        user_ids = [user_ids]
    if isinstance(usernames, str):
        usernames = [usernames]
    if isinstance(emails, str):
        emails = [emails]

    if not any([user_ids, usernames, emails]):
        raise ToolExecutionError("At least one of user_ids, usernames, or emails must be provided")

    if not semaphore:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    user_retrieval_calls = []

    auth_token = context.get_auth_token_or_empty()

    if user_ids:
        user_retrieval_calls.append(get_users_by_id(auth_token, user_ids, semaphore))

    if usernames:
        user_retrieval_calls.append(get_users_by_username(auth_token, usernames, semaphore))

    if emails:
        user_retrieval_calls.append(get_users_by_email(auth_token, emails, semaphore))

    responses = await asyncio.gather(*user_retrieval_calls)

    return await build_multiple_users_retrieval_response(context, responses)


async def get_users_by_id(
    auth_token: str,
    user_ids: list[str],
    semaphore: asyncio.Semaphore | None = None,
) -> dict[str, list]:
    user_ids = list(set(user_ids))

    if len(user_ids) == 1:
        user = await get_single_user_by_id(auth_token, user_ids[0])
        if not user:
            return {"users": [], "not_found": user_ids}
        else:
            return {"users": [user], "not_found": []}

    if not semaphore:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async with semaphore:
        slack_client = AsyncWebClient(token=auth_token)
        response, _ = await async_paginate(
            func=slack_client.users_list,
            response_key="members",
            sentinel=FindMultipleUsersByIdSentinel(user_ids=user_ids),
        )

    user_ids_pending = set(user_ids)
    users = []

    for user in response:
        user_dict = cast(dict, user)
        if user_dict["id"] in user_ids_pending:
            users.append(cast_user_dict(user_dict))
            user_ids_pending.remove(user_dict["id"])

    return {"users": users, "not_found": list(user_ids_pending)}


async def get_single_user_by_id(auth_token: str, user_id: str) -> dict[str, Any] | None:
    slack_client = AsyncWebClient(token=auth_token)
    try:
        response = await slack_client.users_info(user=user_id)
        if not response.get("ok"):
            return None
        return cast_user_dict(response["user"])
    except SlackApiError as e:
        if "not_found" in e.response.get("error", ""):
            return None
        else:
            message = f"There was an error getting the user with ID {user_id}."
            slack_error_message = e.response.get("error", "Unknown Slack API error")
            raise ToolExecutionError(
                message=message,
                developer_message=f"{message}: {slack_error_message}",
            ) from e


async def get_users_by_username(
    auth_token: str,
    usernames: list[str],
    semaphore: asyncio.Semaphore | None = None,
) -> dict[str, list[dict]]:
    usernames = list(set(usernames))

    if not semaphore:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    slack_client = AsyncWebClient(token=auth_token)

    async with semaphore:
        users, _ = await async_paginate(
            func=slack_client.users_list,
            response_key="members",
            max_pagination_timeout_seconds=MAX_PAGINATION_TIMEOUT_SECONDS,
            sentinel=FindMultipleUsersByUsernameSentinel(usernames=usernames),
        )

    users_found = []
    usernames_lower = {username.casefold() for username in usernames}
    usernames_pending = set(usernames)
    available_users = []

    for user in users:
        if is_user_a_bot(user):
            continue

        available_users.append(short_user_info(user))

        if not isinstance(user.get("name"), str):
            continue

        username_lower = user["name"].casefold()

        if username_lower in usernames_lower:
            users_found.append(cast_user_dict(user))
            # Username/handle is unique in Slack, we can ignore it after finding a match
            for pending_username in usernames_pending:
                if pending_username.casefold() == username_lower:
                    usernames_pending.remove(pending_username)
                    break

    response: dict[str, Any] = {"users": users_found}

    if usernames_pending:
        response["not_found"] = list(usernames_pending)
        response["available_users"] = available_users

    return response


async def get_users_by_email(
    auth_token: str,
    emails: list[str],
    semaphore: asyncio.Semaphore | None = None,
) -> dict[str, list[dict]]:
    emails = list(set(emails))

    for email in emails:
        if not is_valid_email(email):
            raise ToolExecutionError(f"Invalid email address: {email}")

    if not semaphore:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    slack_client = AsyncWebClient(token=auth_token)
    callers = [GetUserByEmailCaller(slack_client.users_lookupByEmail, email) for email in emails]

    results = await gather_with_concurrency_limit(
        coroutine_callers=callers,
        semaphore=semaphore,
    )

    users = []
    emails_not_found = []

    for result in results:
        if result["user"]:
            users.append(cast_user_dict(result["user"]))
        else:
            emails_not_found.append(result["email"])

    response: dict[str, Any] = {"users": users}

    if emails_not_found:
        response["not_found"] = emails_not_found

    return response
