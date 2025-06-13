from datetime import timedelta

from arcade_evals import (
    BinaryCritic,
    DatetimeCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

from arcade_microsoft.outlook_mail import (
    list_emails,
    list_emails_by_property,
    list_emails_in_folder,
)
from arcade_microsoft.outlook_mail.enums import WellKnownFolderNames
from evals.outlook_mail.additional_messages import (
    list_emails_with_pagination_token_additional_messages,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_tool(list_emails, "Microsoft")
catalog.add_tool(list_emails_in_folder, "Microsoft")
catalog.add_tool(list_emails_by_property, "Microsoft")


@tool_eval()
def outlook_mail_read_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Outlook Mail tools."""
    suite = EvalSuite(
        name="Outlook Mail Tools Evaluation",
        system_message=("You are an AI that has access to tools to send, read, and write emails."),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List emails in mailbox",
        user_message="get my five most recent emails",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_emails,
                args={"limit": 5},
            )
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=1.0),
        ],
    )

    suite.add_case(
        name="List emails in mailbox with pagination token",
        user_message="get the next 3",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_emails,
                args={
                    "limit": 3,
                    "pagination_token": "https://graph.microsoft.com/v1.0/me/messages?%24count=true&%24orderby=receivedDateTime+DESC&%24select=bccRecipients%2cbody%2cccRecipients%2cconversationId%2cconversationIndex%2cflag%2cfrom%2chasAttachments%2cimportance%2cisDraft%2cisRead%2creceivedDateTime%2creplyTo%2csubject%2ctoRecipients%2cwebLink&%24top=1&%24skip=1",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=0.2),
            BinaryCritic(critic_field="pagination_token", weight=0.8),
        ],
        additional_messages=list_emails_with_pagination_token_additional_messages,
    )

    suite.add_case(
        name="List emails in well-known folder",
        user_message="summarize my inbox",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_emails_in_folder,
                args={
                    "well_known_folder_name": WellKnownFolderNames.INBOX,
                    "folder_id": None,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="well_known_folder_name", weight=0.5),
            BinaryCritic(critic_field="folder_id", weight=0.5),
        ],
    )

    suite.add_case(
        name="List emails in folder by id",
        user_message="get 5 from folder AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoALgAAAyXxSd3UxTpCkDpGouEg0JMBAFuxokOLZRtDncM4",  # noqa: E501
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_emails_in_folder,
                args={
                    "well_known_folder_name": None,
                    "folder_id": "AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoALgAAAyXxSd3UxTpCkDpGouEg0JMBAFuxokOLZRtDncM4",  # noqa: E501
                    "limit": 5,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="well_known_folder_name", weight=0.4),
            BinaryCritic(critic_field="folder_id", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.2),
        ],
    )

    return suite


@tool_eval()
def outlook_mail_list_emails_by_property_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Outlook Mail tools."""
    suite = EvalSuite(
        name="Outlook Mail Tools Evaluation",
        system_message=("You are an AI that has access to tools to send, read, and write emails."),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List emails by subject",
        user_message="get all emails that talk about The Green Bottle",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_emails_by_property,
                args={
                    "property": "subject",
                    "operator": "contains",
                    "value": "The Green Bottle",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="property", weight=1 / 3),
            BinaryCritic(critic_field="operator", weight=1 / 3),
            BinaryCritic(critic_field="value", weight=1 / 3),
        ],
    )

    suite.extend_case(
        name="List emails by thread",
        user_message="get all emails in my thread 1k2jh324h92f24krjb34mtb43kj4bk3tmn34b3k4nnm3tb34mntb34mntb3m4bt3mn4bt3mn4btmnb34tmnb3t4mnb==34tkjh",  # noqa: E501
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_emails_by_property,
                args={
                    "property": "conversationId",
                    "operator": "eq",
                    "value": "1k2jh324h92f24krjb34mtb43kj4bk3tmn34b3k4nnm3tb34mntb34mntb3m4bt3mn4bt3mn4btmnb34tmnb3t4mnb==34tkjh",  # noqa: E501
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="property", weight=1 / 3),
            BinaryCritic(critic_field="operator", weight=1 / 3),
            BinaryCritic(critic_field="value", weight=1 / 3),
        ],
    )

    suite.extend_case(
        name="List emails by date",
        user_message="Today is May 1st 2025. Get all emails that are a year old or older",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_emails_by_property,
                args={
                    "property": "receivedDateTime",
                    "operator": "le",
                    "value": "2024-05-01T00:00:00Z",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="property", weight=1 / 3),
            BinaryCritic(critic_field="operator", weight=1 / 3),
            DatetimeCritic(critic_field="value", weight=1 / 3, tolerance=timedelta(days=1)),
        ],
    )

    suite.extend_case(
        name="List emails by sender",
        user_message="get all of my correspondence with the folks over at arcade.dev",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_emails_by_property,
                args={
                    "property": "sender/emailAddress/address",
                    "operator": "contains",
                    "value": "arcade.dev",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="property", weight=1 / 3),
            BinaryCritic(critic_field="operator", weight=1 / 3),
            BinaryCritic(critic_field="value", weight=1 / 3),
        ],
    )

    return suite
