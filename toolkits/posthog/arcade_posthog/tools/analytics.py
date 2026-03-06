"""Growth analytics convenience tools (trends, funnels, retention, period comparison)."""

from typing import Annotated, Any, Literal

from arcade_mcp_server import Context, tool

from arcade_posthog._helpers import (
    POSTHOG_SECRETS,
    _run_posthog_query,
    _shape_funnel_response,
    _shape_retention_response,
    _shape_trend_response,
)


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_trend(
    context: Context,
    event: Annotated[str, "Event name to trend (e.g., 'account_created', '$pageview'). Use list_event_definitions to discover valid names."],
    date_from: Annotated[str, "Start date: ISO date 'YYYY-MM-DD' or relative like '-7d', '-12w', '-1mStart'. Default '-8w'"] = "-8w",
    date_to: Annotated[str | None, "End date: ISO date or relative. Default is now."] = None,
    interval: Annotated[Literal["day", "week", "month"], "Grouping interval"] = "week",
    breakdown_property: Annotated[str | None, "Property to break down by (e.g., '$initial_utm_source', '$browser'). Omit for a single series."] = None,
    breakdown_type: Annotated[Literal["event", "person", "session"] | None, "Breakdown type. Default 'event'."] = None,
    math: Annotated[Literal["total", "dau", "weekly_active", "monthly_active"] | None, "Aggregation. Default 'total' (count)."] = None,
    property_filters: Annotated[list[dict[str, Any]] | None, "Property filters. Each: {'key': 'utm_source', 'value': 'twitter', 'operator': 'exact', 'type': 'event'}"] = None,
) -> dict[str, Any]:
    """Get a time-series trend for an event over a date range, optionally broken down by a property. Use for questions like: 'How many sign-ups per week over the last 12 weeks?' or 'What channels are driving traffic, broken down by utm_source?'"""
    series_item: dict[str, Any] = {"event": event, "kind": "EventsNode"}
    if math is not None:
        series_item["math"] = math

    query: dict[str, Any] = {
        "kind": "TrendsQuery",
        "series": [series_item],
        "interval": interval,
        "dateRange": {"date_from": date_from},
    }

    if date_to is not None:
        query["dateRange"]["date_to"] = date_to

    if breakdown_property is not None:
        query["breakdownFilter"] = {
            "breakdowns": [{
                "property": breakdown_property,
                "type": breakdown_type or "event",
            }],
        }

    if property_filters:
        query["properties"] = {"type": "AND", "values": [
            {"type": "AND", "values": property_filters}
        ]}

    response = await _run_posthog_query(context, query)
    if "error" in response:
        return response
    return _shape_trend_response(response)


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_funnel(
    context: Context,
    steps: Annotated[list[str], "Ordered list of event names for funnel steps (e.g., ['$pageview', 'account_created', 'api_called'])"],
    date_from: Annotated[str, "Start date: ISO date or relative like '-7d', '-30d'. Default '-7d'"] = "-7d",
    date_to: Annotated[str | None, "End date: ISO date or relative. Default is now."] = None,
    breakdown_property: Annotated[str | None, "Property to break down funnel by (e.g., '$initial_utm_source'). Shows conversion per segment."] = None,
    breakdown_type: Annotated[Literal["event", "person", "session"] | None, "Breakdown type. Default 'event'."] = None,
    funnel_window_days: Annotated[int | None, "Max days between first and last step (default 14)"] = None,
    property_filters: Annotated[list[dict[str, Any]] | None, "Property filters applied to all steps. Each: {'key': 'utm_source', 'value': 'twitter', 'operator': 'exact', 'type': 'event'}"] = None,
) -> dict[str, Any]:
    """Build a multi-step conversion funnel with optional property breakdowns. Use for questions like: 'What is the visitor-to-activated-developer conversion rate?' or 'Show the full funnel for last week broken down by UTM source.'"""
    series = [{"event": step, "kind": "EventsNode"} for step in steps]

    query: dict[str, Any] = {
        "kind": "FunnelsQuery",
        "series": series,
        "dateRange": {"date_from": date_from},
        "funnelsFilter": {"funnelWindowIntervalUnit": "day"},
    }

    if date_to is not None:
        query["dateRange"]["date_to"] = date_to

    if funnel_window_days is not None:
        query["funnelsFilter"]["funnelWindowInterval"] = funnel_window_days

    if breakdown_property is not None:
        query["breakdownFilter"] = {
            "breakdowns": [{
                "property": breakdown_property,
                "type": breakdown_type or "event",
            }],
        }

    if property_filters:
        query["properties"] = {"type": "AND", "values": [
            {"type": "AND", "values": property_filters}
        ]}

    response = await _run_posthog_query(context, query)
    if "error" in response:
        return response
    return _shape_funnel_response(response)


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_retention(
    context: Context,
    start_event: Annotated[str, "Event that defines the cohort entry (e.g., 'account_created')"],
    return_event: Annotated[str | None, "Event that counts as a return (e.g., 'api_called'). Defaults to same as start_event."] = None,
    date_from: Annotated[str, "Start date for cohort analysis: ISO date or relative. Default '-30d'"] = "-30d",
    date_to: Annotated[str | None, "End date. Default is now."] = None,
    retention_type: Annotated[Literal["retention_first_time", "retention_recurring"], "Retention type. Default 'retention_first_time' (first-time users only)."] = "retention_first_time",
    period: Annotated[Literal["Day", "Week", "Month"], "Retention period. Default 'Week'."] = "Week",
    total_intervals: Annotated[int | None, "Number of intervals to show (e.g., 7 for D0-D7, 28 for D0-D28). Default 8."] = None,
    property_filters: Annotated[list[dict[str, Any]] | None, "Property filters for the cohort. Each: {'key': 'utm_source', 'value': 'twitter', 'operator': 'exact', 'type': 'event'}"] = None,
) -> dict[str, Any]:
    """Get cohort retention data (e.g., D7/D28 retention). Use for questions like: 'What is the D7 and D28 retention rate for new users this week?' or 'How does retention compare across weeks?'"""
    query: dict[str, Any] = {
        "kind": "RetentionQuery",
        "retentionFilter": {
            "retentionType": retention_type,
            "targetEntity": {"id": start_event, "type": "events"},
            "returningEntity": {"id": return_event or start_event, "type": "events"},
            "period": period,
            "totalIntervals": total_intervals or 8,
        },
        "dateRange": {"date_from": date_from},
    }

    if date_to is not None:
        query["dateRange"]["date_to"] = date_to

    if property_filters:
        query["properties"] = {"type": "AND", "values": [
            {"type": "AND", "values": property_filters}
        ]}

    response = await _run_posthog_query(context, query)
    if "error" in response:
        return response
    return _shape_retention_response(response)


