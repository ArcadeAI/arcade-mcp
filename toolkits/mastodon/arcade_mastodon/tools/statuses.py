from typing import Annotated

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_mastodon.tools.users import lookup_single_user_by_username
from arcade_mastodon.utils import get_headers, get_url, parse_status, parse_statuses


@tool(
    requires_auth=OAuth2(
        id="mastodon",
        scopes=["write:statuses"],
    ),
    requires_secrets=["MASTODON_SERVER_URL"],
)
async def post_status(
    context: ToolContext,
    status: Annotated[str, "The status to post"],
) -> Annotated[dict, "The status object from Mastodon"]:
    """
    Post a status to Mastodon.
    """

    async with httpx.AsyncClient() as client_http:
        response = await client_http.post(
            get_url(context=context, endpoint="statuses"),
            headers=get_headers(context),
            json={"status": status},
        )
        response.raise_for_status()
        return parse_status(response.json())


@tool(
    requires_auth=OAuth2(
        id="mastodon",
        scopes=["write:statuses"],
    ),
    requires_secrets=["MASTODON_SERVER_URL"],
)
async def delete_status_by_id(
    context: ToolContext,
    status_id: Annotated[str, "The ID of the status to delete"],
) -> Annotated[dict, "The status object from Mastodon that was deleted"]:
    """
    Delete a Mastodon status by its ID.
    """

    async with httpx.AsyncClient() as client_http:
        response = await client_http.delete(
            get_url(context=context, endpoint=f"statuses/{status_id}"),
            headers=get_headers(context),
        )
        response.raise_for_status()
        return parse_status(response.json())


@tool(
    requires_auth=OAuth2(
        id="mastodon",
        scopes=["read:statuses"],
    ),
    requires_secrets=["MASTODON_SERVER_URL"],
)
async def lookup_status_by_id(
    context: ToolContext,
    status_id: Annotated[str, "The ID of the status to lookup"],
) -> Annotated[dict, "The status object from Mastodon"]:
    """
    Lookup a Mastodon status by its ID.
    """

    async with httpx.AsyncClient() as client_http:
        response = await client_http.get(
            get_url(context=context, endpoint=f"statuses/{status_id}"),
            headers=get_headers(context),
        )
        response.raise_for_status()
        return parse_status(response.json())


@tool(
    requires_auth=OAuth2(
        id="mastodon",
        scopes=["read:statuses", "read:accounts"],
    ),
    requires_secrets=["MASTODON_SERVER_URL"],
)
async def search_recent_statuses_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the Mastodon account to look up."],
    limit: Annotated[
        int, "The maximum number of statuses to return. Default is 20, maximum is 40."
    ] = 20,
) -> Annotated[dict, "The statuses from Mastodon"]:
    """
    Search for recent statuses by a username.
    """

    account_info = await lookup_single_user_by_username(context, username)
    if not account_info["account"]:
        raise ToolExecutionError(
            message=f"Account {username} not found.",
            developer_message=f"Account {username} not found while searching for recent statuses.",
        )

    account_id = account_info["account"]["id"]

    limit = max(1, min(limit, 40))

    async with httpx.AsyncClient() as client_http:
        response = await client_http.get(
            get_url(context=context, endpoint=f"accounts/{account_id}/statuses"),
            headers=get_headers(context),
            params={"limit": limit},
        )
        response.raise_for_status()
        return {"statuses": parse_statuses(response.json())}


@tool(
    requires_auth=OAuth2(
        id="mastodon",
        scopes=["read:statuses", "read:accounts"],
    ),
    requires_secrets=["MASTODON_SERVER_URL"],
)
async def search_recent_statuses_by_keywords(
    context: ToolContext,
    keywords: Annotated[list[str] | None, "The keywords to search for."] = None,
    phrases: Annotated[list[str] | None, "The phrases to search for."] = None,
    limit: Annotated[
        int, "The maximum number of statuses to return. Default is 20, maximum is 40."
    ] = 20,
) -> Annotated[dict, "The statuses from Mastodon"]:
    """
    Search for recent statuses by keywords and phrases.
    """

    if not any([keywords, phrases]):
        raise RetryableToolError(
            message="At least one keyword or one phrase must be provided to this tool.",
            developer_message="The LLM did not provide any keywords or phrases to"
            " search for recent statuses.",
            additional_prompt_content="Please provide at least one keyword or one phrase"
            " to search for recent statuses.",
            retry_after_ms=500,
        )

    query = "".join(f'"{phrase}"' for phrase in phrases or [])
    if keywords:
        query += " ".join(f"{keyword}" for keyword in keywords)

    limit = max(1, min(limit, 40))

    async with httpx.AsyncClient() as client_http:
        response = await client_http.get(
            get_url(
                context=context,
                endpoint="search",
                api_version="v2",
            ),
            headers=get_headers(context),
            params={
                "q": query,
                "limit": limit,
            },
        )
        response.raise_for_status()
    return {"statuses": parse_statuses(response.json())}
