import asyncio
from typing import Any

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.constants import MAX_CONCURRENT_REQUESTS, MAX_PAGINATION_TIMEOUT_SECONDS
from arcade_slack.models import (
    ConcurrencySafeCoroutineCaller,
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
) -> list[dict]:
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

    if user_ids:
        user_retrieval_calls.append(get_users_by_id(context, user_ids, semaphore))

    if usernames:
        user_retrieval_calls.append(get_users_by_username(context, usernames, semaphore))

    if emails:
        user_retrieval_calls.append(get_users_by_email(context, emails, semaphore))

    responses = await asyncio.gather(*user_retrieval_calls)

    return build_multiple_users_retrieval_response(users_responses=responses)


async def get_users_by_id(
    context: ToolContext,
    user_ids: list[str],
    semaphore: asyncio.Semaphore | None = None,
) -> dict[str, list[dict]]:
    if len(user_ids) == 0:
        from arcade_slack.tools.users import get_user_info_by_id  # Avoid circular import

        user = await get_user_info_by_id(context, user_id=user_ids[0])
        return {"users": [user]}

    responses = await gather_with_concurrency_limit(
        coroutine_callers=[
            ConcurrencySafeCoroutineCaller(get_user_info_by_id, context, user_id)
            for user_id in user_ids
        ],
        semaphore=semaphore,
    )

    return {"users": [response["user"] for response in responses]}


async def get_users_by_username(
    context: ToolContext,
    usernames: list[str],
    semaphore: asyncio.Semaphore | None = None,
) -> dict[str, list[dict]]:
    if not semaphore:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    slack_client = AsyncWebClient(token=context.get_auth_token_or_empty())

    async with semaphore:
        users, _ = await async_paginate(
            slack_client.users_list,
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
            users_found.append(cast_user_dict(user))
            usernames_pending.remove(user["name"])
        elif not is_user_a_bot(user):
            available_users.append(short_user_info(user))

    response: dict[str, Any] = {"users": users_found}

    if usernames_pending:
        response["usernames_not_found"] = list(usernames_pending)
        response["other_available_users"] = available_users

    return response


async def get_users_by_email(
    context: ToolContext,
    emails: list[str],
    semaphore: asyncio.Semaphore | None = None,
) -> dict[str, list[dict]]:
    for email in emails:
        if not is_valid_email(email):
            raise ToolExecutionError(f"Invalid email address: {email}")

    slack_client = AsyncWebClient(token=context.get_auth_token_or_empty())
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
        response["emails_not_found"] = emails_not_found

    return response