@tool(requires_secrets=POSTHOG_SECRETS)
async def compare_periods(
    context: Context,
    event: Annotated[str, "Event name to compare (e.g., 'account_created')"],
    current_date_from: Annotated[str, "Start of current period: ISO date or relative (e.g., '-7d', '2025-01-06')"],
    current_date_to: Annotated[str | None, "End of current period. Default is now."] = None,
    previous_date_from: Annotated[str | None, "Start of comparison period. Default auto-calculates same duration before current period."] = None,
    previous_date_to: Annotated[str | None, "End of comparison period."] = None,
    interval: Annotated[Literal["day", "week", "month"], "Grouping interval. Default 'day'."] = "day",
    math: Annotated[Literal["total", "dau", "weekly_active", "monthly_active"] | None, "Aggregation. Default 'total'."] = None,
) -> dict[str, Any]:
    """Compare the same metric across two date ranges side-by-side. Use for questions like: 'How do sign-ups this week compare to last week?' or 'Compare pre-campaign vs post-campaign DAU.'"""
    series_item: dict[str, Any] = {"event": event, "kind": "EventsNode"}
    if math is not None:
        series_item["math"] = math

    query: dict[str, Any] = {
        "kind": "TrendsQuery",
        "series": [series_item],
        "interval": interval,
        "dateRange": {"date_from": current_date_from},
        "compareFilter": {"compare": True},
    }

    if current_date_to is not None:
        query["dateRange"]["date_to"] = current_date_to

    # If explicit previous period provided, use it; otherwise PostHog auto-calculates
    if previous_date_from is not None:
        query["compareFilter"]["compare_to"] = previous_date_from

    response = await _run_posthog_query(context, query)
    if "error" in response:
        return response
    return _shape_trend_response(response)


@tool(requires_secrets=POSTHOG_SECRETS)
async def get_trends(
    context: Context,
    events: Annotated[list[str], "List of event names to trend (e.g., ['$pageview', 'account_created', 'api_called'])"],
    date_from: Annotated[str, "Start date: ISO date 'YYYY-MM-DD' or relative like '-7d', '-12w'. Default '-8w'"] = "-8w",
    date_to: Annotated[str | None, "End date: ISO date or relative. Default is now."] = None,
    interval: Annotated[Literal["day", "week", "month"], "Grouping interval"] = "week",
    math: Annotated[Literal["total", "dau", "weekly_active", "monthly_active"] | None, "Aggregation. Default 'total' (count)."] = None,
) -> dict[str, Any]:
    """Batch trend query: get time-series data for multiple events in one call. Returns results per event with partial success — individual events that fail won't block others. Use for the weekly deck workflow instead of calling get_trend multiple times."""
    series = []
    for ev in events:
        item: dict[str, Any] = {"event": ev, "kind": "EventsNode"}
        if math is not None:
            item["math"] = math
        series.append(item)

    query: dict[str, Any] = {
        "kind": "TrendsQuery",
        "series": series,
        "interval": interval,
        "dateRange": {"date_from": date_from},
    }

    if date_to is not None:
        query["dateRange"]["date_to"] = date_to

    response = await _run_posthog_query(context, query)
    if "error" in response:
        return response
    return _shape_trend_response(response)
