import arcade_google
from arcade_google.tools.gmail import (
    get_thread,
    list_threads,
    search_threads,
    send_email,
)
from arcade_google.tools.utils import DateRange

from arcade.sdk import ToolCatalog
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

    suite.add_case(
        name="List threads",
        user_message="Get 42 threads like right now i even wanna see the ones in my trash",
        expected_tool_calls=[
            (
                list_threads,
                {"max_results": 42, "include_spam_trash": True},
            )
        ],
        critics=[
            BinaryCritic(critic_field="max_results", weight=0.5),
            BinaryCritic(critic_field="include_spam_trash", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search threads",
        user_message="Search for threads from johndoe@example.com to janedoe@example.com about that talk about 'Arcade AI' from yesterday",
        expected_tool_calls=[
            (
                search_threads,
                {
                    "sender": "johndoe@example.com",
                    "recipient": "janedoe@example.com",
                    "body": "Arcade AI",
                    "date_range": DateRange.YESTERDAY,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="sender", weight=0.25),
            BinaryCritic(critic_field="recipient", weight=0.25),
            SimilarityCritic(critic_field="body", weight=0.25),
            BinaryCritic(critic_field="date_range", weight=0.25),
        ],
    )

    suite.add_case(
        name="Get a thread by ID",
        user_message="Get the thread r-124325435467568867667878874565464564563523424323524235242412",
        expected_tool_calls=[
            (
                get_thread,
                {
                    "thread_id": "r-124325435467568867667878874565464564563523424323524235242412",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="thread_id", weight=1.0),
        ],
    )

    return suite
