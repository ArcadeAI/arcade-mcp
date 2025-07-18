import asyncio
import datetime
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from arcade_tdk import ToolContext
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.chats.chats_request_builder import ChatsRequestBuilder
from msgraph.generated.chats.item.messages.messages_request_builder import MessagesRequestBuilder
from msgraph.generated.models.aad_user_conversation_member import AadUserConversationMember
from msgraph.generated.models.channel import Channel
from msgraph.generated.models.chat import Chat
from msgraph.generated.models.chat_type import ChatType
from msgraph.generated.models.user import User
from msgraph.generated.teams.item.all_channels.all_channels_request_builder import (
    AllChannelsRequestBuilder,
)
from msgraph.generated.teams.item.members.members_request_builder import (
    MembersRequestBuilder,
)
from msgraph.generated.teams.teams_request_builder import TeamsRequestBuilder
from msgraph.generated.users.item.people.people_request_builder import PeopleRequestBuilder
from msgraph.generated.users.users_request_builder import UsersRequestBuilder
from pydantic import BaseModel

from arcade_teams.client import get_client
from arcade_teams.concurency import paginate
from arcade_teams.constants import (
    ENV_VARS,
    MatchType,
    PartialMatchType,
)
from arcade_teams.exceptions import MultipleItemsFoundError, NoItemsFoundError
from arcade_teams.models import (
    FindChatByMembersSentinel,
    MatchHumansByName,
)
from arcade_teams.serializers import serialize_chat, short_version


def remove_none_values(kwargs: dict) -> dict:
    return {key: val for key, val in kwargs.items() if val is not None}


def load_config_param(context: ToolContext, key: str) -> Any:
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
        raise ToolExecutionError(message=err_msg, developer_message=err_msg)
    return start, end


def is_id(value: str) -> bool:
    return is_teams_id(value) or is_guid(value) or is_channel_id(value)


def is_teams_id(value: str) -> bool:
    return bool(re.match(r"^19:[\w\d]+@thread\.v2$", value))


def is_channel_id(value: str) -> bool:
    return bool(re.match(r"^19:[\w\d]+@[\w\d.]+$", value))


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
    kwargs = remove_none_values(kwargs)
    if "next_page_token" in kwargs:
        kwargs["skiptoken"] = kwargs.pop("next_page_token")
    query_params = request_builder(**kwargs)
    return RequestConfiguration(query_parameters=query_params)


def teams_request(top: int, filter_: str | None, skiptoken: str | None) -> RequestConfiguration:
    return config_request(
        TeamsRequestBuilder.TeamsRequestBuilderGetQueryParameters,
        top=top,
        filter=filter_,
        skiptoken=skiptoken,
    )


def channels_request(select: list[str] | None) -> RequestConfiguration:
    return config_request(
        AllChannelsRequestBuilder.AllChannelsRequestBuilderGetQueryParameters,
        select=select,
    )


def members_request(top: int, filter_: str | None) -> RequestConfiguration:
    return config_request(
        MembersRequestBuilder.MembersRequestBuilderGetQueryParameters, top=top, filter=filter_
    )


def messages_request(**kwargs) -> RequestConfiguration:
    kwargs = remove_none_values(kwargs)
    return config_request(MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters, **kwargs)


def people_request(
    top: int,
    next_page_token: str | None,
    search: str | None,
) -> RequestConfiguration:
    return config_request(
        PeopleRequestBuilder.PeopleRequestBuilderGetQueryParameters,
        top=top,
        next_page_token=next_page_token,
        search=search,
    )


def users_request(**kwargs) -> RequestConfiguration:
    return config_request(UsersRequestBuilder.UsersRequestBuilderGetQueryParameters, **kwargs)


def chats_request(
    top: int,
    next_page_token: str | None,
    expand: list[str] | None,
) -> RequestConfiguration:
    kwargs = {
        "top": top,
        "next_page_token": next_page_token,
        "expand": expand,
    }
    return config_request(ChatsRequestBuilder.ChatsRequestBuilderGetQueryParameters, **kwargs)


