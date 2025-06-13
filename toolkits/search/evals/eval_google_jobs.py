from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    NoneCritic,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_search
from arcade_search.constants import DEFAULT_GOOGLE_JOBS_LANGUAGE
from arcade_search.tools.google_jobs import search_jobs

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)

catalog = ToolCatalog()
# Register the Google Jobs tool
catalog.add_module(arcade_search)


@tool_eval()
def google_jobs_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the Google Jobs tool."""
    suite = EvalSuite(
        name="Google Jobs Tool Evaluation",
        system_message="You are an AI assistant that can perform job searches using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search for 'backend engineer' jobs",
        user_message="Search for 'backend engineer' jobs",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_jobs,
                args={
                    "query": "backend engineer",
                    "location": None,
                    "language": DEFAULT_GOOGLE_JOBS_LANGUAGE,
                    "limit": 10,
                    "next_page_token": None,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=0.5),
            NoneCritic(critic_field="location", weight=0.1),
            BinaryCritic(critic_field="language", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.1),
            NoneCritic(critic_field="next_page_token", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search for 'senior backend engineer' jobs that are part-time",
        user_message="Search for senior backend engineer jobs that are part-time",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_jobs,
                args={
                    "query": "part-time senior backend engineer",
                    "location": None,
                    "language": DEFAULT_GOOGLE_JOBS_LANGUAGE,
                    "limit": 10,
                    "next_page_token": None,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=0.5),
            NoneCritic(critic_field="location", weight=0.1),
            BinaryCritic(critic_field="language", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.1),
            NoneCritic(critic_field="next_page_token", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search for 'backend engineer' jobs in San Francisco",
        user_message="Search for 'backend engineer' jobs in San Francisco",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_jobs,
                args={
                    "query": "backend engineer",
                    "location": "San Francisco",
                    "language": DEFAULT_GOOGLE_JOBS_LANGUAGE,
                    "limit": 10,
                    "next_page_token": None,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=0.35),
            SimilarityCritic(critic_field="location", weight=0.35),
            BinaryCritic(critic_field="language", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.1),
            NoneCritic(critic_field="next_page_token", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get the first 3 jobs for 'backend engineer' in San Francisco",
        user_message="Get the first 3 jobs for 'backend engineer' in San Francisco",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_jobs,
                args={
                    "query": "backend engineer",
                    "location": "San Francisco",
                    "language": DEFAULT_GOOGLE_JOBS_LANGUAGE,
                    "limit": 3,
                    "next_page_token": None,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=0.25),
            SimilarityCritic(critic_field="location", weight=0.25),
            BinaryCritic(critic_field="language", weight=0.125),
            BinaryCritic(critic_field="limit", weight=0.25),
            NoneCritic(critic_field="next_page_token", weight=0.125),
        ],
    )

    suite.add_case(
        name="Search for 'engenheiro de software' jobs in Brazil, return results in Portuguese",
        user_message="Search for 'engenheiro de software' jobs in Brazil, return results in Portuguese",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_jobs,
                args={
                    "query": "engenheiro de software",
                    "location": "Brazil",
                    "language": "pt",
                    "limit": 10,
                    "next_page_token": None,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=0.25),
            SimilarityCritic(critic_field="location", weight=0.125),
            BinaryCritic(critic_field="language", weight=0.25),
            BinaryCritic(critic_field="limit", weight=0.125),
            NoneCritic(critic_field="next_page_token", weight=0.125),
        ],
    )

    return suite
