import pytest
from msgraph.generated.models.email_address import EmailAddress as GraphEmailAddress
from msgraph.generated.models.recipient import Recipient as GraphRecipient

from arcade_microsoft.outlook_mail.message import Recipient


@pytest.mark.parametrize(
    "input_sdk_recipient, expected_email, expected_name",
    [
        (
            GraphRecipient(email_address=GraphEmailAddress(address="dev@arcade.dev", name="Dev")),
            "dev@arcade.dev",
            "Dev",
        ),
        (
            GraphRecipient(email_address=GraphEmailAddress(address="dev@arcade.dev")),
            "dev@arcade.dev",
            "",
        ),
        (GraphRecipient(email_address=GraphEmailAddress(name="Dev")), "", "Dev"),
        (GraphRecipient(email_address=GraphEmailAddress()), "", ""),
        (GraphRecipient(), "", ""),
    ],
)
def test_recipient(input_sdk_recipient, expected_email, expected_name):
    recipient = Recipient.from_sdk(input_sdk_recipient)
    assert (
        recipient.email_address == expected_email
    ), "SDK conversion didn't set email_address correctly"
    assert recipient.name == expected_name, "SDK conversion didn't set name correctly"

    recipient_dict = recipient.to_dict()
    expected_dict = {"email_address": expected_email, "name": expected_name}
    assert recipient_dict == expected_dict, "to_dict conversion did not produce expected dictionary"

    actual_sdk_recipient = recipient.to_sdk()
    assert (
        actual_sdk_recipient.email_address.address == expected_email
    ), "to_sdk conversion produced wrong email address"
    assert (
        actual_sdk_recipient.email_address.name == expected_name
    ), "to_sdk conversion produced wrong name"
