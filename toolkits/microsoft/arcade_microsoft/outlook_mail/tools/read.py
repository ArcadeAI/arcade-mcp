from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft
from arcade_tdk.errors import ToolExecutionError

from arcade_microsoft.client import get_client
from arcade_microsoft.outlook_mail._utils import (
    fetch_emails,
    prepare_list_emails_request_config,
    remove_none_values,
)
from arcade_microsoft.outlook_mail.enums import (
    EmailFilterProperty,
    FilterOperator,
    WellKnownFolderNames,
)
from arcade_microsoft.outlook_mail.message import Message


@tool(requires_auth=Microsoft(scopes=["Mail.Read"]))
async def list_emails(
    context: ToolContext,
    limit: Annotated[int, "The number of messages to return. Max is 100. Defaults to 5."] = 5,
    pagination_token: Annotated[
        str | None, "The pagination token to continue a previous request"
    ] = None,
) -> Annotated[dict, "A dictionary containing a list of emails"]:
    """List emails in the user's mailbox across all folders.

    Since this tool lists email across all folders, it may return sent items, drafts,
    and other items that are not in the inbox.
    """
    client = get_client(context.get_auth_token_or_empty())
    request_config = prepare_list_emails_request_config(limit)
    message_builder = client.me.messages

    response = await fetch_emails(message_builder, pagination_token, request_config)
    messages = [Message.from_sdk(msg).to_dict() for msg in response.value or []]
    pagination_token = response.odata_next_link

    result = {
        "messages": messages,
        "num_messages": len(messages),
        "pagination_token": pagination_token,
    }
    result = remove_none_values(result)
    return result


@tool(requires_auth=Microsoft(scopes=["Mail.Read"]))
async def list_emails_in_folder(
    context: ToolContext,
    well_known_folder_name: Annotated[
        WellKnownFolderNames | None,
        "The name of the folder to list emails from. Defaults to None.",
    ] = None,
    folder_id: Annotated[
        str | None,
        "The ID of the folder to list emails from if the folder is not a well-known folder. "
        "Defaults to None.",
    ] = None,
    limit: Annotated[int, "The number of messages to return. Max is 100. Defaults to 5."] = 5,
    pagination_token: Annotated[
        str | None, "The pagination token to continue a previous request"
    ] = None,
) -> Annotated[
    dict, "A dictionary containing a list of emails and a pagination token, if applicable"
]:
    """List the user's emails in the specified folder.

    Exactly one of `well_known_folder_name` or `folder_id` MUST be provided.
    """
    if not (bool(well_known_folder_name) ^ bool(folder_id)):
        raise ToolExecutionError(
            message="Exactly one of `well_known_folder_name` or `folder_id` must be provided."
        )
    folder_name = well_known_folder_name.value if well_known_folder_name else folder_id
    client = get_client(context.get_auth_token_or_empty())
    request_config = prepare_list_emails_request_config(limit)
    message_builder = client.me.mail_folders.by_mail_folder_id(folder_name).messages  # type: ignore[arg-type]

    response = await fetch_emails(message_builder, pagination_token, request_config)
    messages = [Message.from_sdk(msg).to_dict() for msg in response.value or []]
    pagination_token = response.odata_next_link

    result = {
        "messages": messages,
        "num_messages": len(messages),
        "pagination_token": pagination_token,
    }
    result = remove_none_values(result)
    return result


@tool(requires_auth=Microsoft(scopes=["Mail.Read"]))
async def list_emails_by_property(
    context: ToolContext,
    property: Annotated[EmailFilterProperty, "The property to filter the emails by."],  # noqa: A002
    operator: Annotated[FilterOperator, "The operator to use for the filter."],
    value: Annotated[str, "The value to filter the emails by"],
    limit: Annotated[int, "The number of messages to return. Max is 100. Defaults to 5."] = 5,
    pagination_token: Annotated[
        str | None, "The pagination token to continue a previous request"
    ] = None,
) -> Annotated[dict, "A dictionary containing a list of emails"]:
    """List emails in the user's mailbox across all folders filtering by a property."""
    client = get_client(context.get_auth_token_or_empty())
    request_config = prepare_list_emails_request_config(limit, property, operator, value)
    message_builder = client.me.messages

    response = await fetch_emails(message_builder, pagination_token, request_config)
    messages = [Message.from_sdk(msg).to_dict() for msg in response.value or []]
    pagination_token = response.odata_next_link

    result = {
        "messages": messages,
        "num_messages": len(messages),
        "pagination_token": pagination_token,
    }
    result = remove_none_values(result)
    return result
