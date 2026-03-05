from typing import Annotated, TypedDict

import httpx
from arcade_mcp_server import Context, tool
from arcade_mcp_server.auth import Reddit
from arcade_mcp_server.metadata import (
    Behavior,
    Classification,
    Operation,
    ServiceDomain,
    ToolMetadata,
)

REDDIT_API_URL = "https://oauth.reddit.com"


class RedditUserProfile(TypedDict, total=True):
    username: str
    comment_karma: int | None
    link_karma: int | None


@tool(
    requires_auth=Reddit(scopes=["identity"]),
    metadata=ToolMetadata(
        classification=Classification(
            service_domains=[ServiceDomain.SOCIAL_MEDIA],
        ),
        behavior=Behavior(
            operations=[Operation.READ],
            read_only=True,
            destructive=False,
            idempotent=True,
            open_world=True,
        ),
    ),
)
async def get_my_reddit_profile(
    context: Context,
    include_karma: Annotated[
        bool, "Whether to include karma breakdown in the response"
    ] = True,
) -> Annotated[RedditUserProfile, "The authenticated user's Reddit profile"]:
    """Get the Reddit profile of the authenticated user."""

    token = context.get_auth_token_or_empty()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{REDDIT_API_URL}/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data = response.json()

    profile = RedditUserProfile(
        username=data["name"],
        comment_karma=data.get("comment_karma", None) if include_karma else None,
        link_karma=data.get("link_karma", None) if include_karma else None,
    )

    return profile
