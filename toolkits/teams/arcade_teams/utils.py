import datetime
import re
import uuid
from dataclasses import dataclass
from typing import Any

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.chats.item.messages.messages_request_builder import MessagesRequestBuilder
from msgraph.generated.models.aad_user_conversation_member import AadUserConversationMember
from msgraph.generated.models.chat import Chat
from msgraph.generated.models.chat_type import ChatType
from msgraph.generated.teams.item.all_channels.all_channels_request_builder import (
    AllChannelsRequestBuilder,
)
from msgraph.generated.teams.item.members.members_request_builder import (
    MembersRequestBuilder,
)
from msgraph.generated.teams.teams_request_builder import TeamsRequestBuilder
from msgraph.generated.users.item.people.people_request_builder import PeopleRequestBuilder
from pydantic import BaseModel

from arcade_teams.client import get_client
from arcade_teams.constants import ENV_VARS, MatchType, PartialMatchType
from arcade_teams.exceptions import MultipleItemsFoundError, NoItemsFoundError
from arcade_teams.serializers import serialize_chat, short_person, short_version


def remove_none_values(kwargs: dict) -> dict:
    return {key: val for key, val in kwargs.items() if val is not None}


def load_metadata(context: ToolContext, key: str) -> Any:
    try:
        return context.get_metadata(key)
    except ValueError:
        pass

    try:
        return context.get_secret(key)
    except ValueError:
        pass

    return ENV_VARS.get(key)


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
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    else:
        return True


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


def people_request(**kwargs) -> RequestConfiguration:
    return config_request(PeopleRequestBuilder.PeopleRequestBuilderGetQueryParameters, **kwargs)


def build_conversation_member(user_id: str) -> AadUserConversationMember:
    return AadUserConversationMember(
        odata_type="#microsoft.graph.aadUserConversationMember",
        roles=["owner"],
        additional_data={"user@odata_bind": f"https://graph.microsoft.com/v1.0/users('{user_id}')"},
    )


def build_pagination(response: BaseModel) -> dict:
    pagination = {"is_last_page": True}
    if response.odata_next_link:
        pagination["is_last_page"] = False
        pagination["next_page_token"] = response.odata_next_link
    return pagination


def build_search_clause(
    keywords: list[str],
    match_type: PartialMatchType,
) -> str:
    operator = match_type.to_filter_condition().value
    return f" {operator} ".join([f'"{keyword}"' for keyword in keywords])


def build_filter_clause(
    field: str,
    keywords: str,
    match_type: MatchType,
) -> str:
    if match_type == MatchType.EXACT:
        return f"{field} eq '{keywords.casefold()}'"
    words = keywords.casefold().split()
    condition = f" {match_type.to_filter_condition().value} "
    return condition.join(f"contains({field}, '{word.strip()}')" for word in words)


def build_startswith_filter_clause(
    field: str,
    starts_with: str,
    use_case_variants: bool = False,
) -> str:
    if not use_case_variants:
        return f"startswith({field}, '{starts_with}')"

    variants = generate_case_variants(starts_with)
    return " or ".join(f"startswith({field}, '{variant.strip()}')" for variant in variants)


def filter_by_name_or_description(
    keywords: str,
    match_type: MatchType,
) -> str:
    if match_type == MatchType.EXACT:
        return build_filter_clause("displayName", keywords, match_type)

    name_filter = build_filter_clause("displayName", keywords, match_type)
    description_filter = build_filter_clause("description", keywords, match_type)
    return f"{name_filter} or {description_filter}"


async def resolve_team_id(context: ToolContext, team_id_or_name: str | None) -> str:
    if not team_id_or_name:
        team = await find_unique_user_team(context=context)
        return team["id"]

    if is_id(team_id_or_name):
        return team_id_or_name

    team = await find_unique_team_by_name(context=context, name=team_id_or_name)
    return team["id"]


