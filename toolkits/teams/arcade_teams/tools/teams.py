from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft

from arcade_teams.client import get_client
from arcade_teams.constants import MatchType
from arcade_teams.utils import build_response, filter_by_name_or_description, teams_request


@tool(requires_auth=Microsoft(scopes=["Team.ReadBasic.All"]))
async def list_user_teams(
    context: ToolContext,
) -> Annotated[
    dict,
    "The teams the current user is a direct member of.",
]:
    """Lists the teams the current user is a direct member of."""
    client = get_client(context.get_auth_token_or_empty())
    teams = await client.me.joined_teams.get()
    return {"teams": teams["value"]}


@tool(requires_auth=Microsoft(scopes=["Team.ReadBasic.All"]))
async def list_organization_teams(
    context: ToolContext,
    limit: Annotated[
        int,
        "The maximum number of teams to return. Defaults to 10, max is 50.",
    ] = 10,
    next_page_token: Annotated[
        str | None,
        "The token to use to get the next page of results.",
    ] = None,
) -> Annotated[
    dict,
    "The teams in the organization.",
]:
    """Lists the teams in the organization."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())
    response = await client.teams.get(teams_request(top=limit, skiptoken=next_page_token))
    return build_response("teams", response)


@tool(requires_auth=Microsoft(scopes=["Team.ReadBasic.All"]))
async def search_organization_teams(
    context: ToolContext,
    keywords: Annotated[
        str,
        "The keywords to search for in the team name or description.",
    ],
    match_type: Annotated[
        MatchType,
        "The type of match to use. Defaults to 'partial_match_all_keywords'.",
    ] = MatchType.PARTIAL_ALL,
    limit: Annotated[
        int,
        "The maximum number of teams to return. Defaults to 10, max is 50.",
    ] = 10,
    next_page_token: Annotated[
        str | None,
        "The token to use to get the next page of results.",
    ] = None,
) -> Annotated[
    dict,
    "Search for teams in the organization (regardless of whether the current user is a member).",
]:
    """Search for teams in the organization (regardless of whether the current user is a member)."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    response = await client.teams.get(
        teams_request(
            top=limit,
            filter=filter_by_name_or_description(keywords, match_type),
            skiptoken=next_page_token,
        )
    )
    return build_response("teams", response)
