import pytest

from arcade_microsoft.outlook_mail._utils import _create_filter_expression
from arcade_microsoft.outlook_mail.enums import EmailFilterProperty, FilterOperator


@pytest.mark.parametrize(
    "property_, operator, value, expected_filter_expr",
    [
        (
            EmailFilterProperty.SUBJECT,
            FilterOperator.EQUAL,
            "Hello",
            "receivedDateTime ge 1900-01-01T00:00:00Z and subject eq 'Hello'",
        ),
        (
            EmailFilterProperty.SUBJECT,
            FilterOperator.STARTS_WITH,
            "He",
            "receivedDateTime ge 1900-01-01T00:00:00Z and startsWith(subject, 'He')",
        ),
        (
            EmailFilterProperty.CONVERSATION_ID,
            FilterOperator.EQUAL,
            "12345askdfjh=wef67890",
            "receivedDateTime ge 1900-01-01T00:00:00Z and conversationId eq '12345askdfjh=wef67890'",  # noqa: E501
        ),
        (
            EmailFilterProperty.CONVERSATION_ID,
            FilterOperator.NOT_EQUAL,
            "67890",
            "receivedDateTime ge 1900-01-01T00:00:00Z and conversationId ne 67890",
        ),
        (
            EmailFilterProperty.RECEIVED_DATE_TIME,
            FilterOperator.GREATER_THAN,
            "2024-01-01",
            "receivedDateTime gt '2024-01-01'",
        ),
        (
            EmailFilterProperty.SENDER,
            FilterOperator.EQUAL,
            "a@ex.com",
            "receivedDateTime ge 1900-01-01T00:00:00Z and sender/emailAddress/address eq 'a@ex.com'",  # noqa: E501
        ),
        (
            EmailFilterProperty.SENDER,
            FilterOperator.CONTAINS,
            "joe",
            "receivedDateTime ge 1900-01-01T00:00:00Z and contains(sender/emailAddress/address, 'joe')",  # noqa: E501
        ),
    ],
)
def test_create_filter_expression(property_, operator, value, expected_filter_expr):
    assert _create_filter_expression(property_, operator, value) == expected_filter_expr
