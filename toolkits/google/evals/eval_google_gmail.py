import json

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_google
from arcade_google.models import GmailReplyToWhom
from arcade_google.tools import (
    get_thread,
    list_emails_by_header,
    list_threads,
    reply_to_email,
    search_threads,
    send_email,
    write_draft_reply_email,
)
from arcade_google.utils import DateRange

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


@tool_eval()
def gmail_reply_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Gmail reply tools."""
    suite = EvalSuite(
        name="Gmail Reply Tools Evaluation",
        system_message="You are an AI assistant that can send and manage emails using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    email_history = [
        {"role": "user", "content": "get the latest emails I received from johndoe@gmail.com"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_jowMD7aB9sVPClOfvNof7Llu",
                    "type": "function",
                    "function": {
                        "name": "Google_ListEmailsByHeader",
                        "arguments": json.dumps({
                            "sender": "johndoe@gmail.com",
                            "max_results": 5,
                        }),
                    },
                }
            ],
        },
        {
            "role": "tool",
            "content": json.dumps({
                "emails": [
                    {
                        "body": "test 1",
                        "cc": "",
                        "date": "Tue, 11 Feb 2025 11:33:08 -0300",
                        "from": "John Doe <johndoe@gmail.com>",
                        "header_message_id": "<cierty475cty7245yxq@mail.gmail.com>",
                        "history_id": "123456",
                        "id": "q34759q435nv",
                        "in_reply_to": "",
                        "label_ids": ["INBOX"],
                        "references": "",
                        "reply_to": "",
                        "snippet": "test 1",
                        "subject": "test 1",
                        "thread_id": "345y6v3596",
                        "to": "myself@gmail.com",
                    },
                    {
                        "body": "test 2",
                        "cc": "",
                        "date": "Mon, 20 Jan 2025 13:04:42 -0800",
                        "from": "John Doe <johndoe@gmail.com>",
                        "header_message_id": "<28745ytvw8745ct4@mail.gmail.com>",
                        "history_id": "3456758",
                        "id": "9475tvy24578yx",
                        "in_reply_to": "",
                        "label_ids": [],
                        "references": "",
                        "reply_to": "",
                        "snippet": "test 2",
                        "subject": "test 2",
                        "thread_id": "249576v3496",
                        "to": "myself@gmail.com",
                    },
                ]
            }),
            "tool_call_id": "call_jowMD7aB9sVPClOfvNof7Llu",
            "name": "Google_ListEmailsByHeader",
        },
        {
            "role": "assistant",
            "content": "Here are the latest emails you received from johndoe@gmail.com:\n\n1. **Subject**: test 1\n   - **Date**: Tue, 11 Feb 2025 11:33:08 -0300\n   - **Snippet**: test 1\n\n2. **Subject**: test 2\n   - **Date**: Mon, 20 Jan 2025 13:04:42 -0800\n   - **Snippet**: test 2\n\nIf you need further details from any specific email, let me know!",
        },
    ]

    suite.add_case(
        name="Reply to an email",
        user_message="Reply to the email from johndoe@example.com about 'test 2' saying 'tested and working well'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=reply_to_email,
                args={
                    "reply_to_message_id": "9475tvy24578yx",
                    "body": "tested and working well",
                    "reply_to_whom": GmailReplyToWhom.ONLY_THE_SENDER.value,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="subject", weight=1 / 7),
            SimilarityCritic(critic_field="body", weight=1 / 7),
            BinaryCritic(critic_field="recipient", weight=1 / 7),
            BinaryCritic(critic_field="cc", weight=1 / 7),
            BinaryCritic(critic_field="bcc", weight=1 / 7),
            BinaryCritic(critic_field="reply_to_whom", weight=1 / 7),
            BinaryCritic(critic_field="reply_to_message_id", weight=1 / 7),
        ],
        additional_messages=email_history,
    )

    suite.add_case(
        name="Reply to an email with every recipient",
        user_message="Reply to every recipient in the email from johndoe@example.com about 'test 2' saying 'tested and working well'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=reply_to_email,
                args={
                    "reply_to_message_id": "9475tvy24578yx",
                    "body": "tested and working well",
                    "reply_to_whom": GmailReplyToWhom.EVERY_RECIPIENT.value,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="subject", weight=1 / 7),
            SimilarityCritic(critic_field="body", weight=1 / 7),
            BinaryCritic(critic_field="recipient", weight=1 / 7),
            BinaryCritic(critic_field="cc", weight=1 / 7),
            BinaryCritic(critic_field="bcc", weight=1 / 7),
            BinaryCritic(critic_field="reply_to_whom", weight=1 / 7),
            BinaryCritic(critic_field="reply_to_message_id", weight=1 / 7),
        ],
        additional_messages=email_history,
    )

    suite.add_case(
        name="Reply to an email with bcc",
        user_message="Reply to the email from johndoe@example.com about 'test 2' saying 'tested and working well' and send it to janedoe@example.com as bcc as well",
        expected_tool_calls=[
            ExpectedToolCall(
                func=reply_to_email,
                args={
                    "reply_to_message_id": "9475tvy24578yx",
                    "body": "tested and working well",
                    "bcc": ["janedoe@example.com"],
                    "reply_to_whom": GmailReplyToWhom.ONLY_THE_SENDER.value,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="subject", weight=1 / 7),
            SimilarityCritic(critic_field="body", weight=1 / 7),
            BinaryCritic(critic_field="recipient", weight=1 / 7),
            BinaryCritic(critic_field="cc", weight=1 / 7),
            BinaryCritic(critic_field="bcc", weight=1 / 7),
            BinaryCritic(critic_field="reply_to_whom", weight=1 / 7),
            BinaryCritic(critic_field="reply_to_message_id", weight=1 / 7),
        ],
        additional_messages=email_history,
    )

    suite.add_case(
        name="Write draft reply",
        user_message="Write a draft reply to the email from johndoe@example.com about 'test 2' saying 'tested and working well'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=write_draft_reply_email,
                args={
                    "reply_to_message_id": "9475tvy24578yx",
                    "body": "tested and working well",
                    "reply_to_whom": GmailReplyToWhom.ONLY_THE_SENDER.value,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="subject", weight=1 / 7),
            SimilarityCritic(critic_field="body", weight=1 / 7),
            BinaryCritic(critic_field="recipient", weight=1 / 7),
            BinaryCritic(critic_field="cc", weight=1 / 7),
            BinaryCritic(critic_field="bcc", weight=1 / 7),
            BinaryCritic(critic_field="reply_to_message_id", weight=1 / 7),
            BinaryCritic(critic_field="reply_to_whom", weight=1 / 7),
        ],
        additional_messages=email_history,
    )

    suite.add_case(
        name="Write draft reply to every recipient",
        user_message="Write a draft reply to every recipient in the email from johndoe@example.com about 'test 2' saying 'tested and working well'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=write_draft_reply_email,
                args={
                    "reply_to_message_id": "9475tvy24578yx",
                    "body": "tested and working well",
                    "reply_to_whom": GmailReplyToWhom.EVERY_RECIPIENT.value,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="subject", weight=1 / 7),
            SimilarityCritic(critic_field="body", weight=1 / 7),
            BinaryCritic(critic_field="recipient", weight=1 / 7),
            BinaryCritic(critic_field="cc", weight=1 / 7),
            BinaryCritic(critic_field="bcc", weight=1 / 7),
            BinaryCritic(critic_field="reply_to_whom", weight=0.125),
            BinaryCritic(critic_field="reply_to_message_id", weight=1 / 7),
        ],
        additional_messages=email_history,
    )

    return suite


@tool_eval()
def gmail_list_emails_by_header_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Gmail tools."""
    suite = EvalSuite(
        name="Gmail list_emails_by_header tool evaluation",
        system_message="You are an AI assistant that can send and manage emails using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List emails by header using date-range",
        user_message="List all emails from johndoe@example.com to janedoe@example.com about 'Arcade AI' from yesterday",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_emails_by_header,
                args={
                    "sender": "johndoe@example.com",
                    "recipient": "janedoe@example.com",
                    "subject": "Arcade AI",
                    "date_range": DateRange.YESTERDAY.value,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="sender", weight=1 / 4),
            BinaryCritic(critic_field="recipient", weight=1 / 4),
            SimilarityCritic(critic_field="subject", weight=1 / 4),
            BinaryCritic(critic_field="date_range", weight=1 / 4),
        ],
    )

    suite.add_case(
        name="List emails by header using date-range",
        user_message="List all emails from johndoe@example.com to janedoe@example.com about 'Arcade AI' from the last month",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_emails_by_header,
                args={
                    "sender": "johndoe@example.com",
                    "recipient": "janedoe@example.com",
                    "subject": "Arcade AI",
                    "date_range": DateRange.LAST_MONTH.value,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="sender", weight=1 / 4),
            BinaryCritic(critic_field="recipient", weight=1 / 4),
            SimilarityCritic(critic_field="subject", weight=1 / 4),
            BinaryCritic(critic_field="date_range", weight=1 / 4),
        ],
    )

    return suite
