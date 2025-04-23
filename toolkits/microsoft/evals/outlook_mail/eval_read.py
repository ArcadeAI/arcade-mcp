from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

from arcade_microsoft.outlook_mail import list_emails, list_emails_in_folder
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


@tool_eval()
def outlook_mail_eval_suite() -> EvalSuite:
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
