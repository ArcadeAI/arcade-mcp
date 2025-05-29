from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_hubspot
from arcade_hubspot.custom_critics import ValueInListCritic
from arcade_hubspot.tools import create_contact, get_contact_data_by_keywords

rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
catalog.add_module(arcade_hubspot)


@tool_eval()
def get_contact_data_by_keywords_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the get_contact_data_by_keywords tool."""
    suite = EvalSuite(
        name="Get Contact Data by Keywords",
        system_message="You are an AI assistant that can interact with Hubspot CRM using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get contact data by keywords",
        user_message="Get information about the Jason Bourne contact.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_contact_data_by_keywords,
                args={
                    "keywords": "Jason Bourne",
                    "limit": 10,
                    "next_page_token": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.8),
            BinaryCritic(critic_field="next_page_token", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get contact data by keywords with limit",
        user_message="Get information of up to 3 contacts with last name 'Bourne'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_contact_data_by_keywords,
                args={
                    "keywords": "Bourne",
                    "limit": 3,
                    "next_page_token": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.7),
            BinaryCritic(critic_field="limit", weight=0.15),
            BinaryCritic(critic_field="next_page_token", weight=0.15),
        ],
    )

    suite.add_case(
        name="Get summary of contact activity",
        user_message="Get a summary of the latest activities with the Jason Bourne contact.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_contact_data_by_keywords,
                args={
                    "keywords": "Jason Bourne",
                    "limit": 10,
                    "next_page_token": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.8),
            BinaryCritic(critic_field="next_page_token", weight=0.2),
        ],
    )

    suite.add_case(
        name="Interactions with contacts of an account",
        user_message="Get me the interactions with the Jason Bourne contact from Acme.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_contact_data_by_keywords,
                args={
                    "keywords": ["Jason Bourne", "Jason Bourne Acme"],
                    "limit": 10,
                    "next_page_token": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            ValueInListCritic(critic_field="keywords", weight=0.8),
            BinaryCritic(critic_field="next_page_token", weight=0.2),
        ],
    )

    suite.add_case(
        name="Emails or calls with contacts of an account",
        user_message="Were there any emails or calls with the Jason Bourne contact from Acme this week?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_contact_data_by_keywords,
                args={
                    "keywords": ["Jason Bourne", "Jason Bourne Acme"],
                    "limit": 10,
                    "next_page_token": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            ValueInListCritic(critic_field="keywords", weight=0.8),
            BinaryCritic(critic_field="next_page_token", weight=0.2),
        ],
    )

    suite.add_case(
        name="Get overdue tasks",
        user_message="Are there any tasks overdue for the Jason Bourne contact from Acme?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_contact_data_by_keywords,
                args={
                    "keywords": ["Jason Bourne", "Jason Bourne Acme"],
                    "limit": 10,
                    "next_page_token": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            ValueInListCritic(critic_field="keywords", weight=0.8),
            BinaryCritic(critic_field="next_page_token", weight=0.2),
        ],
    )

    return suite


@tool_eval()
def create_contact_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the create_contact tool."""
    suite = EvalSuite(
        name="Create Contact",
        system_message="You are an AI assistant that can interact with Hubspot CRM using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create contact",
        user_message="Create a contact with the following information: first name 'Jason', "
        "last name 'Bourne', email 'jason.bourne@acme.com', phone '+1234567890', "
        "and job title 'Unbeatable', and associated with company id '1234567890'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_contact,
                args={
                    "company_id": "1234567890",
                    "first_name": "Jason",
                    "last_name": "Bourne",
                    "email": "jason.bourne@acme.com",
                    "phone": "+1234567890",
                    "job_title": "Unbeatable",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="company_id", weight=1 / 6),
            BinaryCritic(critic_field="first_name", weight=1 / 6),
            BinaryCritic(critic_field="last_name", weight=1 / 6),
            BinaryCritic(critic_field="email", weight=1 / 6),
            BinaryCritic(critic_field="phone", weight=1 / 6),
            BinaryCritic(critic_field="job_title", weight=1 / 6),
        ],
    )

    return suite
