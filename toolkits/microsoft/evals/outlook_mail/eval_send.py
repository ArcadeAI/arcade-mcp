from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

from arcade_microsoft.outlook_mail import (
    create_and_send_email,
    reply_to_email,
    send_draft_email,
)
from arcade_microsoft.outlook_mail.enums import ReplyType
from evals.outlook_mail.additional_messages import (
    list_emails_with_pagination_token_additional_messages,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_tool(create_and_send_email, "Microsoft")
catalog.add_tool(send_draft_email, "Microsoft")
catalog.add_tool(reply_to_email, "Microsoft")


@tool_eval()
def outlook_mail_send_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Outlook Mail tools."""
    suite = EvalSuite(
        name="Outlook Mail Send Evaluation",
        system_message=("You are an AI that has access to tools to send, read, and write emails."),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create draft email",
        user_message=(
            "send an email to j@arcade.dev and e@arcade.dev. Title it 'Hello friends' and have it "
            "say 'I've gathered you all here to celebrate the launch of the new Arcade platform.'"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_and_send_email,
                args={
                    "subject": "Hello friends",
                    "body": "I've gathered you all here to celebrate the launch of the new Arcade platform.",  # noqa: E501
                    "to_recipients": ["j@arcade.dev", "e@arcade.dev"],
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="subject", weight=0.3),
            SimilarityCritic(critic_field="body", weight=0.3),
            BinaryCritic(critic_field="to_recipients", weight=0.4),
        ],
    )

    suite.add_case(
        name="Update draft email",
        user_message=(
            "forward the draft AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4_x_WeUwAAAIBDwAAAFuxokOLZRtDncM4_x_WeUwAAAAC-dpvAAAA "  # noqa: E501
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=send_draft_email,
                args={
                    "message_id": "AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4_x_WeUwAAAIBDwAAAFuxokOLZRtDncM4_x_WeUwAAAAC-dpvAAAA",  # noqa: E501
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="message_id", weight=1),
        ],
    )

    suite.add_case(
        name="Reply all to email",
        user_message=("Reply to everyone - 'sounds good to me'"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=reply_to_email,
                args={
                    "message_id": "AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4_x_WeUwAAAIBDAAAAFuxokOLZRtDncM4_x_WeUwAAAABc_ezAAAA",  # noqa: E501
                    "body": "sounds good to me",
                    "reply_type": ReplyType.REPLY_ALL,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="message_id", weight=1 / 3),
            SimilarityCritic(critic_field="body", weight=1 / 3),
            BinaryCritic(critic_field="reply_type", weight=1 / 3),
        ],
        additional_messages=list_emails_with_pagination_token_additional_messages,
    )

    suite.add_case(
        name="Reply to email",
        user_message=("Reply to the account security team - 'sounds good to me'"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=reply_to_email,
                args={
                    "message_id": "AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4_x_WeUwAAAIBDAAAAFuxokOLZRtDncM4_x_WeUwAAAABc_ezAAAA",  # noqa: E501
                    "body": "sounds good to me",
                    "reply_type": ReplyType.REPLY,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="message_id", weight=1 / 3),
            SimilarityCritic(critic_field="body", weight=1 / 3),
            BinaryCritic(critic_field="reply_type", weight=1 / 3),
        ],
        additional_messages=list_emails_with_pagination_token_additional_messages,
    )

    return suite
