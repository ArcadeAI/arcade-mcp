from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Linear

from arcade_linear.client import LinearClient
from arcade_linear.utils import (
    add_pagination_info,
    clean_team_data,
    parse_date_string,
    validate_date_format,
)


@tool(requires_auth=Linear(scopes=["read"]))
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
        "- ISO date string (e.g. 'YYYY-MM-DD')\n"
        "Defaults to None (all time).",
    ] = None,
    limit: Annotated[
        int, "Maximum number of teams to return. Min 1, max 100. Defaults to 50."
    ] = 50,
    end_cursor: Annotated[
        str | None,
        "Cursor for pagination - get teams after this cursor. Use the 'end_cursor' "
        "from previous response. Defaults to None (start from beginning).",
    ] = None,
) -> Annotated[dict[str, Any], "Teams in the workspace with member information"]:
    """Get Linear teams and team information including team members

    This tool retrieves team information from your Linear workspace, including team details,
    settings, and member information. Use this tool for team discovery and team membership queries.

    What this tool provides:
    - Team basic information (name, key, description)
    - Team members and their roles
    - Team settings and configuration
    - Team creation and status information
    - Team hierarchy and relationships

    This tool is the primary way to get team information.
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
        after=end_cursor,
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
    if "pageInfo" in teams_response and teams_response["pageInfo"].get("hasNextPage"):
        add_pagination_info(response, teams_response["pageInfo"])

    return response
