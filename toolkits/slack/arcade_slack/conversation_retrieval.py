import json
from collections.abc import Callable
from typing import cast

from arcade_tdk import ToolContext
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.models import (
    ConcurrencySafeCoroutineCaller,
    ConversationType,
    FindChannelByNameSentinel,
)
from arcade_slack.utils import (
    async_paginate,
    extract_conversation_metadata,
    filter_conversations_by_user_ids,
    gather_with_concurrency_limit,
)


async def get_conversation_by_id(
    context: ToolContext,
    conversation_id: str,
) -> dict:
    """Get metadata of a conversation in Slack by the conversation_id."""
    try:
        slackClient = AsyncWebClient(token=context.get_auth_token_or_empty())
        response = await slackClient.conversations_info(
            channel=conversation_id,
            include_locale=True,
            include_num_members=True,
        )
        return dict(**extract_conversation_metadata(response["channel"]))

    except SlackApiError as e:
        slack_error = cast(str, e.response.get("error", ""))
        if "not_found" in slack_error.lower():
            message = f"Conversation with ID '{conversation_id}' not found."
            raise ToolExecutionError(message=message, developer_message=message)
        raise


async def get_conversations_by_user_ids(
    list_conversations_func: Callable,
    get_members_in_conversation_func: Callable,
    context: ToolContext,
    conversation_types: list[ConversationType],
    user_ids: list[str],
    exact_match: bool = False,
    limit: int | None = None,
    next_cursor: str | None = None,
) -> list[dict]:
    """
    Retrieve conversations filtered by the given user IDs. Includes pagination support
    and optionally limits the number of returned conversations.
    """
    conversations_found: list[dict] = []

    response = await list_conversations_func(
        context=context,
        conversation_types=conversation_types,
        next_cursor=next_cursor,
    )

    # Associate members to each conversation
    conversations_with_members = await associate_members_of_multiple_conversations(
        get_members_in_conversation_func, response["conversations"], context
    )

    conversations_found.extend(
        filter_conversations_by_user_ids(conversations_with_members, user_ids, exact_match)
    )

    return conversations_found if not limit else conversations_found[:limit]


async def associate_members_of_conversation(
    get_members_in_conversation_func: Callable,
    context: ToolContext,
    conversation: dict,
) -> dict:
    response = await get_members_in_conversation_func(context, conversation["id"])
    conversation["members"] = response["members"]
    return conversation


async def associate_members_of_multiple_conversations(
    get_members_in_conversation_func: Callable,
    conversations: list[dict],
    context: ToolContext,
) -> list[dict]:
    """Associate members to each conversation, returning the updated list."""
    results = await gather_with_concurrency_limit([
        ConcurrencySafeCoroutineCaller(
            associate_members_of_conversation,
            get_members_in_conversation_func,
            context,
            conversation,
        )
        for conversation in conversations
    ])

    return cast(list[dict], results)


async def get_channel_by_name(
    context: ToolContext,
    channel_name: str,
) -> dict:
    from arcade_slack.tools.chat import list_conversations_metadata

    results = await async_paginate(
        context=context,
        func=list_conversations_metadata,
        conversation_types=[ConversationType.PUBLIC_CHANNEL, ConversationType.PRIVATE_CHANNEL],
        response_key="conversations",
        sentinel=FindChannelByNameSentinel(channel_name),
    )

    available_channels = []

    for result in results:
        channel = dict(**extract_conversation_metadata(result))
        if channel["name"].casefold() == channel_name.casefold():
            return channel
        else:
            available_channels.append({"id": channel["id"], "name": channel["name"]})

    error_message = f"Channel with name '{channel_name}' not found."

    raise RetryableToolError(
        message=error_message,
        developer_message=error_message,
        additional_prompt_content=f"Available channels: {json.dumps(available_channels)}",
        retry_after_ms=500,
    )
