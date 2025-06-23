import datetime
import re
from dataclasses import dataclass

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.chats.item.messages.messages_request_builder import MessagesRequestBuilder
from msgraph.generated.teams.item.all_channels.all_channels_request_builder import (
    AllChannelsRequestBuilder,
)
from msgraph.generated.teams.item.members.members_request_builder import (
    MembersRequestBuilder,
)
from msgraph.generated.teams.teams_request_builder import TeamsRequestBuilder

from arcade_teams.constants import MatchType
from arcade_teams.exceptions import MultipleItemsFoundError, NoItemsFoundError


def remove_none_values(kwargs: dict) -> dict:
    return {key: val for key, val in kwargs.items() if val is not None}


def validate_datetime_string(value: str) -> str:
    datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return value


def validate_datetime_range(start: str | None, end: str | None) -> tuple[str | None, str | None]:
    invalid_datetime_msg = (
        "Invalid {field} datetime string: {value}. "
        "Provide a string in the format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'."
    )
    start_dt = None
    end_dt = None
    if start:
        try:
            start_dt = validate_datetime_string(start)
        except ValueError as e:
            raise ToolExecutionError(
                invalid_datetime_msg.format(field="start_datetime", value=start)
            ) from e
    if end:
        try:
            end_dt = validate_datetime_string(end)
        except ValueError as e:
            raise ToolExecutionError(
                invalid_datetime_msg.format(field="end_datetime", value=end)
            ) from e
    if start_dt and end_dt and start_dt > end_dt:
        err_msg = "start_datetime must be before end_datetime."
        raise ToolExecutionError(err_msg)
    return start, end


def is_id(value: str) -> bool:
    return is_teams_id(value) or is_guid(value)


def is_teams_id(value: str) -> bool:
    return bool(re.match(r"^19:[\w\d]+@thread\.v2$", value))


def is_guid(value: str) -> bool:
    return bool(re.match(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$", value))


def config_request(
    request_builder: dataclass,
    **kwargs,
) -> RequestConfiguration:
    query_params = request_builder(**remove_none_values(kwargs))
    return RequestConfiguration(query_parameters=query_params)


def teams_request(**kwargs) -> RequestConfiguration:
    return config_request(TeamsRequestBuilder.TeamsRequestBuilderGetQueryParameters, **kwargs)


def channels_request(**kwargs) -> RequestConfiguration:
    return config_request(
        AllChannelsRequestBuilder.AllChannelsRequestBuilderGetQueryParameters, **kwargs
    )


def members_request(**kwargs) -> RequestConfiguration:
    return config_request(MembersRequestBuilder.MembersRequestBuilderGetQueryParameters, **kwargs)


def messages_request(**kwargs) -> RequestConfiguration:
    return config_request(MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters, **kwargs)


def build_response(key: str, api_response: dict) -> dict:
    pagination = {"is_last_page": True}
    if api_response.get("@odata.nextLink"):
        pagination["is_last_page"] = False
        pagination["next_page_token"] = api_response["@odata.nextLink"]
    return {key: api_response["value"], "pagination": pagination}


def build_filter_clause(
    field: str,
    keywords: str,
    match_type: MatchType,
) -> str:
    if match_type == MatchType.EXACT:
        return f"{field} eq '{keywords.casefold()}'"
    words = keywords.casefold().split()
    condition = f" {match_type.to_filter_condition().value} "
    return condition.join(f"contains({field}, '{word}')" for word in words)


def filter_by_name_or_description(
    keywords: str,
    match_type: MatchType,
) -> str:
    if match_type == MatchType.EXACT:
        return build_filter_clause("displayName", keywords, match_type)

    name_filter = build_filter_clause("displayName", keywords, match_type)
    description_filter = build_filter_clause("description", keywords, match_type)
    return f"{name_filter} or {description_filter}"


async def resolve_team_id(context: ToolContext, team_id_or_name: str) -> str:
    if not team_id_or_name:
        team = await find_unique_user_team(context)
        return team["id"]

    if is_id(team_id_or_name):
        return team_id_or_name

    team = await find_unique_team_by_name(context, team_id_or_name)
    return team["id"]


async def find_unique_user_team(context: ToolContext) -> dict:
    from arcade_teams.tools.teams import list_user_teams  # Avoid circular import

    response = await list_user_teams(context)
    teams = response["teams"]
    if len(teams) == 0:
        raise NoItemsFoundError("teams")
    if len(teams) > 1:
        raise MultipleItemsFoundError("teams", teams)
    return teams[0]


async def find_unique_team_by_name(context: ToolContext, name: str) -> dict:
    from arcade_teams.tools.teams import search_organization_teams  # Avoid circular import

    response = await search_organization_teams(
        context=context,
        keywords=name,
        match_type=MatchType.EXACT,
        limit=1,
    )
    teams = response["teams"]
    if len(teams) == 0:
        raise NoItemsFoundError("teams")
    elif len(teams) > 1:
        raise MultipleItemsFoundError("teams", teams)
    return teams[0]


async def resolve_channel_id(context: ToolContext, team_id: str, channel_id_or_name: str) -> str:
    if not channel_id_or_name:
        channel = await find_unique_channel(context, team_id)
        return channel["id"]

    if is_id(channel_id_or_name):
        return channel_id_or_name

    channel = await find_unique_channel_by_name(context, team_id, channel_id_or_name)
    return channel["id"]


async def find_unique_channel(context: ToolContext, team_id: str) -> dict:
    from arcade_teams.tools.channels import list_all_channels  # Avoid circular import

    response = await list_all_channels(context, team_id)
    channels = response["channels"]
    if len(channels) == 0:
        raise NoItemsFoundError("channels")
    if len(channels) > 1:
        raise MultipleItemsFoundError("channels", channels)
    return channels[0]


async def find_unique_channel_by_name(context: ToolContext, team_id: str, name: str) -> dict:
    from arcade_teams.tools.channels import search_channels  # Avoid circular import

    response = await search_channels(
        context=context,
        team_id_or_name=team_id,
        keywords=name,
        match_type=MatchType.EXACT,
    )
    channels = response["channels"]
    if len(channels) == 0:
        raise NoItemsFoundError("channels")
    if len(channels) > 1:
        raise MultipleItemsFoundError("channels", channels)
    return channels[0]
