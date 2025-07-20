from typing import Annotated, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft
from arcade_tdk.errors import ToolExecutionError
from msgraph.generated.models.chat_message import ChatMessage
from msgraph.generated.models.chat_message_type import ChatMessageType
from msgraph.generated.models.item_body import ItemBody

from arcade_teams.client import get_client
from arcade_teams.constants import DatetimeField
from arcade_teams.exceptions import NoItemsFoundError
from arcade_teams.serializers import serialize_chat, serialize_chat_message
from arcade_teams.utils import (
    build_conversation_member,
    build_token_pagination,
    chats_request,
    create_chat_request,
    find_chat_by_users,
    find_humans_by_name,
    messages_request,
    validate_datetime_range,
)


@tool(requires_auth=Microsoft(scopes=["Chat.Read", "Chat.Create"]))
async def get_chat_messages(
    context: ToolContext,
    chat_id: Annotated[str | None, "The ID of the chat to get messages from."] = None,
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
    "The messages in the chat.",
]:
    """Retrieves messages from a Microsoft Teams chat (individual or group).

    Provide one of chat_id OR any combination of user_ids and/or user_names. When available, prefer
    providing a chat_id or user_ids for optimal performance.

    If the user provides user name(s), DO NOT CALL THE `Teams.SearchUsers` or `Teams.SearchPeople`
    tools first. Instead, provide the user name(s) directly to this tool through the `user_names`
    argument. It is not necessary to provide the currently signed in user's name/id, so do not call
    `Teams.GetSignedInUser` before calling this tool.

    Messages will be sorted in descending order by the messages' `created_datetime` field.

    The Microsoft Teams API does not support pagination for this tool.
    """
    if not any([chat_id, user_ids, user_names]):
        message = "At least one of chat_id, user_ids, or user_names must be provided."
        raise ToolExecutionError(message=message, developer_message=message)

    if chat_id and any([user_ids, user_names]):
        message = "chat_id and user_ids/user_names cannot be provided together."
        raise ToolExecutionError(message=message, developer_message=message)

    limit = min(50, max(1, limit))
    start_datetime, end_datetime = validate_datetime_range(start_datetime, end_datetime)

    datetime_filters = []
    datetime_field = DatetimeField.CREATED

    if start_datetime:
        datetime_filters.append(f"{datetime_field.value} ge {start_datetime}")
    if end_datetime:
        datetime_filters.append(f"{datetime_field.value} le {end_datetime}")

    filter_clause = " and ".join(datetime_filters) if datetime_filters else None

    if not chat_id:
        chat = await find_chat_by_users(context, user_ids, user_names)
        chat_id = chat["id"]

    client = get_client(context.get_auth_token_or_empty())
    response = await client.chats.by_chat_id(chat_id).messages.get(
        messages_request(
            top=limit,
            orderby=datetime_field.order_by_clause,
            filter=filter_clause,
        )
    )

    # Unfortunately, the MS Graph API $filter parameter does not support filtering by message type.
    # So we need to filter out non-message items, like systemEventMessage manually.
    messages = [
        serialize_chat_message(message)
        for message in response.value
        if message.message_type == ChatMessageType.Message
    ]

    return {
        "messages": messages,
        "count": len(messages),
        "chat": {"id": chat_id},
    }


@tool(requires_auth=Microsoft(scopes=["Chat.Read"]))
async def get_chat(
    context: ToolContext,
    chat_id: Annotated[str | None, "The ID of the chat to get metadata about."] = None,
    user_ids: Annotated[
        list[str] | None, "The IDs of the users in the chat to get metadata about."
    ] = None,
    user_names: Annotated[
        list[str] | None,
        "The names of the users in the chat to get messages from. Prefer providing user_ids, "
        "when available, since the performance is better.",
    ] = None,
) -> Annotated[
    dict,
    "Metadata about the chat.",
]:
    """Retrieves metadata about a Microsoft Teams chat.

    Provide exactly one of chat_id or user_ids/user_names. When available, prefer providing a
    chat_id or user_ids for optimal performance.
    """
    if not chat_id:
        return {"chat": await find_chat_by_users(context, user_ids, user_names)}

    client = get_client(context.get_auth_token_or_empty())
    response = await client.chats.by_chat_id(chat_id).get()

    return {"chat": serialize_chat(response)}


