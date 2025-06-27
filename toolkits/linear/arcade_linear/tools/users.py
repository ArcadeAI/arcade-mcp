from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2

from arcade_linear.client import LinearClient
from arcade_linear.utils import (
    add_pagination_info,
    clean_user_data,
    resolve_team_by_name,
)


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["read"]))
async def get_users(
    context: ToolContext,
    email: Annotated[
        str | None,
        "Email address to filter users by. Provide full email (e.g. 'user@company.com'). "
        "Defaults to None (all users).",
    ] = None,
    team: Annotated[
        str | None,
        "Team name or ID to filter users by. Provide team name (e.g. 'Frontend', 'Backend') or team ID. "
        "Defaults to None (all teams).",
    ] = None,
    include_guests: Annotated[
        bool, "Whether to include guest users in results. Defaults to False (team members only)."
    ] = False,
    active_only: Annotated[
        bool, "Whether to only return active users. Defaults to True (exclude inactive users)."
    ] = True,
    limit: Annotated[
        int, "Maximum number of users to return. Min 1, max 100. Defaults to 50."
    ] = 50,
    after_cursor: Annotated[
        str | None,
        "Cursor for pagination - get users after this cursor. Use the 'end_cursor' from previous response. "
        "Defaults to None (start from beginning).",
    ] = None,
) -> Annotated[dict[str, Any], "Users in the workspace with their information"]:
    """Get Linear workspace users and their information

    This tool retrieves user information from your Linear workspace, including team members,
    their contact details, and user metadata. Use this for user discovery and contact information.

    WHEN TO USE THIS TOOL:
    - "Show me all users in the workspace" → Use this tool
    - "Find users in the Frontend team" → Use this tool with team filter
    - "Get contact info for all team members" → Use this tool
    - "Who are the active users?" → Use this tool with active_only=True
    - "List all engineers" → Use this tool with team filter
    - ANY question about user information, team membership, or contact details

    What this tool provides:
    - User basic information (name, email, display name)
    - User status and activity information
    - Team membership and user roles
    - Contact information and avatars
    - User account metadata

    When NOT to use this tool:
    - Finding issues assigned to users - Use 'search_issues' with assignee filter
    - Getting user's specific assigned work - Use 'search_issues' with assignee='me'
    - Managing or updating user information - This is read-only

    For assigned issues, use search_issues with assignee parameter instead.
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

    # Get users
    users_response = await client.get_users(
        first=limit,
        after=after_cursor,
        team_id=team_id,
        include_guests=include_guests,
    )

    # Clean and format users
    cleaned_users = [clean_user_data(user) for user in users_response["nodes"]]

    response = {
        "users": cleaned_users,
        "total_count": len(cleaned_users),
        "filters": {
            "team": team,
            "include_guests": include_guests,
        },
    }

    # Add pagination info
    if "pageInfo" in users_response:
        add_pagination_info(response, users_response["pageInfo"])

    return response
