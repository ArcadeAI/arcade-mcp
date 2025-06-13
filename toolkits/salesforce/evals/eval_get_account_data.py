from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_salesforce
from arcade_salesforce.tools import get_account_data_by_id, get_account_data_by_keywords

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_salesforce)


@tool_eval()
def get_account_data_by_keywords_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="get_account_data_by_keywords",
        system_message=(
            "You are an AI assistant with access to Salesforce tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get account data by keywords",
        user_message="Get information about the Acme account.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_account_data_by_keywords,
                args={
                    "query": "Acme",
                    "page": 1,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="query", weight=0.5),
            BinaryCritic(critic_field="page", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get account data by keywords with limit",
        user_message="Get information of up to 3 accounts with the word 'Acme' in their name.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_account_data_by_keywords,
                args={
                    "query": "Acme",
                    "limit": 3,
                    "page": 1,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="query", weight=1 / 3),
            BinaryCritic(critic_field="limit", weight=1 / 3),
            BinaryCritic(critic_field="page", weight=1 / 3),
        ],
    )

    suite.add_case(
        name="Get summary of account activity",
        user_message="Get a summary of the latest activities in the Acme account.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_account_data_by_keywords,
                args={
                    "query": "Acme",
                    "page": 1,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="query", weight=0.5),
            BinaryCritic(critic_field="page", weight=0.5),
        ],
    )

    suite.add_case(
        name="Interactions with contacts of an account",
        user_message="Get me the interactions with the contacts of the Acme account.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_account_data_by_keywords,
                args={
                    "query": "Acme",
                    "page": 1,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="query", weight=0.5),
            BinaryCritic(critic_field="page", weight=0.5),
        ],
    )

    suite.add_case(
        name="Emails or calls with contacts of an account",
        user_message="Were there any emails or calls with contacts of the Acme account this week?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_account_data_by_keywords,
                args={
                    "query": "Acme",
                    "page": 1,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="query", weight=0.5),
            BinaryCritic(critic_field="page", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get account status",
        user_message="What's the status of the Acme account?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_account_data_by_keywords,
                args={
                    "query": "Acme",
                    "page": 1,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="query", weight=0.5),
            BinaryCritic(critic_field="page", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get overdue tasks",
        user_message="Are there any tasks overdue for the Acme account?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_account_data_by_keywords,
                args={
                    "query": "Acme",
                    "page": 1,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="query", weight=0.5),
            BinaryCritic(critic_field="page", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get account closing likelihood",
        user_message="What's the likelihood of the Acme account closing a deal?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_account_data_by_keywords,
                args={
                    "query": "Acme",
                    "page": 1,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="query", weight=0.5),
            BinaryCritic(critic_field="page", weight=0.5),
        ],
    )

    return suite


@tool_eval()
def get_account_data_by_id_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="get_account_data_by_id",
        system_message=(
            "You are an AI assistant with access to Salesforce tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get account data by ID",
        user_message="Get information about the account with ID 001gK000003DIn0QAG.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_account_data_by_id,
                args={
                    "account_id": "001gK000003DIn0QAG",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="account_id", weight=1.0),
        ],
    )

    return suite
