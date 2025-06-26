from typing import Annotated, Any, Dict, List, Optional

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2

from arcade_linear.client import LinearClient
from arcade_linear.constants import ProjectStatus
from arcade_linear.utils import (
    add_pagination_info,
    clean_project_data,
    resolve_team_by_name,
    parse_date_string,
)


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["read"]))
async def get_projects(
    context: ToolContext,
    team: Annotated[
        Optional[str],
        "Team name or ID to filter projects. Provide team name (e.g. 'Frontend', 'Backend') or team ID. "
        "Defaults to None (all teams)."
    ] = None,
    status: Annotated[
        Optional[ProjectStatus],
        "Project status to filter by. Valid values: planned, started, completed, canceled, paused. "
        "Defaults to None (all statuses)."
    ] = None,
    include_archived: Annotated[
        bool,
        "Whether to include archived projects in the results. Defaults to False."
    ] = False,
    created_after: Annotated[
        Optional[str],
        "ISO date string to filter projects created after this date (e.g. '2024-01-01'). "
        "Defaults to None (all time)."
    ] = None,
    limit: Annotated[
        int,
        "Maximum number of projects to return. Min 1, max 100. Defaults to 50."
    ] = 50,
    after_cursor: Annotated[
        Optional[str],
        "Cursor for pagination - get projects after this cursor. Use the 'end_cursor' from previous response. "
        "Defaults to None (start from beginning)."
    ] = None,
) -> Annotated[Dict[str, Any], "Projects in the Linear workspace"]:
    """Get Linear projects for organization and tracking
    
    This tool retrieves project information from your Linear workspace. Projects are used
    to organize and track work across multiple issues and teams in Linear.
    
    WHEN TO USE THIS TOOL:
    - "Show me all projects" - Use this tool
    - "Find projects for the Frontend team" - Use this with team="Frontend"
    - "List active projects" - Use this with status filter
    - "Get projects created this month" - Use this with created_after filter
    - ANY question about discovering or listing projects
    
    What this tool provides:
    - List of projects in the workspace or specific team
    - Project status and progress information
    - Project timelines and milestones
    - Team assignments and project ownership
    - Issue counts and project metrics
    
    When NOT to use this tool:
    - Finding issues within projects - Use search_issues with project filter
    - Assigning issues to projects - Use assign_issue_to_container
    - Creating or updating projects - Use dedicated project management tools
    
    This tool is for project discovery and information only.
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
            if team_data:
                team_id = team_data["id"]
    
    # Parse created_after date if provided
    created_after_date = None
    if created_after:
        created_after_date = parse_date_string(created_after)
    
    # Get projects
    projects_response = await client.get_projects(
        first=limit,
        after=after_cursor,
        team_id=team_id,
        status=status,
        include_archived=include_archived,
        created_after=created_after_date,
    )
    
    # Clean and format projects
    cleaned_projects = [clean_project_data(project) for project in projects_response["nodes"]]
    
    response = {
        "projects": cleaned_projects,
        "total_count": len(cleaned_projects),
        "filters": {
            "team": team,
            "status": status.value if status and hasattr(status, 'value') else (str(status) if status else None),
            "include_archived": include_archived,
            "created_after": created_after,
        },
    }
    
    # Add pagination info
    if "pageInfo" in projects_response:
        add_pagination_info(response, projects_response["pageInfo"])
    
    return response 