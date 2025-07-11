import json
from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_teams.client import get_client
from arcade_teams.constants import CHANNEL_PROPS, MatchType
from arcade_teams.exceptions import UniqueItemError
from arcade_teams.utils import (
    channels_request,
    filter_by_name_or_description,
    members_request,
    resolve_channel_id,
    resolve_team_id,
)


@tool(requires_auth=Microsoft(scopes=["Channel.ReadBasic.All"]))
async def get_channel(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to get the channel of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be returned with "
        "a list of all teams to pick from.",
    ],
    channel_id: Annotated[
        str | None, "The ID of the channel to get. Provide one of channel_id OR channel_name."
    ] = None,
    channel_name: Annotated[
        str | None,
        "The name of the channel to get. Prefer providing a channel_id for optimal performance. "
        "Provide one of channel_id OR channel_name.",
    ] = None,
) -> Annotated[dict, "The channel."]:
    """Retrieves metadata about a channel.

    Provide exactly one of channel_id or channel_name. When available, prefer providing a
    channel_id for optimal performance.
    """
    if len({bool(channel_id), bool(channel_name)}) != 1:
        message = "Provide exactly one of channel_id OR channel_name."
        raise ToolExecutionError(message=message, developer_message=message)

    try:
        team_id = await resolve_team_id(context, team_id_or_name)
    except UniqueItemError as e:
        return {"error": e.message, "available_options": e.available_options}

    client = get_client(context.get_auth_token_or_empty())

    if channel_id:
        response = (
            await client.teams.by_team_id(team_id)
            .all_channels.by_channel_id(channel_id)
            .get(channels_request(select=CHANNEL_PROPS))
        )
        return {"channel": response}

    # Retrieve the channel by name
    response = await search_channels(
        context=context,
        team_id_or_name=team_id_or_name,
        keywords=channel_name,
        match_type=MatchType.EXACT,
    )
    if len(response["channels"]) == 0:
        message = f"No channel found with name '{channel_name}'."
        raise RetryableToolError(message=message, developer_message=message)
    elif len(response["channels"]) > 1:
        message = f"Multiple channels found with name '{channel_name}'."
        available_channels = json.dumps(response["channels"])
        raise RetryableToolError(
            message=message,
            developer_message=message,
            additional_prompt_content=f"Channels matching '{channel_name}': {available_channels}",
        )
    return {"channel": response["channels"][0]}


@tool(requires_auth=Microsoft(scopes=["Channel.ReadBasic.All"]))
async def get_channel_by_name(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to get the channel of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be returned with "
        "a list of all teams to pick from.",
    ],
    channel_name: Annotated[str, "The name of the channel to get."],
) -> Annotated[dict, "The channel."]:
    """Gets a channel by name."""
    response = await search_channels(
        context=context,
        team_id_or_name=team_id_or_name,
        keywords=channel_name,
        match_type=MatchType.EXACT,
    )
    if len(response["channels"]) == 0:
        return {"channel": None, "error": f"No channel found with name '{channel_name}'."}
    elif len(response["channels"]) > 1:
        return {
            "error": f"Multiple channels found with name '{channel_name}'",
            "channels": response["channels"],
        }
    return {"channel": response["channels"][0]}


@tool(requires_auth=Microsoft(scopes=["Channel.ReadBasic.All"]))
async def list_all_channels(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to list the channels of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be returned with "
        "a list of all teams to pick from.",
    ],
) -> Annotated[
    dict,
    "The channels in the team.",
]:
    """Lists all channels in a given team."""
    try:
        team_id = await resolve_team_id(context, team_id_or_name)
    except UniqueItemError as e:
        return {"error": e.message, "available_options": e.available_options}

    client = get_client(context.get_auth_token_or_empty())
    response = await client.teams.by_team_id(team_id).all_channels.get(
        channels_request(select=CHANNEL_PROPS)
    )
    return {"channels": response["value"]}


@tool(requires_auth=Microsoft(scopes=["Channel.ReadBasic.All"]))
async def search_channels(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to list the channels of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be returned with "
        "a list of all teams to pick from.",
    ],
    keywords: Annotated[
        str,
        "The keywords to search for in the channels.",
    ],
    match_type: Annotated[
        MatchType,
        "The type of match to use for the search. Defaults to 'partial_match_all_keywords'.",
    ] = MatchType.PARTIAL_ALL,
) -> Annotated[
    dict,
    "The channels in the team.",
]:
    """Lists the channels in a given team."""
    try:
        team_id = await resolve_team_id(context, team_id_or_name)
    except UniqueItemError as e:
        return {"error": e.message, "available_options": e.available_options}

    client = get_client(context.get_auth_token_or_empty())
    response = await client.teams.by_team_id(team_id).all_channels.get(
        channels_request(
            select=CHANNEL_PROPS,
            filter=filter_by_name_or_description(keywords, match_type),
        )
    )
    return {"channels": response["value"]}


@tool(requires_auth=Microsoft(scopes=["Channel.ReadBasic.All"]))
async def get_primary_channel(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to get the primary channel. If not provided: in case the user "
        "is a member of a single team, the tool will use it; otherwise an error will be returned "
        "with a list of all teams to pick from.",
    ],
) -> Annotated[
    dict,
    "The primary channel of a team.",
]:
    """The primary channel of a team."""
    try:
        team_id = await resolve_team_id(context, team_id_or_name)
    except UniqueItemError as e:
        return {"error": e.message, "available_options": e.available_options}

    client = get_client(context.get_auth_token_or_empty())
    response = client.teams.by_team_id(team_id).primary_channel.get(
        channels_request(select=CHANNEL_PROPS)
    )
    return {"primary_channel": response}


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