def create_chat_request(members: list[AadUserConversationMember]) -> Chat:
    return Chat(
        chat_type=ChatType.OneOnOne if len(members) == 2 else ChatType.Group,
        members=members,
    )


def build_conversation_member(
    user_id: str, roles: list[str] | None = None
) -> AadUserConversationMember:
    roles = roles or ["owner"]
    return AadUserConversationMember(
        odata_type="#microsoft.graph.aadUserConversationMember",
        roles=roles,
        additional_data={"user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_id}')"},
    )


def build_token_pagination(response: BaseModel) -> dict:
    pagination = {"is_last_page": True}
    if response.odata_next_link:
        pagination["is_last_page"] = False
        pagination["next_page_token"] = response.odata_next_link
    return pagination


def build_offset_pagination(
    items: list, limit: int, offset: int, more_results: bool | None = None
) -> dict:
    if isinstance(more_results, bool):
        is_last_page = not more_results
    else:
        is_last_page = len(items) < limit or offset + limit >= 999

    pagination = {
        "is_last_page": is_last_page,
        "limit": limit,
        "current_offset": offset,
    }
    if not is_last_page:
        pagination["next_offset"] = offset + len(items)
    return pagination


def build_people_search_clause(
    keywords: list[str],
    match_type: PartialMatchType,
) -> str:
    operator = match_type.to_filter_condition().value
    return f" {operator} ".join([f'"{keyword}"' for keyword in keywords])


def build_users_search_clause(
    keywords: list[str],
    match_type: PartialMatchType,
) -> str:
    operator = match_type.to_filter_condition().value
    return f" {operator} ".join([f'"displayName:{keyword}"' for keyword in keywords])


def build_filter_clause(
    field: str,
    keywords: str,
    match_type: MatchType,
) -> str:
    if match_type == MatchType.EXACT:
        return f"{field} eq '{keywords.casefold()}'"
    words = keywords.casefold().split()
    condition = f" {match_type.to_filter_condition().value} "
    return condition.join(f"startswith({field}, '{word.strip()}')" for word in words)


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


async def resolve_channel_id(
    context: ToolContext,
    team_id: str,
    channel_id_or_name: str | None,
) -> str:
    if not channel_id_or_name:
        channel = await find_unique_channel(context, team_id)
        return channel["id"]

    if is_channel_id(channel_id_or_name):
        return channel_id_or_name

    channel = await find_unique_channel_by_name(context, team_id, channel_id_or_name)
    return channel["id"]


async def find_unique_channel(context: ToolContext, team_id: str) -> dict:
    from toolkits.teams.arcade_teams.tools.channel import list_channels  # Avoid circular import

    response = await list_channels(context, team_id)
    channels = response["channels"]
    if len(channels) == 0:
        raise NoItemsFoundError("channels")
    if len(channels) > 1:
        raise MultipleItemsFoundError("channels", channels)
    return channels[0]


async def find_unique_channel_by_name(context: ToolContext, team_id: str, name: str) -> dict:
    from arcade_teams.tools.channel import search_channels  # Avoid circular import

    response = await search_channels(
        context=context,
        team_id_or_name=team_id,
        keywords=[name],
        match_type=MatchType.PARTIAL_ANY,
    )
    channels = response["channels"]

    if len(channels) == 1:
        return channels[0]

    if len(channels) == 0:
        raise NoItemsFoundError(
            item="channels",
            available_options=channels,
            search_term=name,
        )

    if len(channels) > 1:
        for channel in channels:
            if channel["name"].casefold() == name.casefold():
                return channel
        raise MultipleItemsFoundError(
            item="channels",
            available_options=channels,
            search_term=name,
        )


async def find_chat_by_users(
    context: ToolContext,
    user_ids: list[str] | None,
    user_names: list[str] | None,
    semaphore: asyncio.Semaphore | None = None,
) -> dict:
    if not user_ids and not user_names:
        error = (
            "The user_ids and user_names arguments are empty. "
            "Provide at least one of user_ids or user_names or a combination of both."
        )
        raise ToolExecutionError(message=error, developer_message=error)

    if not user_names:
        return await find_chat_by_user_ids(context, user_ids, semaphore)

    return await find_chat_by_user_ids_and_names(context, user_ids or [], user_names, semaphore)


