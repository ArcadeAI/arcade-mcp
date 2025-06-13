from arcade_tdk import ToolContext
from msgraph.generated.models.message_collection_response import MessageCollectionResponse
from msgraph.generated.users.item.mail_folders.item.messages.messages_request_builder import (
    MessagesRequestBuilder as MailFolderMessagesRequestBuilder,
)
from msgraph.generated.users.item.messages.item.reply.reply_post_request_body import (
    ReplyPostRequestBody,
)
from msgraph.generated.users.item.messages.item.reply_all.reply_all_post_request_body import (
    ReplyAllPostRequestBody,
)
from msgraph.generated.users.item.messages.messages_request_builder import (
    MessagesRequestBuilder as UserMessagesRequestBuilder,
)

from arcade_microsoft.client import get_client
from arcade_microsoft.outlook_mail.constants import DEFAULT_MESSAGE_FIELDS
from arcade_microsoft.outlook_mail.enums import EmailFilterProperty, FilterOperator, ReplyType


def remove_none_values(data: dict) -> dict:
    """Remove all keys with None values from the dictionary."""
    return {k: v for k, v in data.items() if v is not None}


def _create_filter_expression(
    property_: EmailFilterProperty | None = None,
    operator: FilterOperator | None = None,
    value: str | None = None,
) -> str | None:
    if property_ and operator and value:
        property_value = property_.value
        operator_value = operator.value

        # Never use quotes around 'value' for booleans and numerics
        value_quote = "'"
        if value.lower() in ["true", "false"] or value.isdigit():
            value_quote = ""

        # Handle function operators (e.g., contains, startsWith, endsWith)
        if operator.is_function():
            filter_expr = f"{operator_value}({property_value}, {value_quote}{value}{value_quote})"
        else:
            # Handle comparison operators (e.g., eq, ne, gt, ge, lt, le)
            filter_expr = f"{property_value} {operator_value} {value_quote}{value}{value_quote}"

        if property_value == EmailFilterProperty.RECEIVED_DATE_TIME:
            filter_expr = filter_expr
        else:  # Since receivedDateTime is in orderby, it must be in filter: https://learn.microsoft.com/en-us/graph/api/user-list-messages?view=graph-rest-1.0&tabs=http#optional-query-parameters
            filter_expr = f"receivedDateTime ge 1900-01-01T00:00:00Z and {filter_expr}"

        return filter_expr

    return None


def prepare_list_emails_request_config(
    limit: int,
    property_: EmailFilterProperty | None = None,
    operator: FilterOperator | None = None,
    value: str | None = None,
) -> MailFolderMessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration:
    """Prepare a request configuration for listing emails."""
    limit = max(1, min(limit, 100))  # limit must be between 1 and 100

    orderby = ["receivedDateTime DESC"]
    filter_expr = _create_filter_expression(property_, operator, value)

    query_params = MailFolderMessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
        count=True,
        select=DEFAULT_MESSAGE_FIELDS,
        orderby=orderby,
        filter=filter_expr,
        top=limit,
    )
    return MailFolderMessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
        query_parameters=query_params,
    )


async def fetch_emails(
    message_builder: MailFolderMessagesRequestBuilder | UserMessagesRequestBuilder,
    pagination_token: str | None = None,
    request_config: MailFolderMessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration
    | None = None,
) -> MessageCollectionResponse:
    """Fetch emails from the user's mailbox.

    Microsoft Graph Python SDK does not support pagination (as of 2025-04-17),
    so we use raw URL for pagination if a pagination token is provided.
    """
    if pagination_token:
        return await message_builder.with_url(pagination_token).get()  # type: ignore[return-value]
    return await message_builder.get(request_configuration=request_config)  # type: ignore[return-value, arg-type]


async def send_reply_email(
    context: ToolContext,
    message_id: str,
    body: str,
    reply_type: ReplyType,
) -> dict:
    """Send a reply email to the sender or all recipients of an existing email."""
    client = get_client(context.get_auth_token_or_empty())

    if reply_type == ReplyType.REPLY:
        reply_request_body = ReplyPostRequestBody(comment=body)
        await client.me.messages.by_message_id(message_id).reply.post(reply_request_body)
    elif reply_type == ReplyType.REPLY_ALL:
        reply_all_request_body = ReplyAllPostRequestBody(comment=body)
        await client.me.messages.by_message_id(message_id).reply_all.post(reply_all_request_body)

    return {
        "success": True,
        "message": "Email sent successfully",
    }
