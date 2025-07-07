import json
from typing import cast

from arcade_tdk import ToolContext
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.models import (
    ConversationType,
    FindChannelByNameSentinel,
)
from arcade_slack.utils import (
    async_paginate,
    extract_conversation_metadata,
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
        sentinel=FindChannelByNameSentinel(channel_name.lstrip("#")),
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
