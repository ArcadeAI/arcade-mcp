from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2

from arcade_linear.client import LinearClient
from arcade_linear.utils import (
    add_pagination_info,
    clean_team_data,
    parse_date_string,
    validate_date_format,
)


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["read"]))
async def get_teams(
    context: ToolContext,
    team_name: Annotated[
        str | None,
        "Filter by team name. Provide specific team name (e.g. 'Frontend', 'Product Web') "
        "or partial name. Use this to find specific teams or check team membership. "
        "Defaults to None (all teams).",
    ] = None,
    include_archived: Annotated[
        bool, "Whether to include archived teams in results. Defaults to False."
    ] = False,
    created_after: Annotated[
        str | None,
        "Filter teams created after this date. Can be:\n"
        "- Relative date string (e.g. 'last month', 'this week', 'yesterday')\n"
        "- ISO date string (e.g. '2024-01-01')\n"
        "Defaults to None (all time).",
    ] = None,
    limit: Annotated[
        int, "Maximum number of teams to return. Min 1, max 100. Defaults to 50."
    ] = 50,
    after_cursor: Annotated[
        str | None,
        "Cursor for pagination - get teams after this cursor. Use the 'end_cursor' "
        "from previous response. Defaults to None (start from beginning).",
    ] = None,
) -> Annotated[dict[str, Any], "Teams in the workspace with member information"]:
    """Get Linear teams and team information including team members

    This tool retrieves team information from your Linear workspace, including team details,
    settings, and member information. Use this tool for team discovery and team membership queries.

    WHEN TO USE THIS TOOL:
    - "Show me all teams" → Use this tool
    - "Who is in the 'Product Web' team?" → Use this tool with team_name="Product Web"
    - "What teams exist in our workspace?" → Use this tool
    - "Find the Frontend team" → Use this tool with team_name="Frontend"
    - "Which teams were created recently?" → Use this tool with created_after filter
    - "List all active teams" → Use this tool with include_archived=False
    - ANY question about team information, team discovery, or team membership

    What this tool provides:
    - Team basic information (name, key, description)
    - Team members and their roles
    - Team settings and configuration
    - Team creation and status information
    - Team hierarchy and relationships

    When NOT to use this tool:
    - Finding individual users across teams - Use get_users
    - Getting user-specific assigned issues - Use get_assigned_issues
    - Searching for issues within teams - Use search_issues with team filter

    This tool is the primary way to get team information and answer "who is in team X" questions.
    """

    # Validate inputs
    limit = max(1, min(limit, 100))

    # Parse and validate date
    created_after_date = None
    if created_after:
        # Validate and parse string (handles DateRange enum strings internally)
        validate_date_format("created_after", created_after)
        created_after_date = parse_date_string(created_after)

    client = LinearClient(context.get_auth_token_or_empty())

    # Get teams with filtering
    teams_response = await client.get_teams(
        first=limit,
        after=after_cursor,
        include_archived=include_archived,
        name_filter=team_name,
    )

    # Apply additional filtering if needed
    teams = teams_response["nodes"]

    # Filter by creation date if specified
    if created_after_date:
        filtered_teams = []
        for team in teams:
            team_created_at = parse_date_string(team.get("createdAt", ""))
            if team_created_at and team_created_at >= created_after_date:
                filtered_teams.append(team)
        teams = filtered_teams

    # Clean and format teams
    cleaned_teams = [clean_team_data(team) for team in teams]

    response = {
        "teams": cleaned_teams,
        "total_count": len(cleaned_teams),
        "filters": {
            "team_name": team_name,
            "include_archived": include_archived,
            "created_after": created_after,
        },
    }

    # Add pagination info
    if "pageInfo" in teams_response:
        add_pagination_info(response, teams_response["pageInfo"])

    return response
