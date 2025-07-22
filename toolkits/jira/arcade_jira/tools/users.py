from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian
from arcade_tdk.errors import ToolExecutionError

from arcade_jira.client import JiraClient
from arcade_jira.exceptions import NotFoundError
from arcade_jira.utils import (
    add_pagination_to_response,
    clean_user_dict,
    remove_none_values,
    resolve_cloud_id,
)


@tool(requires_auth=Atlassian(scopes=["read:jira-user"]))
async def list_users(
    context: ToolContext,
    account_type: Annotated[
        str | None,
        "The account type of the users to return. Defaults to 'atlassian'. Provide `None` to  "
        "disable filtering by account type. The account type filter will be applied after "
        "retrieving users from Jira API, thus the tool may return less users than the limit and "
        "still have more users to paginate. Check the `pagination` key in the response dictionary.",
    ] = "atlassian",
    limit: Annotated[
        int,
        "The maximum number of users to return. Min of 1, max of 50. Defaults to 50.",
    ] = 50,
    offset: Annotated[
        int,
        "The number of users to skip before starting to return users. "
        "Defaults to 0 (start from the first user).",
    ] = 0,
    atlassian_cloud_id: Annotated[
        str | None,
        "The ID of the Atlassian Cloud to use (defaults to None). If not provided and the user has "
        "a single cloud authorized, the tool will use that. Otherwise, an error will be raised.",
    ] = None,
) -> Annotated[dict[str, Any], "The information about all users."]:
    """Browse users in Jira."""
    limit = max(min(limit, 50), 1)
    atlassian_cloud_id = await resolve_cloud_id(context, atlassian_cloud_id)
    client = JiraClient(context=context, cloud_id=atlassian_cloud_id)
    api_response = await client.get(
        "/users/search",
        params={
            "startAt": offset,
            "maxResults": limit,
        },
    )
    items = cast(list[dict[str, Any]], api_response)

    users = [
        clean_user_dict(user)
        for user in api_response
        if not account_type or user["accountType"].casefold() == account_type.casefold()
    ]
    response = add_pagination_to_response({"users": users}, items, limit, offset)
    response["pagination"]["total_results"] = len(users)
    return response


@tool(requires_auth=Atlassian(scopes=["read:jira-user"]))
async def get_user_by_id(
    context: ToolContext,
    user_id: Annotated[str, "The the user's ID."],
    atlassian_cloud_id: Annotated[
        str | None,
        "The ID of the Atlassian Cloud to use (defaults to None). If not provided and the user has "
        "a single cloud authorized, the tool will use that. Otherwise, an error will be raised.",
    ] = None,
) -> Annotated[dict[str, Any], "The user information."]:
    """Get user information by their ID."""
    atlassian_cloud_id = await resolve_cloud_id(context, atlassian_cloud_id)
    client = JiraClient(context=context, cloud_id=atlassian_cloud_id)

    not_found = {"error": "User not found"}

    try:
        response = await client.get("user", params={"accountId": user_id})
    except NotFoundError:
        return not_found

    if not response:
        return not_found

    return {"user": clean_user_dict(response)}


@tool(requires_auth=Atlassian(scopes=["read:jira-user"]))
async def get_users_without_id(
    context: ToolContext,
    name_or_email: Annotated[
        str,
        "The user's display name or email address to search for (case-insensitive). The string can "
        "match the prefix of the user's attribute. For example, a string of 'john' will match "
        "users with a display name or email address that starts with 'john', such as "
        "'John Doe', 'Johnson', 'john@example.com', etc.",
    ],
    enforce_exact_match: Annotated[
        bool,
        "Whether to enforce an exact match of the name_or_email against users' display name and "
        "email attributes. Defaults to False (return all users that match the prefix). If set to "
        "True, before returning results, the tool will filter users with a display name OR email "
        "address that match exactly the value of the `name_or_email` argument.",
    ] = False,
    limit: Annotated[
        int,
        "The maximum number of users to return. Min of 1, max of 50. Defaults to 50.",
    ] = 50,
    offset: Annotated[
        int,
        "The number of users to skip before starting to return users. "
        "Defaults to 0 (start from the first user).",
    ] = 0,
    atlassian_cloud_id: Annotated[
        str | None,
        "The ID of the Atlassian Cloud to use (defaults to None). If not provided and the user has "
        "a single cloud authorized, the tool will use that. Otherwise, an error will be raised.",
    ] = None,
) -> Annotated[dict[str, Any], "The information about users that match the search criteria."]:
    """Get users without their account ID, searching by display name and email address.

    The Jira user search API will return up to 1,000 (one thousand) users for any given name/email
    query. If you need to get more users, please use the `Jira.ListAllUsers` tool.
    """
    limit = max(min(limit, 1000), 1)

    if limit + offset > 1000:
        raise ToolExecutionError(
            message="The maximum number of users returned by the Jira search API is 1000. "
            f"To get more users use the `Jira.{list_users.__tool_name__}` tool."
        )

    if not name_or_email:
        raise ToolExecutionError(
            message="The `user_name_or_email` argument is required to search for users."
        )

    atlassian_cloud_id = await resolve_cloud_id(context, atlassian_cloud_id)
    client = JiraClient(context=context, cloud_id=atlassian_cloud_id)
    api_response = await client.get(
        "/user/search",
        params=remove_none_values({
            "query": name_or_email,
            "startAt": offset,
            "maxResults": limit,
        }),
    )

    users = [clean_user_dict(user) for user in api_response]

    if enforce_exact_match:
        users = [
            user
            for user in users
            if user["name"].casefold() == name_or_email.casefold()
            or user["email"].casefold() == name_or_email.casefold()
        ]

    response = {
        "users": users,
        "query": {
            "name_or_email": name_or_email,
            "enforce_exact_match": enforce_exact_match,
            "limit": limit,
            "offset": offset,
        },
    }
    return add_pagination_to_response(response, users, limit, offset, 1000)
