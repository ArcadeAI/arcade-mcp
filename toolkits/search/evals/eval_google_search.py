from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    NumericCritic,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_search
from arcade_search.tools import search_google

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)

catalog = ToolCatalog()
# Register the Google Search tool
catalog.add_module(arcade_search)


@tool_eval()
def google_search_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the Google Search tool."""
    suite = EvalSuite(
        name="Google Search Tool Evaluation",
        system_message="You are an AI assistant that can perform web searches using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    # Simple search query with default results
    suite.add_case(
        name="Simple search query with default results",
        user_message="Search for 'Climate change effects on polar bears' on Google.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_google,
                args={
                    "query": "Climate change effects on polar bears",
                    "n_results": 5,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=1.0),
        ],
    )

    # Search query with specific number of results
    suite.add_case(
        name="Search query with specific number of results",
        user_message="Find the top 3 articles about quantum computing.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_google,
                args={
                    "query": "articles about quantum computing",
                    "n_results": 3,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=0.7),
            NumericCritic(
                critic_field="n_results",
                weight=0.3,
                value_range=(1, 100),
            ),
        ],
    )

    # Search query with 'n' results specified in words
    suite.add_case(
        name="Search query with 'n' results specified in words",
        user_message="Give me five recipes for vegan lasagna.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_google,
                args={
                    "query": "recipes for vegan lasagna",
                    "n_results": 5,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=0.7),
            NumericCritic(
                critic_field="n_results",
                weight=0.3,
                value_range=(1, 100),
            ),
        ],
    )

    # Ambiguous number of results
    suite.add_case(
        name="Ambiguous number of results",
        user_message="Find articles about climate change impacts 10.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_google,
                args={
                    "query": "articles about climate change impacts 10",
                    "n_results": 5,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=1.0),
        ],
    )

    # Search query with multiple instructions
    suite.add_case(
        name="Search query with multiple instructions",
        user_message="Search for the latest news on electric cars, and tell me about Tesla's new model.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_google,
                args={
                    "query": "latest news on electric cars",
                    "n_results": 5,
                },
            ),
            ExpectedToolCall(
                func=search_google,
                args={
                    "query": "Tesla's new model",
                    "n_results": 5,
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=1.0),
        ],
    )

    # Search with stop words and filler words
    suite.add_case(
        name="Search with stop words and filler words",
        user_message="Could you please search for the best ways to learn French?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_google,
                args={
                    "query": "best ways to learn French",
                    "n_results": 5,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=1.0),
        ],
    )

    # No clear query given
    suite.add_case(
        name="No clear query given",
        user_message="Find it for me.",
        expected_tool_calls=[],
        critics=[],
    )

    # Search query with special characters
    suite.add_case(
        name="Search query with special characters",
        user_message="Find me '@OpenAI's latest research papers'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_google,
                args={
                    "query": "@OpenAI's latest research papers",
                    "n_results": 5,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=1.0),
        ],
    )

    # Search query with complex instructions
    suite.add_case(
        name="Search query with complex instructions",
        user_message="I need information about the impact of deforestation in the Amazon over the past decade.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_google,
                args={
                    "query": "impact of deforestation in the Amazon over the past decade",
                    "n_results": 5,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=1.0),
        ],
    )

    # Search query in a different language
    suite.add_case(
        name="Search query in a different language",
        user_message="Busca información sobre la economía de España.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_google,
                args={
                    "query": "economía de España",
                    "n_results": 5,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=1.0),
        ],
    )

    # Search query with numeric data
    suite.add_case(
        name="Search query with numeric data",
        user_message="What was the population of Japan in 2020?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_google,
                args={
                    "query": "population of Japan in 2020",
                    "n_results": 5,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=1.0),
        ],
    )

    return suite
