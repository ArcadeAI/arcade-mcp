from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_hubspot
from arcade_hubspot.tools import get_company_data_by_keywords

rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
catalog.add_module(arcade_hubspot)


@tool_eval()
def get_company_data_by_keywords_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the get_company_data_by_keywords tool."""
    suite = EvalSuite(
        name="Get Company Data by Keywords",
        system_message="You are an AI assistant that can interact with Hubspot CRM using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get company data by keywords",
        user_message="Get information about the Acme company.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_company_data_by_keywords,
                args={
                    "keywords": "Acme",
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
        name="Get company data by keywords with limit",
        user_message="Get information of up to 3 companies with the word 'Acme' in their name.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_company_data_by_keywords,
                args={
                    "keywords": "Acme",
                    "limit": 3,
                    "next_page_token": None,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.6),
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="next_page_token", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get summary of company activity",
        user_message="Get a summary of the latest activities in the Acme company.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_company_data_by_keywords,
                args={
                    "keywords": "Acme",
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
        user_message="Get me the interactions with the contacts of the Acme company.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_company_data_by_keywords,
                args={
                    "keywords": "Acme",
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
        name="Emails or calls with contacts of an account",
        user_message="Were there any emails or calls with contacts of the Acme company this week?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_company_data_by_keywords,
                args={
                    "keywords": "Acme",
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
        name="Get company status",
        user_message="What's the status of the Acme company?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_company_data_by_keywords,
                args={
                    "keywords": "Acme",
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
        name="Get overdue tasks",
        user_message="Are there any tasks overdue for the Acme company?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_company_data_by_keywords,
                args={
                    "keywords": "Acme",
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
        name="Get company closing likelihood",
        user_message="What's the likelihood of the Acme company closing a deal?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_company_data_by_keywords,
                args={
                    "keywords": "Acme",
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

    return suite