async def find_chat_by_user_ids(
    context: ToolContext,
    user_ids: list[str],
    semaphore: asyncio.Semaphore | None = None,
) -> dict:
    """Find a chat by its members' IDs.

    If we only have user_ids, we can simply create the chat. If it already exists, the MS Graph API
    will return the existing chat. This is the most efficient way.
    """
    from arcade_teams.tools.users import get_signed_in_user  # Avoid circular import

    client = get_client(context.get_auth_token_or_empty())
    semaphore = semaphore or asyncio.Semaphore(load_config_param(context, "TEAMS_MAX_CONCURRENCY"))

    async with semaphore:
        current_user = await get_signed_in_user(context)
        if current_user["id"] not in user_ids:
            user_ids.append(current_user["id"])

        request_body = Chat(
            chat_type=ChatType.OneOnOne if len(user_ids) == 2 else ChatType.Group,
            members=[build_conversation_member(user_id) for user_id in user_ids],
        )
        response = await client.chats.post(request_body)

        # The "chats.get" endpoint returns more data than the "chats.post" one. We call the
        # "chats.get" endpoint to keep responses standardized.
        chat = await client.chats.by_chat_id(response["id"]).get()
        return serialize_chat(chat)


async def find_chat_by_user_ids_and_names(
    context: ToolContext,
    user_ids: list[str],
    user_names: list[str],
    semaphore: asyncio.Semaphore | None = None,
) -> dict:
    """Find a chat by its members' IDs and names.

    To find a chat by its members' names, we need to retrieve chats and filter by their members.
    Searching for the users and getting their IDs would be more efficient, but the
    Users and People endpoints have limitations that prevent us from doing that in a reliable way:

    1) The Users endpoint will only return users in the current user's tenant. If the user is
    looking for a chat with users from other tenants (external orgs), we won't find them.

    2) The Users endpoint only returns up to 999 users. In large tenants, we might not be able to
    find the relevant users.

    3) The People endpoint only returns people the current user has interacted with before. If
    the chat has to be created with people that the current user has never interacted with
    before, this will not work.

    4) The People endpoint will return people like email and calendar contacts, which may not
    be relevant for the purposes of Teams chat membership and lead to false positives when we
    do a search by name.

    Even combining the two endpoints would still not be entirely reliable. This is why we do an
    inefficient scan of chats and filter by their members.
    """
    from arcade_teams.tools.users import get_signed_in_user  # Avoid circular import

    current_user = await get_signed_in_user(context)
    if current_user["id"] not in user_ids:
        user_ids.append(current_user["id"])

    find_chat_sentinel = FindChatByMembersSentinel(user_ids=user_ids, user_names=user_names)
    client = get_client(context.get_auth_token_or_empty())
    semaphore = semaphore or asyncio.Semaphore(load_config_param(context, "TEAMS_MAX_CONCURRENCY"))

    chats, _ = await paginate(
        context=context,
        func=client.me.chats.get,
        request_builder=chats_request,
        page_limit=50,
        semaphore=semaphore,
        sentinel=find_chat_sentinel,
        expand=["members", "lastMessagePreview"],
    )

    if len(find_chat_sentinel.exact_matches) == 1:
        return serialize_chat(find_chat_sentinel.exact_matches[0])

    elif len(find_chat_sentinel.exact_matches) > 1:
        raise MultipleItemsFoundError(
            "chats", [serialize_chat(chat) for chat in find_chat_sentinel.exact_matches]
        )

    elif len(find_chat_sentinel.partial_matches) == 1:
        return serialize_chat(find_chat_sentinel.partial_matches[0])

    elif len(find_chat_sentinel.partial_matches) > 1:
        raise MultipleItemsFoundError(
            "chats", [serialize_chat(chat) for chat in find_chat_sentinel.partial_matches]
        )

    raise NoItemsFoundError(
        item="chats",
        available_options=[serialize_chat(chat) for chat in chats],
    )


