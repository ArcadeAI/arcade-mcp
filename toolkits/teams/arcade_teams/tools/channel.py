from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft
from arcade_tdk.errors import ToolExecutionError
from msgraph.generated.models.chat_message_type import ChatMessageType

from arcade_teams.client import get_client
from arcade_teams.constants import CHANNEL_PROPS, MatchType
from arcade_teams.serializers import serialize_channel, serialize_chat_message, serialize_member
from arcade_teams.utils import (
    build_offset_pagination,
    channels_request,
    filter_channels_by_name,
    find_unique_channel_by_name,
    is_channel_id,
    members_request,
    messages_request,
    resolve_channel_id,
    resolve_team_id,
)


@tool(requires_auth=Microsoft(scopes=["Channel.ReadBasic.All", "Team.ReadBasic.All"]))
async def get_channel(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to get the channel of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be returned with "
        "a list of all teams to pick from.",
    ],
    channel_id_or_name: Annotated[str, "The ID or name of the channel to get."],
) -> Annotated[dict, "The channel."]:
    """Retrieves metadata about a channel.

    When available, prefer providing a channel_id for optimal performance.
    """
    team_id = await resolve_team_id(context, team_id_or_name)

    client = get_client(context.get_auth_token_or_empty())

    if is_channel_id(channel_id_or_name):
        response = (
            await client.teams.by_team_id(team_id)
            .channels.by_channel_id(channel_id_or_name)
            .get(channels_request(select=CHANNEL_PROPS))
        )
        return {"channel": serialize_channel(response)}

    return {"channel": await find_unique_channel_by_name(context, team_id, channel_id_or_name)}


@tool(requires_auth=Microsoft(scopes=["Channel.ReadBasic.All", "Team.ReadBasic.All"]))
async def list_channels(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to list the channels of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be returned with "
        "a list of all teams to pick from.",
    ],
    limit: Annotated[
        int,
        "The maximum number of channels to return. Defaults to 50, max is 100.",
    ] = 50,
    offset: Annotated[int, "The offset to start from."] = 0,
) -> Annotated[
    dict,
    "The channels in the team.",
]:
    """Lists channels in a given team (including incoming channels shared with the team)."""
    limit = min(100, max(1, limit)) + offset

    team_id = await resolve_team_id(context, team_id_or_name)
    client = get_client(context.get_auth_token_or_empty())
    response = await client.teams.by_team_id(team_id).all_channels.get(
        channels_request(select=CHANNEL_PROPS)
    )
    channels = [serialize_channel(channel) for channel in response.value]
    channels = channels[offset : offset + limit]

    return {
        "channels": channels,
        "count": len(channels),
        "pagination": build_offset_pagination(channels, limit, offset),
    }


@tool(requires_auth=Microsoft(scopes=["Channel.ReadBasic.All", "Team.ReadBasic.All"]))
async def search_channels(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to list the channels of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be raised with "
        "a list of available teams to pick from.",
    ],
    keywords: Annotated[
        list[str],
        "The keywords to search for in channel names.",
    ],
    match_type: Annotated[
        MatchType,
        f"The type of match to use for the search. Defaults to '{MatchType.PARTIAL_ALL.value}'.",
    ] = MatchType.PARTIAL_ALL,
    limit: Annotated[
        int, "The maximum number of channels to return. Defaults to 50. Max of 100."
    ] = 50,
    offset: Annotated[int, "The offset to start from."] = 0,
) -> Annotated[
    dict,
    "The channels in the team.",
]:
    """Lists the channels in a given team."""
    if not keywords:
        message = "At least one keyword is required."
        raise ToolExecutionError(message=message, developer_message=message)

    limit = min(100, max(1, limit)) + offset

    team_id = await resolve_team_id(context, team_id_or_name)

    client = get_client(context.get_auth_token_or_empty())
    response = await client.teams.by_team_id(team_id).all_channels.get(
        channels_request(select=CHANNEL_PROPS)
    )

    channels = filter_channels_by_name(
        channels=response.value,
        keywords=keywords,
        match_type=match_type,
        serializer=serialize_channel,
    )

    channels = channels[offset : offset + limit]

    return {
        "channels": channels,
        "count": len(channels),
        "pagination": build_offset_pagination(channels, limit, offset),
    }


@tool(requires_auth=Microsoft(scopes=["Channel.ReadBasic.All", "Team.ReadBasic.All"]))
async def get_primary_channel(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to get the primary channel. If not provided: in case the user "
        "is a member of a single team, the tool will use it; otherwise an error will be returned "
        "with a list of all teams to pick from.",
    ],
) -> Annotated[
    dict[str, dict | None],
    "The primary channel of a team. If no primary channel is set, returns None.",
]:
    """The primary channel of a team."""
    team_id = await resolve_team_id(context, team_id_or_name)
    client = get_client(context.get_auth_token_or_empty())
    response = await client.teams.by_team_id(team_id).primary_channel.get(
        channels_request(select=CHANNEL_PROPS)
    )

    return {"primary_channel": serialize_channel(response) if response else None}


@tool(requires_auth=Microsoft(scopes=["Group.Read.All"]))
async def list_channel_members(
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
        "The maximum number of members to return. Defaults to 50, max is 999.",
    ] = 50,
    offset: Annotated[int, "The offset to start from."] = 0,
) -> Annotated[
    dict,
    "The members of a channel.",
]:
    """Lists the members of a channel.

    The Microsoft Graph API returns only up to the first 999 members of any channel.
    """
    limit = min(999, max(1, limit)) + offset
    offset = min(offset, 999 - limit)

    team_id = await resolve_team_id(context, team_id_or_name)
    channel_id = await resolve_channel_id(context, team_id, channel_id_or_name)

    client = get_client(context.get_auth_token_or_empty())
    response = (
        await client.teams.by_team_id(team_id)
        .channels.by_channel_id(channel_id)
        .members.get(members_request(top=limit))
    )
    members = [serialize_member(member) for member in response.value]
    members = members[offset : offset + limit]
    return {
        "members": members,
        "count": len(members),
        "pagination": build_offset_pagination(members, limit, offset),
    }


@tool(requires_auth=Microsoft(scopes=["ChannelMessage.Read.All", "Team.ReadBasic.All"]))
async def get_channel_messages(
    context: ToolContext,
    team_id_or_name: Annotated[
        str | None,
        "The ID or name of the team to get the messages of. If not provided: in case the user is "
        "a member of a single team, the tool will use it; otherwise an error will be returned with "
        "a list of all teams to pick from.",
    ],
    channel_id_or_name: Annotated[str, "The ID or name of the channel to get the messages of."],
    limit: Annotated[
        int,
        "The maximum number of messages to return. Defaults to 50, max is 50.",
    ] = 50,
) -> Annotated[dict, "The messages in the channel."]:
    """Gets the messages in a channel."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    team_id = await resolve_team_id(context, team_id_or_name)
    channel_id = await resolve_channel_id(context, team_id, channel_id_or_name)

    response = (
        await client.teams.by_team_id(team_id)
        .channels.by_channel_id(channel_id)
        .messages.get(messages_request(top=limit, expand=["replies"]))
    )

    messages = [
        serialize_chat_message(message)
        for message in response.value
        if message.message_type == ChatMessageType.Message
    ]

    return {
        "messages": messages,
        "count": len(messages),
    }
