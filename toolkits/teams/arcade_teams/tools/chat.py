from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft

from arcade_teams.client import get_client
from arcade_teams.constants import DatetimeField
from arcade_teams.utils import messages_request, validate_datetime_range


@tool(requires_auth=Microsoft(scopes=["Chat.Read"]))
async def list_messages_in_chat_by_id(
    context: ToolContext,
    chat_id: Annotated[str, "The ID of the chat to list the members of."],
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
    datetime_field: Annotated[
        DatetimeField,
        "Which field to filter by start_datetime and end_datetime. Defaults to 'createdDateTime'. "
        "The results will also be ordered by this field in descending order. Ascending order is "
        "not supported.",
    ] = DatetimeField.CREATED,
    limit: Annotated[
        int,
        "The maximum number of messages to return. Defaults to 50, max is 50.",
    ] = 50,
) -> Annotated[
    dict,
    "The messages in the chat (this tool does not support pagination).",
]:
    """Lists the messages in a chat."""
    limit = min(50, max(1, limit))
    start_datetime, end_datetime = validate_datetime_range(start_datetime, end_datetime)

    datetime_filters = []

    if start_datetime:
        datetime_filters.append(f"{datetime_field.value} ge {start_datetime}")
    if end_datetime:
        datetime_filters.append(f"{datetime_field.value} le {end_datetime}")

    if datetime_filters:
        filter_clause = " and ".join(datetime_filters)

    client = get_client(context.get_auth_token_or_empty())
    response = await client.chats.by_chat_id(chat_id).messages.get(
        messages_request(
            top=limit,
            order_by=datetime_field.order_by_clause,
            filter=filter_clause,
        )
    )

    return {"messages": response["value"]}
