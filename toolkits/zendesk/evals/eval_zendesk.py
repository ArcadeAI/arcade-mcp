from datetime import timedelta

import arcade_zendesk
from arcade_evals import (
    DatetimeCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_evals.critic import BinaryCritic, SimilarityCritic
from arcade_tdk import ToolCatalog
from arcade_zendesk.tools.search_articles import search_articles

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_zendesk)


@tool_eval()
def zendesk_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Zendesk Help Center Tools Evaluation",
        system_message=(
            "You are an AI assistant with access to Zendesk Help Center tools. "
            "Use them to help users search for knowledge base articles and documentation."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Basic search scenarios
    suite.add_case(
        name="Basic search with query only",
        user_message="Find articles about password reset",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={
                    "query": "password reset",
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=1.0),
        ],
    )

    suite.add_case(
        name="Search with specific result count",
        user_message="Show me 25 articles about API documentation",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={"query": "API documentation", "per_page": 25},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.7),
            BinaryCritic(critic_field="per_page", weight=0.3),
        ],
    )

    # Date filtering scenarios
    suite.add_case(
        name="Search with created after date filter",
        user_message="Find articles about security updates created after January 15, 2024",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={"query": "security updates", "created_after": "2024-01-15"},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.6),
            DatetimeCritic(
                critic_field="created_after", weight=0.4, tolerance=timedelta(days=1)
            ),
        ],
    )

    suite.add_case(
        name="Search with date range filter",
        user_message="Show me articles about new features created between January and June 2024",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={
                    "query": "new features",
                    "created_after": "2024-01-01",
                    "created_before": "2024-06-30",
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.4),
            DatetimeCritic(
                critic_field="created_after", weight=0.3, tolerance=timedelta(days=1)
            ),
            DatetimeCritic(
                critic_field="created_before", weight=0.3, tolerance=timedelta(days=1)
            ),
        ],
    )

    # Category and section filtering
    suite.add_case(
        name="Search by category ID only",
        user_message="Show me all articles in category 123",
        expected_tool_calls=[
            ExpectedToolCall(func=search_articles, args={"category": 123})
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="category", weight=1.0),
        ],
    )

    suite.add_case(
        name="Search with category and section filters",
        user_message="Find troubleshooting articles in category 100, section 200",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={"query": "troubleshooting", "category": 100, "section": 200},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.4),
            BinaryCritic(critic_field="category", weight=0.3),
            BinaryCritic(critic_field="section", weight=0.3),
        ],
    )

    # Label filtering (Professional/Enterprise)
    suite.add_case(
        name="Search by labels only",
        user_message="Show me articles tagged with windows and setup labels",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles, args={"label_names": "windows,setup"}
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="label_names", weight=1.0),
        ],
    )

    suite.add_case(
        name="Search with query and labels",
        user_message="Find installation guides with labels: macos, quickstart",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={"query": "installation guide", "label_names": "macos,quickstart"},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.5),
            SimilarityCritic(critic_field="label_names", weight=0.5),
        ],
    )

    # Sorting scenarios
    suite.add_case(
        name="Search sorted by creation date ascending",
        user_message="Find onboarding articles sorted by oldest first",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={
                    "query": "onboarding",
                    "sort_by": "created_at",
                    "sort_order": "asc",
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.4),
            BinaryCritic(critic_field="sort_by", weight=0.3),
            BinaryCritic(critic_field="sort_order", weight=0.3),
        ],
    )

    suite.add_case(
        name="Search sorted by most recently created",
        user_message="Show me troubleshooting guides sorted by latest creation",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={
                    "query": "troubleshooting guide",
                    "sort_by": "created_at",
                    "sort_order": "desc",
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.4),
            BinaryCritic(critic_field="sort_by", weight=0.3),
            BinaryCritic(critic_field="sort_order", weight=0.3),
        ],
    )

    # Pagination scenarios
    suite.add_case(
        name="Search with all pages requested",
        user_message="Search for all installation guides and get every result available",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={"query": "installation guide", "all_pages": True},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.7),
            BinaryCritic(critic_field="all_pages", weight=0.3),
        ],
    )

    suite.add_case(
        name="Search with limited pages",
        user_message="Find API documentation, get up to 3 pages with 50 results per page",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={"query": "API documentation", "max_pages": 3, "per_page": 50},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.4),
            BinaryCritic(critic_field="max_pages", weight=0.3),
            BinaryCritic(critic_field="per_page", weight=0.3),
        ],
    )

    # Complex search scenarios
    suite.add_case(
        name="Complex search with multiple filters",
        user_message="Find recent troubleshooting articles about login issues in category 150, created after March 2024, sorted by newest first",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={
                    "query": "login issues troubleshooting",
                    "category": 150,
                    "created_after": "2024-03-01",
                    "sort_by": "created_at",
                    "sort_order": "desc",
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.3),
            BinaryCritic(critic_field="category", weight=0.2),
            DatetimeCritic(
                critic_field="created_after", weight=0.2, tolerance=timedelta(days=1)
            ),
            BinaryCritic(critic_field="sort_by", weight=0.15),
            BinaryCritic(critic_field="sort_order", weight=0.15),
        ],
    )

    # Content control
    suite.add_case(
        name="Search without article body content",
        user_message="List article titles about billing without the full content",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles, args={"query": "billing", "include_body": False}
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.7),
            BinaryCritic(critic_field="include_body", weight=0.3),
        ],
    )

    # Edge cases
    suite.add_case(
        name="Search with exact phrase matching",
        user_message='Find articles with the exact phrase "password reset procedure"',
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={
                    "query": '"password reset procedure"',
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="query", weight=1.0),
        ],
    )

    return suite


@tool_eval()
def zendesk_pagination_eval_suite() -> EvalSuite:
    """Separate suite for pagination scenarios with context."""
    suite = EvalSuite(
        name="Zendesk Pagination Evaluation",
        system_message=(
            "You are an AI assistant with access to Zendesk Help Center tools. "
            "Use them to help users search for knowledge base articles. "
            "When users ask for more results, use appropriate pagination parameters."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Pagination with context
    suite.add_case(
        name="Initial search with pagination context",
        user_message="I need to find all troubleshooting articles. Start by showing me the first 20.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles, args={"query": "troubleshooting", "per_page": 20}
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.6),
            BinaryCritic(critic_field="per_page", weight=0.4),
        ],
    )

    suite.add_case(
        name="Request for all results after initial search",
        user_message="Actually, just get me all the troubleshooting articles at once",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_articles,
                args={"query": "troubleshooting", "all_pages": True},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.7),
            BinaryCritic(critic_field="all_pages", weight=0.3),
        ],
        additional_messages=[
            {
                "role": "user",
                "content": "I need to find all troubleshooting articles. Start by showing me the first 20.",
            },
            {
                "role": "assistant",
                "content": "I'll search for troubleshooting articles and show you the first 20 results.",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "search_articles",
                            "arguments": '{"query": "troubleshooting", "per_page": 20}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"results": [{"content": "Troubleshooting guide 1", "metadata": {"id": 1, "title": "How to troubleshoot login issues"}}], "count": 150}',
                "tool_call_id": "call_1",
                "name": "search_articles",
            },
            {
                "role": "assistant",
                "content": "I found 150 troubleshooting articles total. Here are the first 20 results. The first one is 'How to troubleshoot login issues'.",
            },
        ],
    )

    return suite
