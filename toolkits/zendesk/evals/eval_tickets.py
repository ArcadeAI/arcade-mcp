from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_zendesk
from arcade_zendesk.enums import SortOrder, TicketStatus
from arcade_zendesk.tools.tickets import (
    add_ticket_comment,
    get_ticket_comments,
    list_tickets,
    mark_ticket_solved,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_zendesk)


@tool_eval()
def zendesk_tickets_read_eval_suite() -> EvalSuite:
    """Evaluation suite for ticket reading operations."""
    suite = EvalSuite(
        name="Zendesk Tickets Read Operations",
        system_message=(
            "You are an AI assistant with access to Zendesk ticket tools. "
            "Use them to help users view and manage support tickets."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Basic ticket listing
    suite.add_case(
        name="List all open tickets",
        user_message="Show me all open tickets",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_tickets,
                args={},
            )
        ],
        rubric=rubric,
        critics=[],  # No args to validate
    )

    suite.add_case(
        name="List tickets with explicit status request",
        user_message="Can you list the open support tickets?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_tickets,
                args={},
            )
        ],
        rubric=rubric,
        critics=[],
    )

    suite.add_case(
        name="Request for ticket overview",
        user_message="I need to see what tickets are currently open",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_tickets,
                args={},
            )
        ],
        rubric=rubric,
        critics=[],
    )

    # Test pagination
    suite.add_case(
        name="List tickets with limit",
        user_message="Show me the first 5 open tickets",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_tickets,
                args={"limit": 5},
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=1.0),
        ],
    )

    # Test status filter
    suite.add_case(
        name="List tickets with specific status",
        user_message="Show me all pending tickets",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_tickets,
                args={"status": TicketStatus.PENDING},
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="status", weight=1.0),
        ],
    )

    # Test sort order
    suite.add_case(
        name="List tickets oldest first",
        user_message="Show me tickets sorted from oldest to newest",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_tickets,
                args={"sort_order": SortOrder.ASC},
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="sort_order", weight=1.0),
        ],
    )

    return suite


@tool_eval()
def zendesk_get_ticket_comments_eval_suite() -> EvalSuite:
    """Evaluation suite for getting ticket comments."""
    suite = EvalSuite(
        name="Zendesk Get Ticket Comments",
        system_message=(
            "You are an AI assistant with access to Zendesk ticket tools. "
            "Use them to help users view ticket comments and conversation history."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Get comments for a ticket
    suite.add_case(
        name="Get comments for specific ticket",
        user_message="Show me the comments for ticket 123",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_ticket_comments,
                args={"ticket_id": 123},
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=1.0),
        ],
    )

    suite.add_case(
        name="View ticket conversation",
        user_message="Can you show me the conversation history for ticket #456?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_ticket_comments,
                args={"ticket_id": 456},
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=1.0),
        ],
    )

    suite.add_case(
        name="Get ticket description",
        user_message="What is the original description of ticket 789?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_ticket_comments,
                args={"ticket_id": 789},
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=1.0),
        ],
    )

    return suite


