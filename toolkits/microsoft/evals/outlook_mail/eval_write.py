from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

from arcade_microsoft.outlook_mail import create_draft_email, update_draft_email
from evals.outlook_mail.additional_messages import (
    update_draft_email_additional_messages,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_tool(create_draft_email, "Microsoft")
catalog.add_tool(update_draft_email, "Microsoft")


@tool_eval()
def outlook_mail_write_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Outlook Mail tools."""
    suite = EvalSuite(
        name="Outlook Mail Write Evaluation",
        system_message=("You are an AI that has access to tools to send, read, and write emails."),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create draft email",
        user_message=(
            "create a new draft email with subject 'Hello friends' and body "
            "'I've gathered you all here to celebrate the launch of the new Arcade platform."
            "address it to e@arcade.dev and z@arcade.dev. also carbon copy to j@arcade.dev, "
            "f@arcade.dev, k@arcade.dev and finally to m@arcade.dev. also bcc to r@arcade.dev"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_draft_email,
                args={
                    "subject": "Hello friends",
                    "body": "I've gathered you all here to celebrate the launch of the new Arcade platform.",  # noqa: E501
                    "to_recipients": ["e@arcade.dev", "z@arcade.dev"],
                    "cc_recipients": [
                        "j@arcade.dev",
                        "f@arcade.dev",
                        "k@arcade.dev",
                        "m@arcade.dev",
                    ],
                    "bcc_recipients": ["r@arcade.dev"],
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="subject", weight=0.2),
            SimilarityCritic(critic_field="body", weight=0.2),
            BinaryCritic(critic_field="to_recipients", weight=0.2),
            BinaryCritic(critic_field="cc_recipients", weight=0.2),
            BinaryCritic(critic_field="bcc_recipients", weight=0.2),
        ],
    )

    suite.add_case(
        name="Update draft email",
        user_message=(
            "oh wait i think i messed up on some emails. I meant 'z', not 'e'. "
            "Also, I forgot to bcc y@arcade.dev. Also, replace the period with an "
            "exclamation point since I want to convey excitement. Oh I almost forgot, "
            "Don't cc anyone."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_draft_email,
                args={
                    "message_id": "AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4_x_WeUwAAAIBDwAAAFuxokOLZRtDncM4_x_WeUwAAAAC-dpvAAAA",  # noqa: E501
                    "body": "I've gathered you all here to celebrate the launch of the new Arcade platform!",  # noqa: E501
                    "to_add": ["z@arcade.dev"],
                    "to_remove": ["e@arcade.dev"],
                    "cc_remove": ["j@arcade.dev", "f@arcade.dev", "k@arcade.dev", "m@arcade.dev"],
                    "bcc_add": ["y@arcade.dev"],
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="message_id", weight=1 / 6),
            BinaryCritic(critic_field="body", weight=1 / 6),
            BinaryCritic(critic_field="to_add", weight=1 / 6),
            BinaryCritic(critic_field="to_remove", weight=1 / 6),
            BinaryCritic(critic_field="cc_remove", weight=1 / 6),
            BinaryCritic(critic_field="bcc_add", weight=1 / 6),
        ],
        additional_messages=update_draft_email_additional_messages,
    )

    return suite
