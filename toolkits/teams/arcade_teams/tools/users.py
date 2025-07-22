from typing import Annotated, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft
from arcade_tdk.errors import ToolExecutionError
from msgraph.generated.models.user import User

# Microsoft Graph search requires the special request header "ConsistencyLevel: eventual"
# and the $count query parameter. We build these explicitly via RequestConfiguration.
from arcade_teams.client import get_client
from arcade_teams.constants import PartialMatchType
from arcade_teams.serializers import serialize_user
from arcade_teams.utils import build_offset_pagination, match_user_by_name, users_request


@tool(requires_auth=Microsoft(scopes=["User.Read"]))
async def get_signed_in_user(
    context: ToolContext,
) -> Annotated[dict, "The user currently signed in."]:
    """Get the user currently signed in Microsoft Teams.

    This tool is not necessary to call before calling other tools.
    """
    client = get_client(context.get_auth_token_or_empty())
    response = await client.me.get()
    return serialize_user(cast(User, response))


@tool(requires_auth=Microsoft(scopes=["User.Read"]))
async def list_users(
    context: ToolContext,
    limit: Annotated[
        int, "The maximum number of users to return. Defaults to 50, max is 100."
    ] = 50,
    offset: Annotated[int, "The offset to start from."] = 0,
) -> Annotated[dict, "The users in the tenant."]:
    """Lists the users in the Microsoft Teams tenant.

    The Microsoft Graph API returns only up to the first 999 users.
    """
    limit = min(100, max(1, limit)) + offset

    client = get_client(context.get_auth_token_or_empty())

    response = await client.users.get(users_request(top=limit))

    users = [
        serialize_user(user)
        for user in response.value[offset : offset + limit]  # type: ignore[index,union-attr]
    ]

    return {
        "users": users,
        "count": len(users),
        "pagination": {
            "is_last_page": len(users) < limit,
            "limit": limit,
            "current_offset": offset,
            "next_offset": offset + len(users),
        },
    }


# NOTE: the "list users" endpoint docs says it supports $search and $filter, but it's completely
# broken and simply don't work. The endpoint returns all users, regardless of keywords specified
# in the $search or $filter parameters. This is why we filter users dynamically in this tool.
@tool(requires_auth=Microsoft(scopes=["User.Read"]))
async def search_users(
    context: ToolContext,
    keywords: Annotated[list[str], "The keywords to match against users' names."],
    match_type: Annotated[
        PartialMatchType,
        "The type of match to use for the keywords. "
        f"Defaults to {PartialMatchType.PARTIAL_ANY.value}.",
    ] = PartialMatchType.PARTIAL_ANY,
    limit: Annotated[
        int, "The maximum number of users to return. Defaults to 50, max is 999."
    ] = 50,
    offset: Annotated[int, "The offset to start from."] = 0,
) -> Annotated[dict, "The users in the tenant."]:
    """Searches for users in the Microsoft Teams tenant.

    This tool only return users that are directly linked to the tenant the current signed in user
    is a member of. If you need to retrieve users that have interacted with the current user but
    are from external tenants/organizations, use `Teams.SearchPeople`, instead.

    The Microsoft Graph API returns only up to the first 999 users.
    """
    limit = min(999, max(1, limit))

    if limit + offset > 999:
        offset = 999 - limit

    if not keywords:
        error = "At least one keyword is required."
        raise ToolExecutionError(message=error, developer_message=error)

    client = get_client(context.get_auth_token_or_empty())

    response = await client.users.get(users_request(top=limit))

    users = [
        serialize_user(user)
        for user in response.value  # type: ignore[union-attr]
        if match_user_by_name(user, keywords, match_type)
    ][offset : offset + limit]

    return {
        "users": users,
        "count": len(users),
        "pagination": build_offset_pagination(users, limit, offset),
    }