@tool_eval()
def zendesk_ticket_comments_eval_suite() -> EvalSuite:
    """Evaluation suite for ticket comment operations."""
    suite = EvalSuite(
        name="Zendesk Ticket Comments",
        system_message=(
            "You are an AI assistant with access to Zendesk ticket tools. "
            "Use them to help users add comments to support tickets."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Public comments
    suite.add_case(
        name="Add public comment to ticket",
        user_message="Add a comment to ticket 123 saying 'We are investigating this issue'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_ticket_comment,
                args={
                    "ticket_id": 123,
                    "comment_body": "We are investigating this issue",
                    "public": True,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.3),
            SimilarityCritic(critic_field="comment_body", weight=0.5),
            BinaryCritic(critic_field="public", weight=0.2),
        ],
    )

    suite.add_case(
        name="Add public comment without specifying visibility",
        user_message="Please comment on ticket #456: "
        "The issue has been escalated to our engineering team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_ticket_comment,
                args={
                    "ticket_id": 456,
                    "comment_body": "The issue has been escalated to our engineering team",
                    "public": True,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.3),
            SimilarityCritic(critic_field="comment_body", weight=0.5),
            BinaryCritic(critic_field="public", weight=0.2),
        ],
    )

    # Internal comments
    suite.add_case(
        name="Add internal comment to ticket",
        user_message="Add an internal note to ticket 789: Customer is VIP, prioritize this issue",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_ticket_comment,
                args={
                    "ticket_id": 789,
                    "comment_body": "Customer is VIP, prioritize this issue",
                    "public": False,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.3),
            SimilarityCritic(critic_field="comment_body", weight=0.5),
            BinaryCritic(critic_field="public", weight=0.2),
        ],
    )

    suite.add_case(
        name="Add private comment to ticket",
        user_message="Add a private comment to ticket 321 for agents only: "
        "Check with backend team about API limits",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_ticket_comment,
                args={
                    "ticket_id": 321,
                    "comment_body": "Check with backend team about API limits",
                    "public": False,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.3),
            SimilarityCritic(critic_field="comment_body", weight=0.5),
            BinaryCritic(critic_field="public", weight=0.2),
        ],
    )

    # Complex comment scenarios
    suite.add_case(
        name="Add detailed public update",
        user_message="Update ticket 555 with: 'We've identified the root cause. "
        "A fix will be deployed within 24 hours. We apologize for the inconvenience.'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_ticket_comment,
                args={
                    "ticket_id": 555,
                    "comment_body": "We've identified the root cause. "
                    "A fix will be deployed within 24 hours. We apologize for the inconvenience.",
                    "public": True,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.3),
            SimilarityCritic(critic_field="comment_body", weight=0.6),
            BinaryCritic(critic_field="public", weight=0.1),
        ],
    )

    return suite


