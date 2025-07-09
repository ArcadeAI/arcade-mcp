import json
from typing import cast

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
    auth_token: str,
    conversation_id: str,
) -> dict:
    """Get metadata of a conversation in Slack by the conversation_id."""
    try:
        slack_client = AsyncWebClient(token=auth_token)
        response = await slack_client.conversations_info(
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
    auth_token: str,
    channel_name: str,
) -> dict:
    channel_name_casefolded = channel_name.lstrip("#").casefold()

    slack_client = AsyncWebClient(token=auth_token)

    results, _ = await async_paginate(
        func=slack_client.conversations_list,
        response_key="channels",
        types=",".join([
            ConversationType.PUBLIC_CHANNEL.value,
            ConversationType.PRIVATE_CHANNEL.value,
        ]),
        exclude_archived=True,
        sentinel=FindChannelByNameSentinel(channel_name_casefolded),
    )

    available_channels = []

    for channel in results:
        if channel["name"].casefold() == channel_name_casefolded:
            return dict(**extract_conversation_metadata(channel))
        else:
            available_channels.append({"id": channel["id"], "name": channel["name"]})

    error_message = f"Channel with name '{channel_name}' not found."

    raise RetryableToolError(
        message=error_message,
        developer_message=error_message,
        additional_prompt_content=f"Available channels: {json.dumps(available_channels)}",
        retry_after_ms=500,
    )
