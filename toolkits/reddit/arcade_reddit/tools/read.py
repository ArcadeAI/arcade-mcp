from typing import Annotated, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Reddit

from arcade_reddit.client import RedditClient
from arcade_reddit.enums import (
    RedditTimeFilter,
    SubredditListingType,
)
from arcade_reddit.utils import (
    parse_get_content_of_post_response,
    parse_get_posts_in_subreddit_response,
    parse_get_top_level_comments_response,
    remove_none_values,
)


@tool(requires_auth=Reddit(scopes=["read"]))
async def get_posts_in_subreddit(
    context: ToolContext,
    subreddit: Annotated[str, "The name of the subreddit to fetch posts from"],
    listing: Annotated[
        SubredditListingType,
        (
            "The type of listing to fetch. For simple listings such as 'hot', 'new', or 'rising', "
            "the 'time_range' parameter is ignored. For time-based listings such as "
            "'top' or 'controversial', the 'time_range' parameter is required."
        ),
    ] = SubredditListingType.HOT,
    limit: Annotated[int, "The maximum number of posts to fetch. Default is 10, max is 100."] = 10,
    cursor: Annotated[Optional[str], "The pagination token from a previous call"] = None,
    time_range: Annotated[
        RedditTimeFilter,
        "The time range for filtering posts. Must be provided if the listing type is "
        f"{SubredditListingType.TOP.value} or {SubredditListingType.CONTROVERSIAL.value}. "
        f"Otherwise, it is ignored. Defaults to {RedditTimeFilter.TODAY.value}.",
    ] = RedditTimeFilter.TODAY,
) -> Annotated[dict, "A dictionary with a cursor for the next page and a list of posts"]:
    """Get posts in the specified subreddit

    The time_range is required if the listing type is 'top' or 'controversial'.
    """
    client = RedditClient(context.get_auth_token_or_empty())

    params = {"limit": limit, "after": cursor}
    if listing.is_time_based():
        params["t"] = time_range.to_api_value()

    params = remove_none_values(params)
    data = await client.get(f"r/{subreddit}/{listing.value}", params=params)
    result = parse_get_posts_in_subreddit_response(data)

    return result


@tool(requires_auth=Reddit(scopes=["read"]))
async def get_content_of_post(
    context: ToolContext, permalink: Annotated[str, "The permalink of the Reddit post"]
) -> Annotated[dict, "The content (body) of the Reddit post"]:
    """Get the content (body) of a Reddit post by its permalink."""
    client = RedditClient(context.get_auth_token_or_empty())

    data = await client.get(f"{permalink}.json")
    result = parse_get_content_of_post_response(data)

    return result


@tool(requires_auth=Reddit(scopes=["read"]))
async def get_top_level_comments(
    context: ToolContext,
    permalink: Annotated[str, "The permalink of the Reddit post to fetch comments from"],
) -> Annotated[dict, "A dictionary with a list of top level comments"]:
    """Get the first page of top-level comments of a Reddit post."""
    client = RedditClient(context.get_auth_token_or_empty())

    data = await client.get(f"{permalink}.json")
    result = parse_get_top_level_comments_response(data)

    return result
