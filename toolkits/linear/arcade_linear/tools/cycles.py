from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2

from arcade_linear.client import LinearClient
from arcade_linear.utils import (
    clean_cycle_data,
    clean_issue_data,
    resolve_cycle_by_name,
    resolve_team_by_name,
)


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["read"]))
async def get_current_cycle(
    context: ToolContext,
    team: Annotated[
        str,
        "Team name or ID to get the current active cycle for (e.g. 'Frontend', 'Backend', 'Product').",
    ],
) -> Annotated[dict[str, Any], "Current active cycle details"]:
    """Get the current active cycle (sprint) for a team

    This tool retrieves information about the currently active cycle/sprint for a specified team.
    In Linear, cycles represent sprints or time-boxed work periods.

    What this tool provides:
    - Current cycle details (name, number, dates, progress)
    - Team information
    - Issues in the current cycle (if any)

    When to use this tool:
    - When you need to find the current sprint for a team
    - Before adding issues to the current cycle
    - To check cycle progress and timeline
    - To see what's in the current sprint

    This tool is READ-ONLY - it cannot modify cycles.
    """

    client = LinearClient(context.get_auth_token_or_empty())

    # Resolve team
    team_id = None
    if team.startswith("team_"):  # Assume it's an ID
        team_id = team
    else:
        team_data = await resolve_team_by_name(context, team)
        if not team_data:
            return {"error": f"Team not found: {team}. Please check the team name and try again."}
        team_id = team_data["id"]

    # Get current active cycle for the team
    current_cycle = await client.get_current_cycle(team_id)

    if not current_cycle:
        return {
            "message": f"No current active cycle found for team '{team}'. The team may not have cycles enabled or no cycle is currently active.",
            "team": team,
            "current_cycle": None,
        }

    # Clean and format the cycle data
    cleaned_cycle = clean_cycle_data(current_cycle)

    return {
        "current_cycle": cleaned_cycle,
        "team": team,
        "message": f"Current active cycle for team '{team}' is '{cleaned_cycle.get('name', cleaned_cycle.get('number', 'Unnamed'))}'",
    }


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["read"]))
async def list_cycles(
    context: ToolContext,
    team: Annotated[
        str, "Team name or ID to list cycles for (e.g. 'Frontend', 'Backend', 'Product')."
    ],
    active_only: Annotated[bool, "Whether to show only active cycles. Defaults to True."] = True,
    limit: Annotated[
        int, "Maximum number of cycles to return. Min 1, max 50. Defaults to 10."
    ] = 10,
) -> Annotated[dict[str, Any], "List of cycles for the team"]:
    """List cycles (sprints) for a team

    This tool retrieves a list of cycles/sprints for a specified team, with options to filter
    by active status and limit the number of results.

    What this tool provides:
    - List of cycles with details (name, number, dates, progress)
    - Team information
    - Filtering options for active vs all cycles

    When to use this tool:
    - When you need to see all available cycles for a team
    - To find specific cycle names or IDs
    - To check cycle history and planning
    - To see upcoming or past sprints

    This tool is READ-ONLY - it cannot modify cycles.
    """

    # Validate inputs
    limit = max(1, min(limit, 50))

    client = LinearClient(context.get_auth_token_or_empty())

    # Resolve team
    team_id = None
    if team.startswith("team_"):  # Assume it's an ID
        team_id = team
    else:
        team_data = await resolve_team_by_name(context, team)
        if not team_data:
            return {"error": f"Team not found: {team}. Please check the team name and try again."}
        team_id = team_data["id"]

    # Get cycles for the team
    cycles_response = await client.get_cycles(
        first=limit, team_id=team_id, active_only=active_only, include_completed=not active_only
    )

    cycles = cycles_response.get("nodes", [])

    # Clean and format cycle data
    cleaned_cycles = [clean_cycle_data(cycle) for cycle in cycles]

    return {
        "cycles": cleaned_cycles,
        "total_count": len(cleaned_cycles),
        "team": team,
        "active_only": active_only,
        "message": f"Found {len(cleaned_cycles)} {'active' if active_only else ''} cycles for team '{team}'",
    }


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["read"]))
async def get_cycle_issues(
    context: ToolContext,
    cycle: Annotated[str, "Cycle name, number, or ID to get issues for."],
    team: Annotated[
        str | None,
        "Team name or ID to scope the cycle lookup. Helpful when cycle names might conflict across teams.",
    ] = None,
    limit: Annotated[
        int, "Maximum number of issues to return. Min 1, max 100. Defaults to 50."
    ] = 50,
) -> Annotated[dict[str, Any], "Issues in the specified cycle"]:
    """Get all issues in a specific cycle (sprint)

    This tool retrieves all issues that are assigned to a specific cycle/sprint, with their
    current status, assignees, and other details.

    What this tool provides:
    - List of issues in the cycle with full details
    - Cycle information
    - Issue status, priority, and assignment information

    When to use this tool:
    - When you need to see what's in a specific sprint
    - To review cycle progress and completion
    - To check issue assignments within a cycle
    - For sprint planning and review meetings

    This tool is READ-ONLY - it cannot modify issues or cycles.
    """

    # Validate inputs
    limit = max(1, min(limit, 100))

    client = LinearClient(context.get_auth_token_or_empty())

    # Resolve team if provided
    team_id = None
    if team:
        if team.startswith("team_"):  # Assume it's an ID
            team_id = team
        else:
            team_data = await resolve_team_by_name(context, team)
            if not team_data:
                return {
                    "error": f"Team not found: {team}. Please check the team name and try again."
                }
            team_id = team_data["id"]

    # Resolve cycle
    cycle_id = None
    cycle_info = None

    if cycle.startswith("cycle_"):  # Assume it's an ID
        cycle_id = cycle
        cycle_info = await client.get_cycle_by_id(cycle_id)
    else:
        # Try to resolve by name/number
        if team_id:
            cycle_data = await resolve_cycle_by_name(context, cycle, team_id)
        else:
            # Search across all teams - this might be ambiguous
            cycle_data = await resolve_cycle_by_name(context, cycle, None)

        if cycle_data:
            cycle_id = cycle_data["id"]
            cycle_info = cycle_data
        else:
            return {
                "error": f"Cycle not found: {cycle}. Please check the cycle name and try again."
            }

    if not cycle_info:
        return {"error": f"Cycle not found: {cycle}. Please check the cycle ID and try again."}

    # Get issues in the cycle
    issues_response = await client.get_cycle_issues(cycle_id)
    issues = issues_response.get("nodes", [])

    # Limit results if needed
    if len(issues) > limit:
        issues = issues[:limit]

    # Clean and format issue data
    cleaned_issues = [clean_issue_data(issue) for issue in issues]
    cleaned_cycle = clean_cycle_data(cycle_info)

    return {
        "cycle": cleaned_cycle,
        "issues": cleaned_issues,
        "total_count": len(cleaned_issues),
        "message": f"Found {len(cleaned_issues)} issues in cycle '{cleaned_cycle.get('name', cleaned_cycle.get('number', 'Unnamed'))}'",
    }
