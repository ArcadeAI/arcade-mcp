"""CLI entrypoint for arcade-posthog MCP server."""

import sys
from typing import cast

from arcade_mcp_server import MCPApp
from arcade_mcp_server.mcp_app import TransportType

import arcade_posthog

app = MCPApp(
    name="arcade_posthog",
    instructions=(
        "PostHog analytics tools for growth metrics, funnels, retention, feature flags, "
        "experiments, and surveys.\n"
        "\n"
        "FIRST STEP: Call check_connection to verify credentials and confirm the active project.\n"
        "\n"
        "DISCOVERY WORKFLOW: list_event_definitions → list_properties(event_name=...) to find "
        "events and their properties.\n"
        "\n"
        "ANALYTICS (prefer these over run_query):\n"
        "• get_trend / get_trends (batch) — time-series metrics, breakdowns by property\n"
        "• get_funnel — multi-step conversion with optional UTM/property breakdowns\n"
        "• get_retention — D7/D28 cohort retention\n"
        "• compare_periods — side-by-side date range comparison\n"
        "\n"
        "EXPERIMENTS: Use create_experiment_with_flag to create both the flag and experiment "
        "in one step.\n"
        "\n"
        "FALLBACK: search_docs when other tools return unexpected results or you need HogQL "
        "syntax help."
    ),
)

app.add_tools_from_module(arcade_posthog)


def main() -> None:
    """CLI entrypoint."""
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
    app.run(transport=cast(TransportType, transport), host=host, port=port)


if __name__ == "__main__":
    main()
