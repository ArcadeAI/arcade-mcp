"""Adversarial evaluation suite for arcade_posthog tools.

Run with: arcade evals evals/
"""

from arcade_core import ToolCatalog
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)

import arcade_posthog
from arcade_posthog.tools.analytics import (
    compare_periods,
    get_funnel,
    get_retention,
    get_trend,
    get_trends,
)
from arcade_posthog.tools.connection import check_connection
from arcade_posthog.tools.dashboards import create_dashboard, get_dashboard, list_dashboards
from arcade_posthog.tools.discovery import list_event_definitions, list_properties, search_docs
from arcade_posthog.tools.errors import list_errors
from arcade_posthog.tools.experiments import (
    create_experiment_with_flag,
    list_experiments,
)
from arcade_posthog.tools.feature_flags import (
    create_feature_flag,
    get_feature_flag,
    list_feature_flags,
)
from arcade_posthog.tools.insights import list_insights
from arcade_posthog.tools.queries import run_query
from arcade_posthog.tools.surveys import get_survey_stats, list_surveys

rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_posthog)


@tool_eval()
def posthog_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="PostHog Tools Evaluation",
        system_message=(
            "You are an AI assistant with access to PostHog analytics tools. "
            "Use them to help users analyze product data, manage feature flags, "
            "run experiments, and track growth metrics."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # --- Connection ---

    suite.add_case(
        name="check_connection",
        user_message="Check if my PostHog connection is working",
        expected_tool_calls=[ExpectedToolCall(func=check_connection, args={})],
    )

    # --- Dashboards ---

    suite.add_case(
        name="list_dashboards",
        user_message="Show me all my dashboards",
        expected_tool_calls=[ExpectedToolCall(func=list_dashboards, args={})],
    )

    suite.add_case(
        name="get_dashboard_by_name",
        user_message="Get the dashboard called Growth Overview",
        expected_tool_calls=[
            ExpectedToolCall(func=get_dashboard, args={"dashboard_name": "Growth Overview"}),
        ],
        critics=[SimilarityCritic(critic_field="dashboard_name", weight=1.0)],
    )

    suite.add_case(
        name="create_dashboard",
        user_message="Create a dashboard named Q1 Metrics",
        expected_tool_calls=[
            ExpectedToolCall(func=create_dashboard, args={"name": "Q1 Metrics"}),
        ],
        critics=[SimilarityCritic(critic_field="name", weight=1.0)],
    )

    # --- Feature Flags ---

    suite.add_case(
        name="list_feature_flags",
        user_message="List all feature flags",
        expected_tool_calls=[ExpectedToolCall(func=list_feature_flags, args={})],
    )

    suite.add_case(
        name="get_feature_flag_by_key",
        user_message="Get the feature flag with key new-checkout",
        expected_tool_calls=[
            ExpectedToolCall(func=get_feature_flag, args={"flag_key": "new-checkout"}),
        ],
        critics=[BinaryCritic(critic_field="flag_key", weight=1.0)],
    )

    suite.add_case(
        name="create_feature_flag",
        user_message="Create a feature flag called beta-pricing",
        expected_tool_calls=[
            ExpectedToolCall(func=create_feature_flag, args={"key": "beta-pricing"}),
        ],
        critics=[SimilarityCritic(critic_field="key", weight=1.0)],
    )

    # --- Analytics ---

    suite.add_case(
        name="get_trend_pageviews",
        user_message="Show me the trend of pageview events over the last 30 days",
        expected_tool_calls=[
            ExpectedToolCall(func=get_trend, args={"event": "$pageview", "date_from": "-30d"}),
        ],
        critics=[
            BinaryCritic(critic_field="event", weight=0.5),
            SimilarityCritic(critic_field="date_from", weight=0.5),
        ],
    )

    suite.add_case(
        name="get_trends_batch",
        user_message="Get trends for signup and purchase events this week",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_trends, args={"events": ["signup", "purchase"], "date_from": "-7d"}
            ),
        ],
        critics=[SimilarityCritic(critic_field="events", weight=0.5)],
    )

    suite.add_case(
        name="get_funnel",
        user_message="What's the conversion funnel from pageview to signup to purchase?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_funnel, args={"steps": ["$pageview", "signup", "purchase"]}
            ),
        ],
        critics=[SimilarityCritic(critic_field="steps", weight=1.0)],
    )

    suite.add_case(
        name="get_retention",
        user_message="Show D7 retention for users who signed up",
        expected_tool_calls=[
            ExpectedToolCall(func=get_retention, args={"start_event": "signup"}),
        ],
        critics=[SimilarityCritic(critic_field="start_event", weight=1.0)],
    )

    suite.add_case(
        name="compare_periods",
        user_message="Compare signups this week vs last week",
        expected_tool_calls=[
            ExpectedToolCall(
                func=compare_periods, args={"event": "signup", "current_date_from": "-7d"}
            ),
        ],
        critics=[
            BinaryCritic(critic_field="event", weight=0.5),
            SimilarityCritic(critic_field="current_date_from", weight=0.5),
        ],
    )

    suite.add_case(
        name="run_hogql_query",
        user_message="Run this HogQL query: SELECT count() FROM events WHERE event = '$pageview'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=run_query,
                args={
                    "query": {
                        "kind": "HogQLQuery",
                        "query": "SELECT count() FROM events WHERE event = '$pageview'",
                    }
                },
            ),
        ],
        critics=[SimilarityCritic(critic_field="query", weight=1.0)],
    )

    # --- Surveys ---

    suite.add_case(
        name="list_surveys",
        user_message="List all active surveys",
        expected_tool_calls=[ExpectedToolCall(func=list_surveys, args={})],
    )

    suite.add_case(
        name="get_survey_stats",
        user_message="Get results for survey 456",
        expected_tool_calls=[
            ExpectedToolCall(func=get_survey_stats, args={"survey_id": 456}),
        ],
        critics=[BinaryCritic(critic_field="survey_id", weight=1.0)],
    )

    # --- Experiments ---

    suite.add_case(
        name="list_experiments",
        user_message="List all running experiments",
        expected_tool_calls=[ExpectedToolCall(func=list_experiments, args={})],
    )

    suite.add_case(
        name="create_experiment_with_flag",
        user_message="Create an experiment called pricing-test with flag pricing-v2",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_experiment_with_flag,
                args={"name": "pricing-test", "feature_flag_key": "pricing-v2"},
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="name", weight=0.5),
            SimilarityCritic(critic_field="feature_flag_key", weight=0.5),
        ],
    )

    # --- Discovery ---

    suite.add_case(
        name="list_event_definitions",
        user_message="What events are available in PostHog?",
        expected_tool_calls=[ExpectedToolCall(func=list_event_definitions, args={})],
    )

    suite.add_case(
        name="list_properties_for_event",
        user_message="What properties does the $pageview event have?",
        expected_tool_calls=[
            ExpectedToolCall(func=list_properties, args={"event_name": "$pageview"}),
        ],
        critics=[BinaryCritic(critic_field="event_name", weight=1.0)],
    )

    # --- Multi-step workflows ---

    suite.add_case(
        name="discover_then_trend",
        user_message="Find what events exist and then show me the trend for pageviews",
        expected_tool_calls=[
            ExpectedToolCall(func=list_event_definitions, args={}),
            ExpectedToolCall(func=get_trend, args={"event": "$pageview"}),
        ],
        critics=[BinaryCritic(critic_field="event", weight=1.0)],
    )

    suite.add_case(
        name="check_then_list",
        user_message="Check my connection and then list dashboards",
        expected_tool_calls=[
            ExpectedToolCall(func=check_connection, args={}),
            ExpectedToolCall(func=list_dashboards, args={}),
        ],
    )

    # --- Fallback ---

    suite.add_case(
        name="search_docs_fallback",
        user_message="How do I write a HogQL query to get unique users?",
        expected_tool_calls=[
            ExpectedToolCall(func=search_docs, args={"query": "HogQL unique users"}),
        ],
        critics=[SimilarityCritic(critic_field="query", weight=1.0)],
    )

    return suite