async def find_unique_user_team(context: ToolContext) -> dict:
    from arcade_teams.tools.teams import list_teams  # Avoid circular import

    response = await list_teams(context)
    teams = response["teams"]
    if len(teams) == 0:
        raise NoItemsFoundError("teams")
    if len(teams) > 1:
        raise MultipleItemsFoundError("teams", [short_version(team) for team in teams])
    return teams[0]


async def find_unique_team_by_name(context: ToolContext, name: str) -> dict:
    from arcade_teams.tools.teams import search_teams  # Avoid circular import

    response = await search_teams(
        context=context,
        team_name_starts_with=name,
        limit=1,
    )
    teams = response["teams"]
    if len(teams) == 0:
        raise NoItemsFoundError("teams")
    elif len(teams) > 1:
        raise MultipleItemsFoundError("teams", [short_version(team) for team in teams])
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
    from toolkits.teams.arcade_teams.tools.channel import list_all_channels  # Avoid circular import

    response = await list_all_channels(context, team_id)
    channels = response["channels"]
    if len(channels) == 0:
        raise NoItemsFoundError("channels")
    if len(channels) > 1:
        raise MultipleItemsFoundError("channels", channels)
    return channels[0]


async def find_unique_channel_by_name(context: ToolContext, team_id: str, name: str) -> dict:
    from toolkits.teams.arcade_teams.tools.channel import search_channels  # Avoid circular import

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


async def find_chat_by_users(
    context: ToolContext,
    user_ids: list[str] | None,
    user_names: list[str] | None,
) -> dict:
    user_ids = user_ids or []

    if user_names:
        users = await find_people_by_name(context, user_names)
        user_ids.extend([user["id"] for user in users])

    request_body = Chat(
        chat_type=ChatType.OneOnOne,
        members=[build_conversation_member(user_id) for user_id in user_ids],
    )
    client = get_client(context.get_auth_token_or_empty())
    response = await client.chats.post(request_body)
    return serialize_chat(response)


async def find_people_by_name(context: ToolContext, names: list[str]) -> list[dict]:
    from arcade_teams.tools.people import search_people  # Avoid circular import

    response = await search_people(
        context=context,
        keywords=names,
        match_type=PartialMatchType.PARTIAL_ANY,
    )

    people_by_display_name = {}
    people_by_first_name = {}
    people_by_last_name = {}

    for person in response["people"]:
        build_people_by_name(people_by_display_name, person, "display")
        build_people_by_name(people_by_first_name, person, "first")
        build_people_by_name(people_by_last_name, person, "last")

    names_pending = set(names)
    people_found = []

    for name in names:
        name_lower = name.casefold()
        if name_lower in people_by_display_name:
            person = get_person_match(people_found, people_by_display_name, name)
            names_pending.remove(name)
            people_found.append(person)

        elif name_lower in people_by_first_name:
            person = get_person_match(people_found, people_by_first_name, name)
            names_pending.remove(name)
            people_found.append(person)

        elif name_lower in people_by_last_name:
            person = get_person_match(people_found, people_by_last_name, name)
            names_pending.remove(name)
            people_found.append(person)

    return {
        "people": people_found,
        "not_found": list(names_pending),
    }


def get_person_match(people_found: list[dict], people_by_name: dict, name: str) -> list[dict]:
    name_lower = name.casefold()

    matches = people_by_name[name_lower]

    # In case multiple people match this name
    if len(matches) > 1:
        people_found = [short_person(person) for person in matches]
        raise MultipleItemsFoundError(
            item="people",
            available_options=people_found,
            search_term=name,
        )

    return matches[0]


def build_people_by_name(people_dict: dict, person: dict, name_key: str) -> dict:
    name = person["name"][name_key].casefold()
    if name not in people_dict:
        people_dict[name] = [person]
        return people_dict

    people_dict[name].append(person)


def generate_case_variants(keyword: str) -> list[str]:
    return [
        keyword,
        keyword.casefold(),
        keyword.upper(),
        keyword.title(),
        keyword.capitalize(),
    ]
