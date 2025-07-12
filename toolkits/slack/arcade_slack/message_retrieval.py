from datetime import datetime, timezone
from typing import Any

from arcade_tdk.errors import ToolExecutionError
from slack_sdk.web.async_client import AsyncWebClient

from arcade_slack.utils import (
    async_paginate,
    convert_datetime_to_unix_timestamp,
    convert_relative_datetime_to_unix_timestamp,
    enrich_message_datetime,
)


async def retrieve_messages_in_conversation(
    conversation_id: str,
    auth_token: str | None = None,
    oldest_relative: str | None = None,
    latest_relative: str | None = None,
    oldest_datetime: str | None = None,
    latest_datetime: str | None = None,
    limit: int | None = None,
    next_cursor: str | None = None,
) -> dict:
    error_message = None
    if oldest_datetime and oldest_relative:
        error_message = "Cannot specify both 'oldest_datetime' and 'oldest_relative'."

    if latest_datetime and latest_relative:
        error_message = "Cannot specify both 'latest_datetime' and 'latest_relative'."

    if error_message:
        raise ToolExecutionError(error_message, developer_message=error_message)

    current_unix_timestamp = int(datetime.now(timezone.utc).timestamp())

    if latest_relative:
        latest_timestamp = convert_relative_datetime_to_unix_timestamp(
            latest_relative, current_unix_timestamp
        )
    elif latest_datetime:
        latest_timestamp = convert_datetime_to_unix_timestamp(latest_datetime)
    else:
        latest_timestamp = None

    if oldest_relative:
        oldest_timestamp = convert_relative_datetime_to_unix_timestamp(
            oldest_relative, current_unix_timestamp
        )
    elif oldest_datetime:
        oldest_timestamp = convert_datetime_to_unix_timestamp(oldest_datetime)
    else:
        oldest_timestamp = None

    datetime_args: dict[str, Any] = {}
    if oldest_timestamp:
        datetime_args["oldest"] = oldest_timestamp
    if latest_timestamp:
        datetime_args["latest"] = latest_timestamp

    slackClient = AsyncWebClient(token=auth_token)

    response, next_cursor = await async_paginate(
        slackClient.conversations_history,
        "messages",
        limit=limit,
        next_cursor=next_cursor,
        channel=conversation_id,
        include_all_metadata=True,
        inclusive=True,  # Include messages at the start and end of the time range
        **datetime_args,
    )

    messages = [enrich_message_datetime(message) for message in response]

    return {"messages": messages, "next_cursor": next_cursor}
