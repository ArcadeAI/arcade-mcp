"""Query execution and HogQL generation tools."""

from typing import Annotated, Any

from arcade_mcp_server import Context, tool

from arcade_posthog._helpers import (
    POSTHOG_SECRETS,
    _api_get_draft_sql,
    _call_tool,
    _get_project_id,
    _run_posthog_query,
)


@tool(requires_secrets=POSTHOG_SECRETS)
async def run_query(
    context: Context,
    query: Annotated[dict[str, Any], "PostHog query object. For trends: {'kind': 'TrendsQuery', 'series': [{'event': '$pageview'}], 'dateRange': {'date_from': '-7d'}}. For funnels: {'kind': 'FunnelsQuery', 'series': [{'event': 'step1'}, {'event': 'step2'}]}. For HogQL: {'kind': 'HogQLQuery', 'query': 'SELECT ...'}"],
) -> dict[str, Any]:
    """Execute a raw PostHog query. Prefer the convenience tools (get_trend, get_funnel, get_retention, compare_periods) for common analytics patterns. Use this only for custom query shapes those tools don't cover. Use list_event_definitions first to discover valid event names."""
    return await _run_posthog_query(context, query)


@tool(requires_secrets=POSTHOG_SECRETS)
async def generate_hogql_from_question(
    context: Context,
    question: Annotated[str, "Natural language question about your data (e.g., 'What are the top 10 pages by pageview count this week?')"],
) -> dict[str, Any]:
    """Generate a HogQL query from a natural language question. This is slower than the convenience tools — use get_trend, get_funnel, or get_retention first. Only fall back to this for complex queries those tools can't express."""
    project_id = _get_project_id(context)

    return await _call_tool(
        _api_get_draft_sql,
        context,
        project_id=project_id,
    )
