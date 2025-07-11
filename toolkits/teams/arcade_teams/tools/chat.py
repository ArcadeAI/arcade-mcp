from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft

from arcade_teams.client import get_client
from arcade_teams.constants import DatetimeField
from arcade_teams.serializers import serialize_chat, serialize_chat_message
from arcade_teams.utils import (
    find_chat_by_users,
    messages_request,
    validate_datetime_range,
)


@tool(requires_auth=Microsoft(scopes=["Chat.Read"]))
async def get_chat_messages(
    context: ToolContext,
    chat_id: Annotated[str, "The ID of the chat to get messages from."],
    user_ids: Annotated[
        list[str] | None, "The IDs of the users in the chat to get messages from."
    ] = None,
    user_names: Annotated[
        list[str] | None,
        "The names of the users in the chat to get messages from. Prefer providing user_ids, "
        "when available, since the performance is better.",
    ] = None,
    start_datetime: Annotated[
        str | None,
        "The start date to filter messages. Provide a string in the format 'YYYY-MM-DD' or "
        "'YYYY-MM-DD HH:MM:SS'. Defaults to None (no start date filter).",
    ] = None,
    end_datetime: Annotated[
        str | None,
        "The end date to filter messages. Provide a string in the format 'YYYY-MM-DD' or "
        "'YYYY-MM-DD HH:MM:SS'. Defaults to None (no end date filter).",
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of messages to return. Defaults to 50, max is 50.",
    ] = 50,
) -> Annotated[
    dict,
    "The messages in the chat/conversation.",
]:
    """Retrieves messages from a chat/conversation filtering by datetime range.

    Provide one of chat_id OR any combination of user_ids and/or user_names. When available, prefer
    providing a chat_id or user_ids for optimal performance.

    Messages will be sorted in descending order by default. Ascending order is not supported by the
    Microsoft Teams API.

    The Microsoft Teams API does not support pagination for this tool.
    """
    limit = min(50, max(1, limit))
    start_datetime, end_datetime = validate_datetime_range(start_datetime, end_datetime)

    datetime_filters = []
    datetime_field = DatetimeField.CREATED

    if start_datetime:
        datetime_filters.append(f"{datetime_field.value} ge {start_datetime}")
    if end_datetime:
        datetime_filters.append(f"{datetime_field.value} le {end_datetime}")

    if datetime_filters:
        filter_clause = " and ".join(datetime_filters)

    if not chat_id:
        chat = await find_chat_by_users(context, user_ids, user_names)
        chat_id = chat["id"]

    client = get_client(context.get_auth_token_or_empty())
    response = await client.chats.by_chat_id(chat_id).messages.get(
        messages_request(
            top=limit,
            order_by=datetime_field.order_by_clause,
            filter=filter_clause,
        )
    )

    messages = [serialize_chat_message(message) for message in response.value]

    return {
        "messages": messages,
        "count": len(messages),
        "chat": {"id": chat_id},
    }


@tool(requires_auth=Microsoft(scopes=["Chat.Read"]))
async def get_chat(
    context: ToolContext,
    chat_id: Annotated[str, "The ID of the chat to get metadata about."],
    user_ids: Annotated[
        list[str] | None, "The IDs of the users in the chat to get messages from."
    ] = None,
    user_names: Annotated[
        list[str] | None,
        "The names of the users in the chat to get messages from. Prefer providing user_ids, "
        "when available, since the performance is better.",
    ] = None,
) -> Annotated[
    dict,
    "Metadata about the conversation (chat or channel).",
]:
    """Retrieves metadata about a conversation (chat or channel).

    Provide exactly one of conversation_id or channel_name. When available, prefer providing a
    conversation_id for optimal performance.
    """
    if not chat_id:
        chat = await find_chat_by_users(context, user_ids, user_names)
        chat_id = chat["id"]

    client = get_client(context.get_auth_token_or_empty())
    response = await client.chats.by_chat_id(chat_id).get()

    return serialize_chat(response.value)
