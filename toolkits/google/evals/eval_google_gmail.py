import arcade_google
from arcade_google.tools.gmail import (
    send_email,
)

from arcade.core.catalog import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    SimilarityCritic,
    tool_eval,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_google)


@tool_eval()
def gmail_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Gmail tools."""
    suite = EvalSuite(
        name="Gmail Tools Evaluation",
        system_message="You are an AI assistant that can send and manage emails using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Send email to user with clear username",
        user_message="Send a email to johndoe@example.com saying 'Hello, can we meet at 3 PM?'. CC his boss janedoe@example.com",
        expected_tool_calls=[
            (
                send_email,
                {
                    "subject": "Meeting Request",
                    "body": "Hello, can we meet at 3 PM?",
                    "recipient": "johndoe@example.com",
                    "cc": ["janedoe@example.com"],
                    "bcc": None,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="subject", weight=0.125),
            SimilarityCritic(critic_field="body", weight=0.25),
            BinaryCritic(critic_field="recipient", weight=0.25),
            BinaryCritic(critic_field="cc", weight=0.25),
            BinaryCritic(critic_field="bcc", weight=0.125),
        ],
    )

    return suite
