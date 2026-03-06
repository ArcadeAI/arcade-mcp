"""PostHog tool functions for arcade_posthog."""

from arcade_posthog.tools.analytics import (
    compare_periods,
    get_funnel,
    get_retention,
    get_trend,
    get_trends,
)
from arcade_posthog.tools.connection import check_connection
from arcade_posthog.tools.dashboards import (
    add_insight_to_dashboard,
    create_dashboard,
    delete_dashboard,
    get_dashboard,
    list_dashboards,
    update_dashboard,
)
from arcade_posthog.tools.discovery import (
    list_event_definitions,
    list_properties,
    search_docs,
)
from arcade_posthog.tools.errors import get_error_details, list_errors
from arcade_posthog.tools.experiments import (
    create_experiment,
    create_experiment_with_flag,
    delete_experiment,
    get_experiment,
    get_experiment_results,
    list_experiments,
    update_experiment,
)
from arcade_posthog.tools.feature_flags import (
    create_feature_flag,
    delete_feature_flag,
    get_feature_flag,
    list_feature_flags,
    update_feature_flag,
)
from arcade_posthog.tools.insights import (
    create_insight_from_query,
    delete_insight,
    get_insight,
    list_insights,
    update_insight,
)
from arcade_posthog.tools.organizations import (
    get_organization_details,
    list_organizations,
    list_projects,
)
from arcade_posthog.tools.queries import generate_hogql_from_question, run_query
from arcade_posthog.tools.surveys import (
    create_survey,
    delete_survey,
    get_all_survey_stats,
    get_survey,
    get_survey_stats,
    list_surveys,
    update_survey,
)

__all__ = [
    "add_insight_to_dashboard",
    "check_connection",
    "compare_periods",
    "create_dashboard",
    "create_experiment",
    "create_experiment_with_flag",
    "create_feature_flag",
    "create_insight_from_query",
    "create_survey",
    "delete_dashboard",
    "delete_experiment",
    "delete_feature_flag",
    "delete_insight",
    "delete_survey",
    "generate_hogql_from_question",
    "get_all_survey_stats",
    "get_dashboard",
    "get_error_details",
    "get_experiment",
    "get_experiment_results",
    "get_feature_flag",
    "get_funnel",
    "get_insight",
    "get_organization_details",
    "get_retention",
    "get_survey",
    "get_survey_stats",
    "get_trend",
    "get_trends",
    "list_dashboards",
    "list_errors",
    "list_event_definitions",
    "list_experiments",
    "list_feature_flags",
    "list_insights",
    "list_organizations",
    "list_projects",
    "list_properties",
    "list_surveys",
    "run_query",
    "search_docs",
    "update_dashboard",
    "update_experiment",
    "update_feature_flag",
    "update_insight",
    "update_survey",
]
