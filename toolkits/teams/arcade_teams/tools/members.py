from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft

from arcade_teams.client import get_client
from arcade_teams.constants import MatchType
from arcade_teams.exceptions import UniqueItemError
from arcade_teams.utils import (
    build_filter_clause,
    members_request,
    resolve_channel_id,
    resolve_team_id,
)


@tool(requires_auth=Microsoft(scopes=["TeamMember.Read.All"]))
async def list_members_of_team(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to list the members of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be returned with "
        "a list of all teams to pick from.",
    ],
    limit: Annotated[
        int,
        "The maximum number of members to return. Defaults to 100, max is 999.",
    ] = 100,
) -> Annotated[
    dict,
    "The members of a team (this tool does not support pagination).",
]:
    """Lists the members of a team (this tool does not support pagination)."""
    limit = min(999, max(1, limit))
    try:
        team_id = await resolve_team_id(context, team_id_or_name)
    except UniqueItemError as e:
        return {"error": e.message, "available_options": e.available_options}

    client = get_client(context.get_auth_token_or_empty())
    response = await client.teams.by_team_id(team_id).members.get(members_request(top=limit))
    return {"members": response["value"]}


@tool(requires_auth=Microsoft(scopes=["TeamMember.Read.All"]))
async def search_members_of_team(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to list the members of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be returned with "
        "a list of all teams to pick from.",
    ],
    keywords: Annotated[
        str,
        "The keywords to search for in the members.",
    ],
    match_type: Annotated[
        MatchType,
        "The type of match to use for the search. Defaults to 'partial_match_all_keywords'.",
    ] = MatchType.PARTIAL_ALL,
    limit: Annotated[
        int,
        "The maximum number of members to return. Defaults to 100, max is 999.",
    ] = 100,
) -> Annotated[
    dict,
    "The members of a team (this tool does not support pagination).",
]:
    """Lists the members of a team (this tool does not support pagination)."""
    limit = min(999, max(1, limit))
    try:
        team_id = await resolve_team_id(context, team_id_or_name)
    except UniqueItemError as e:
        return {"error": e.message, "available_options": e.available_options}

    filter_by_name = build_filter_clause("displayName", keywords, match_type)

    client = get_client(context.get_auth_token_or_empty())
    response = await client.teams.by_team_id(team_id).members.get(
        members_request(top=limit, filter=filter_by_name)
    )
    return {"members": response["value"]}


@tool(requires_auth=Microsoft(scopes=["Group.Read.All"]))
async def list_members_of_channel(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to list the members of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be returned with "
        "a list of all teams to pick from.",
    ],
    channel_id_or_name: Annotated[
        str | None,
        "The ID or name of the channel to list the members of. If not provided: in case the team "
        "has a single channel, the tool will use it; otherwise an error will be returned with a "
        "list of all channels to pick from.",
    ],
    limit: Annotated[
        int,
        "The maximum number of members to return. Defaults to 100, max is 999.",
    ] = 100,
) -> Annotated[
    dict,
    "The members of a channel (this tool does not support pagination).",
]:
    """Lists the members of a channel (this tool does not support pagination)."""
    limit = min(999, max(1, limit))

    try:
        team_id = await resolve_team_id(context, team_id_or_name)
        channel_id = await resolve_channel_id(context, team_id, channel_id_or_name)
    except UniqueItemError as e:
        return {"error": e.message, "available_options": e.available_options}

    client = get_client(context.get_auth_token_or_empty())
    response = (
        await client.teams.by_team_id(team_id)
        .channels.by_channel_id(channel_id)
        .members.get(members_request(top=limit))
    )
    return {"members": response["value"]}


@tool(requires_auth=Microsoft(scopes=["Group.Read.All"]))
async def search_members_of_channel(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to list the members of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be returned with "
        "a list of all teams to pick from.",
    ],
    channel_id_or_name: Annotated[
        str | None,
        "The ID or name of the channel to list the members of. If not provided: in case the team "
        "has a single channel, the tool will use it; otherwise an error will be returned with a "
        "list of all channels to pick from.",
    ],
    keywords: Annotated[
        str,
        "The keywords to search for in the members.",
    ],
    match_type: Annotated[
        MatchType,
        "The type of match to use for the search. Defaults to 'partial_match_all_keywords'.",
    ] = MatchType.PARTIAL_ALL,
    limit: Annotated[
        int,
        "The maximum number of members to return. Defaults to 100, max is 999.",
    ] = 100,
) -> Annotated[
    dict,
    "The members of a channel (this tool does not support pagination).",
]:
    """Lists the members of a channel (this tool does not support pagination)."""
    limit = min(999, max(1, limit))

    try:
        team_id = await resolve_team_id(context, team_id_or_name)
        channel_id = await resolve_channel_id(context, team_id, channel_id_or_name)
    except UniqueItemError as e:
        return {"error": e.message, "available_options": e.available_options}

    filter_by_name = build_filter_clause("displayName", keywords, match_type)

    client = get_client(context.get_auth_token_or_empty())
    response = (
        await client.teams.by_team_id(team_id)
        .channels.by_channel_id(channel_id)
        .members.get(
            members_request(
                top=limit,
                filter=filter_by_name,
            )
        )
    )
    return {"members": response["value"]}


@tool(requires_auth=Microsoft(scopes=["Chat.ReadBasic"]))
async def list_members_of_chat(
    context: ToolContext,
    chat_id: Annotated[
        str,
        "The ID of the chat to list the members of.",
    ],
) -> Annotated[
    dict,
    "The members of a chat.",
]:
    """Lists the members of a chat."""
    client = get_client(context.get_auth_token_or_empty())
    response = await client.me.chats.by_chat_id(chat_id).members.get()
    return {"members": response["value"]}
