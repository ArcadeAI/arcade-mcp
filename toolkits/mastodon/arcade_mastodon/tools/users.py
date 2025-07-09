from typing import Annotated

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2

from arcade_mastodon.utils import get_headers, get_url


@tool(
    requires_auth=OAuth2(
        id="mastodon",
        scopes=["read:accounts"],
    ),
    requires_secrets=["MASTODON_SERVER_URL"],
)
async def lookup_single_user_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the Mastodon account to look up."],
) -> Annotated[dict, "The account object from Mastodon"]:
    """
    Lookup a single Mastodon account by its username.
    """

    async with httpx.AsyncClient() as client_http:
        response = await client_http.get(
            get_url(context=context, endpoint=f"accounts/lookup?acct={username}"),
            headers=get_headers(context),
        )
        response.raise_for_status()
        return {"account": response.json()}