async def find_humans_by_name(
    context: ToolContext,
    names: list[str],
    semaphore: asyncio.Semaphore | None = None,
):
    if not names:
        message = "No names provided"
        raise ToolExecutionError(message=message, developer_message=message)

    semaphore = semaphore or asyncio.Semaphore(load_config_param(context, "TEAMS_MAX_CONCURRENCY"))
    names = deduplicate_names(names)

    # Avoid circular import
    from arcade_teams.serializers import serialize_person
    from arcade_teams.tools.users import search_users

    client = get_client(context.get_auth_token_or_empty())

    async with semaphore:
        users_response, people = await asyncio.gather(
            search_users(
                context=context,
                keywords=names,
                match_type=PartialMatchType.PARTIAL_ANY,
                limit=999,  # The MS Graph API does not support more than 999 users
            ),
            paginate(
                context=context,
                func=client.me.people.get,
                request_builder=people_request,
                page_limit=1000,
                semaphore=semaphore,
                search=build_people_search_clause(names, PartialMatchType.PARTIAL_ANY),
            ),
        )

    match_humans_by_name = MatchHumansByName(
        names=names,
        users=users_response["users"],
        people=[serialize_person(person) for person in people],
    )

    match_humans_by_name.run()

    return match_humans_by_name.get_unique_exact_matches()


def _matches_channel_name(channel_name: str, keywords: list[str], match_type: MatchType) -> bool:
    channel_name = channel_name.casefold()
    if match_type == MatchType.EXACT:
        return any(channel_name == keyword.casefold() for keyword in keywords)
    if match_type == MatchType.PARTIAL_ALL:
        return all(keyword.casefold() in channel_name for keyword in keywords)
    return any(keyword.casefold() in channel_name for keyword in keywords)


def filter_channels_by_name(
    channels: list[Channel],
    keywords: list[str],
    match_type: MatchType,
    serializer: Callable | None = None,
) -> list[Channel]:
    serializer = serializer or (lambda x: x)
    return [
        serializer(channel)
        for channel in channels
        if _matches_channel_name(channel.display_name, keywords, match_type)
    ]


def deduplicate_names(names: list[str]) -> list[str]:
    names_unique = []
    names_casefold = {name.casefold() for name in names}
    for name in names:
        name_lower = name.casefold()
        if name_lower in names_casefold:
            names_unique.append(name)
            names_casefold.remove(name_lower)
    return names_unique


def generate_case_variants(keyword: str) -> list[str]:
    return [
        keyword,
        keyword.casefold(),
        keyword.upper(),
        keyword.title(),
        keyword.capitalize(),
    ]


def match_user_by_name(user: User, keywords: list[str], match_type: MatchType) -> bool:
    user_name = user.display_name.casefold()
    if match_type == MatchType.EXACT:
        return any(keyword.casefold() == user_name for keyword in keywords)
    elif match_type == MatchType.PARTIAL_ALL:
        return all(keyword.casefold() in user_name for keyword in keywords)
    else:
        return any(keyword.casefold() in user_name for keyword in keywords)


def raise_for_humans_not_found(
    not_found: list[str],
    not_matched: list[dict],
) -> None:
    # Avoid circular import
    from arcade_teams.serializers import short_human
    from arcade_teams.tools.people import search_people
    from arcade_teams.tools.users import search_users

    max_items = 50
    message = f"Could not find the following users: {', '.join(not_found)}"
    available_humans = [short_human(human) for human in not_matched[0:max_items]]
    additional_prompt = f"Available users/people: {json.dumps(available_humans)}"
    if len(available_humans) > max_items:
        additional_prompt = (
            "Some of the available users/people are listed next. To retrieve more, use the "
            f"Teams.{search_users.__tool_name__} or Teams.{search_people.__tool_name__} tools. "
            f"{additional_prompt}"
        )
    raise RetryableToolError(
        message=message,
        developer_message=message,
        additional_prompt_content=additional_prompt,
    )