@tool_eval()
def zendesk_ticket_resolution_eval_suite() -> EvalSuite:
    """Evaluation suite for ticket resolution operations."""
    suite = EvalSuite(
        name="Zendesk Ticket Resolution",
        system_message=(
            "You are an AI assistant with access to Zendesk ticket tools. "
            "Use them to help users resolve support tickets."
            "Consider that closing a ticket is the same as marking it as solved."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Simple resolution
    suite.add_case(
        name="Mark ticket as solved without comment",
        user_message="Mark ticket 100 as solved",
        expected_tool_calls=[
            ExpectedToolCall(
                func=mark_ticket_solved,
                args={
                    "ticket_id": 100,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=1.0),
        ],
    )

    suite.add_case(
        name="Close ticket",
        user_message="Please close ticket #200",
        expected_tool_calls=[
            ExpectedToolCall(
                func=mark_ticket_solved,
                args={
                    "ticket_id": 200,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=1.0),
        ],
    )

    # Resolution with public comment
    suite.add_case(
        name="Solve ticket with public resolution comment",
        user_message="Resolve ticket 300 with comment: "
        "'Issue resolved by updating your account settings'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=mark_ticket_solved,
                args={
                    "ticket_id": 300,
                    "comment_body": "Issue resolved by updating your account settings",
                    "comment_public": True,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.3),
            SimilarityCritic(critic_field="comment_body", weight=0.5),
            BinaryCritic(critic_field="comment_public", weight=0.2),
        ],
    )

    suite.add_case(
        name="Close ticket with customer-facing message",
        user_message="Close ticket 400 and tell the customer: "
        "Your refund has been processed successfully",
        expected_tool_calls=[
            ExpectedToolCall(
                func=mark_ticket_solved,
                args={
                    "ticket_id": 400,
                    "comment_body": "Your refund has been processed successfully",
                    "comment_public": True,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.3),
            SimilarityCritic(critic_field="comment_body", weight=0.5),
            BinaryCritic(critic_field="comment_public", weight=0.2),
        ],
    )

    # Resolution with internal comment
    suite.add_case(
        name="Solve ticket with internal note",
        user_message="Mark ticket 500 as solved with internal note: "
        "'Resolved via backend database fix'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=mark_ticket_solved,
                args={
                    "ticket_id": 500,
                    "comment_body": "Resolved via backend database fix",
                    "comment_public": False,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.3),
            SimilarityCritic(critic_field="comment_body", weight=0.5),
            BinaryCritic(critic_field="comment_public", weight=0.2),
        ],
    )

    # Default internal comment behavior
    suite.add_case(
        name="Solve ticket with comment defaults to internal",
        user_message="Mark ticket 550 as solved with comment: 'Fixed by applying patch #2345'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=mark_ticket_solved,
                args={
                    "ticket_id": 550,
                    "comment_body": "Fixed by applying patch #2345",
                    # comment_public should default to False if not specified
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.4),
            SimilarityCritic(critic_field="comment_body", weight=0.6),
        ],
    )

    suite.add_case(
        name="Close ticket with private resolution details",
        user_message="Close ticket 600 with a private note for agents: "
        "'Customer account had duplicate entries, merged successfully'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=mark_ticket_solved,
                args={
                    "ticket_id": 600,
                    "comment_body": "Customer account had duplicate entries, merged successfully",
                    "comment_public": False,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.3),
            SimilarityCritic(critic_field="comment_body", weight=0.5),
            BinaryCritic(critic_field="comment_public", weight=0.2),
        ],
    )

    return suite


@tool_eval()
def zendesk_ticket_workflow_eval_suite() -> EvalSuite:
    """Evaluation suite for ticket workflow scenarios with context."""
    suite = EvalSuite(
        name="Zendesk Ticket Workflows",
        system_message=(
            "You are an AI assistant with access to Zendesk ticket tools. "
            "Use them to help users manage support ticket workflows."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Workflow: View then comment
    suite.add_case(
        name="Comment on specific ticket after viewing",
        user_message="Add a comment to the login issue ticket saying we're working on it",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_ticket_comment,
                args={
                    "ticket_id": 1,
                    "comment_body": "We're currently working on resolving your login issue.",
                    "public": True,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.3),
            SimilarityCritic(critic_field="comment_body", weight=0.5),
            BinaryCritic(critic_field="public", weight=0.2),
        ],
        additional_messages=[
            {
                "role": "user",
                "content": "Show me all open tickets",
            },
            {
                "role": "assistant",
                "content": "I'll list all open tickets for you.",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "list_tickets",
                            "arguments": "{}",
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"tickets": [{"id": 1, "subject": "Login issue", "status": "open", '
                '"html_url": "https://example.zendesk.com/agent/tickets/1"}, '
                '{"id": 2, "subject": "Password reset request", "status": "open", '
                '"html_url": "https://example.zendesk.com/agent/tickets/2"}], "count": 2}',
                "tool_call_id": "call_1",
                "name": "list_tickets",
            },
            {
                "role": "assistant",
                "content": "I found 2 open tickets:\n"
                "1. Ticket #1: Login issue\n2. Ticket #2: Password reset request",
            },
        ],
    )

    # Workflow: Comment then resolve
    suite.add_case(
        name="Resolve ticket after adding solution",
        user_message="Now mark that ticket as solved",
        expected_tool_calls=[
            ExpectedToolCall(
                func=mark_ticket_solved,
                args={
                    "ticket_id": 789,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=1.0),
        ],
        additional_messages=[
            {
                "role": "user",
                "content": "Add a comment to ticket 789: "
                "'Reset your password using the forgot password link on the login page'",
            },
            {
                "role": "assistant",
                "content": "I'll add that comment to ticket 789.",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "add_ticket_comment",
                            "arguments": '{"ticket_id": 789, "comment_body": '
                            '"Reset your password using the forgot password link on the login '
                            'page", "public": true}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"success": true, "ticket_id": 789, "comment_type": "public", '
                '"ticket": {"id": 789, "html_url": "https://example.zendesk.com/agent/tickets/789"}}',
                "tool_call_id": "call_1",
                "name": "add_ticket_comment",
            },
            {
                "role": "assistant",
                "content": "I've added the comment with password reset instructions "
                "to ticket #789.",
            },
        ],
    )

    # Workflow: Multiple updates
    suite.add_case(
        name="Add final comment and close ticket",
        user_message="Add 'This issue has been fully resolved' and close ticket 999",
        expected_tool_calls=[
            ExpectedToolCall(
                func=mark_ticket_solved,
                args={
                    "ticket_id": 999,
                    "comment_body": "This issue has been fully resolved",
                    "comment_public": True,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="ticket_id", weight=0.3),
            SimilarityCritic(critic_field="comment_body", weight=0.5),
            BinaryCritic(critic_field="comment_public", weight=0.2),
        ],
    )

    return suite
