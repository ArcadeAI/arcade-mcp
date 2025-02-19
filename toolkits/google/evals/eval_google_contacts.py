from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade.sdk.eval.critic import BinaryCritic

import arcade_google
from arcade_google.tools.contacts import create_contact, search_contacts

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_google)


@tool_eval()
def contacts_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Google Contacts tools."""
    suite = EvalSuite(
        name="Google Contacts Tools Evaluation",
        system_message="You are an AI assistant that can manage Google Contacts using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Find a contact by name",
        user_message="Find my contact Bob",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_contacts,
                args={"query": "Bob"},
            )
        ],
    )

    suite.add_case(
        name="Search contacts with query and limit",
        user_message="Find 5 contacts whose names include 'Alice'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_contacts,
                args={
                    "query": "Alice",
                    "limit": 5,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="query", weight=0.5),
            BinaryCritic(critic_field="limit", weight=0.5),
        ],
    )

    suite.add_case(
        name="Create new contact with only given name",
        user_message="Create a new contact for Alice",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_contact,
                args={
                    "given_name": "Alice",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="given_name", weight=1.0),
        ],
    )

    suite.add_case(
        name="Create new contact with only email (infer name from email)",
        user_message="Create a new contact for alice@example.com",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_contact,
                args={
                    "given_name": "Alice",
                    "email": "alice@example.com",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="email", weight=0.5),
            BinaryCritic(critic_field="given_name", weight=0.5),
        ],
    )

    suite.add_case(
        name="Create new contact with full name and email",
        user_message="Create a contact for Bob Smith (bob.smith@example.com)",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_contact,
                args={
                    "given_name": "Bob",
                    "family_name": "Smith",
                    "email": "bob.smith@example.com",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="given_name", weight=0.33),
            BinaryCritic(critic_field="family_name", weight=0.33),
            BinaryCritic(critic_field="email", weight=0.34),
        ],
    )

    return suite