@tool(requires_auth=Microsoft(scopes=["Chat.Read"]))
async def list_chats(
    context: ToolContext,
    limit: Annotated[int, "The maximum number of chats to return. Defaults to 50, max is 50."] = 50,
    next_page_token: Annotated[
        str | None, "The token to use to get the next page of results."
    ] = None,
) -> Annotated[dict, "The chats to which the current user is a member of."]:
    """List the Microsoft Teams chats to which the current user is a member of."""
    limit = min(50, max(1, limit))

    client = get_client(context.get_auth_token_or_empty())

    response = await client.me.chats.get(
        chats_request(
            top=limit,
            next_page_token=next_page_token,
            expand=["members", "lastMessagePreview"],
        )
    )

    chats = [serialize_chat(chat) for chat in response.value]

    return {
        "chats": chats,
        "count": len(chats),
        "pagination": build_token_pagination(response),
    }


@tool(requires_auth=Microsoft(scopes=["ChatMessage.Send"]))
async def send_message_to_chat(
    context: ToolContext,
    message: Annotated[str, "The message to send to the chat."],
    chat_id: Annotated[str | None, "The ID of the chat to get messages from."] = None,
    user_ids: Annotated[
        list[str] | None, "The IDs of the users in the chat to get messages from."
    ] = None,
    user_names: Annotated[
        list[str] | None,
        "The names of the users in the chat to get messages from. Prefer providing user_ids, "
        "when available, since the performance is better.",
    ] = None,
) -> Annotated[dict, "The message that was sent."]:
    """Sends a message to a Microsoft Teams chat.

    Provide exactly one of chat_id or user_ids/user_names. When available, prefer providing a
    chat_id or user_ids for optimal performance.
    """
    if not chat_id:
        try:
            chat = await find_chat_by_users(context, user_ids, user_names)
            chat_id = chat["id"]
        except NoItemsFoundError:
            chat = await create_chat(context, user_ids, user_names)
            chat_id = chat["id"]

    client = get_client(context.get_auth_token_or_empty())
    response = await client.chats.by_chat_id(chat_id).messages.post(
        ChatMessage(body=ItemBody(content=message))
    )
    return {
        "status": "Message successfully sent.",
        "message": serialize_chat_message(response),
    }


@tool(requires_auth=Microsoft(scopes=["Chat.Create"]))
async def create_chat(
    context: ToolContext,
    user_ids: Annotated[list[str] | None, "The IDs of the users to create a chat with."] = None,
    user_names: Annotated[list[str] | None, "The names of the users to create a chat with."] = None,
) -> Annotated[dict, "The chat that was created."]:
    """Creates a Microsoft Teams chat.

    If the chat already exists with the specified members, the MS Graph API will return the
    existing chat.

    Provide any combination of user_ids and/or user_names. When available, prefer providing
    user_ids for optimal performance.
    """
    if not any([user_ids, user_names]):
        message = "At least one of user_ids or user_names must be provided."
        raise ToolExecutionError(message=message, developer_message=message)

    user_ids = cast(list[str], user_ids or [])

    if user_names:
        humans = await find_humans_by_name(context, user_names)
        user_ids.extend([human["id"] for human in humans["found"]])

    client = get_client(context.get_auth_token_or_empty())
    response = await client.chats.post(
        create_chat_request(
            members=[build_conversation_member(user_id=user_id) for user_id in user_ids]
        )
    )

    return {"chat": serialize_chat(response)}
