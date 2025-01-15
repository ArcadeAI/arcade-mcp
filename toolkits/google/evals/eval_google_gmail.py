from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)

import arcade_google
from arcade_google.tools.gmail import (
    get_thread,
    list_threads,
    search_threads,
    send_email,
)
from arcade_google.tools.utils import DateRange

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
            ExpectedToolCall(
                func=send_email,
                args={
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
        name="Simple list threads",
        user_message="Get 42 threads like right now i even wanna see the ones in my trash",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_threads,
                args={"max_results": 42, "include_spam_trash": True},
            )
        ],
        critics=[
            BinaryCritic(critic_field="max_results", weight=0.5),
            BinaryCritic(critic_field="include_spam_trash", weight=0.5),
        ],
    )

    history = [
        {"role": "user", "content": "list 1 thread"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_X8V5Hw9iJ3wfB8WMZf8omAMi",
                    "type": "function",
                    "function": {"name": "Google_ListThreads", "arguments": '{"max_results":1}'},
                }
            ],
        },
        {
            "role": "tool",
            "content": '{"next_page_token":"10321400718999360131","num_threads":1,"threads":[{"historyId":"61691","id":"1934a8f8deccb749","snippet":"Hi Joe, I hope this email finds you well. Thank you for being a part of our community."}]}',
            "tool_call_id": "call_X8V5Hw9iJ3wfB8WMZf8omAMi",
            "name": "Google_ListThreads",
        },
        {
            "role": "assistant",
            "content": "Here is one email thread:\n\n- **Snippet:** Hi Joe, I hope this email finds you well. Thank you for being a part of our community.\n- **Thread ID:** 1934a8f8deccb749\n- **History ID:** 61691",
        },
    ]
    suite.add_case(
        name="List threads with history",
        user_message="Get the next 5 threads",
        additional_messages=history,
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_threads,
                args={
                    "max_results": 5,
                    "page_token": "10321400718999360131",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="max_results", weight=0.2),
            BinaryCritic(critic_field="page_token", weight=0.8),
        ],
    )

    suite.add_case(
        name="Search threads",
        user_message="Search for threads from johndoe@example.com to janedoe@example.com about that talk about 'Arcade AI' from yesterday",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_threads,
                args={
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
            ExpectedToolCall(
                func=get_thread,
                args={
                    "thread_id": "r-124325435467568867667878874565464564563523424323524235242412",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="thread_id", weight=1.0),
        ],
    )

    return suite
