from typing import Annotated, Optional, cast

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Reddit

from arcade_reddit.client import RedditClient


@tool(requires_auth=Reddit(scopes=["submit"]))
async def submit_text_post(
    context: ToolContext,
    subreddit: Annotated[str, "The name of the subreddit to which the post will be submitted"],
    title: Annotated[str, "The title of the submission"],
    text: Annotated[str, "The body of the post in markdown format"],
    nsfw: Annotated[Optional[bool], "Indicates if the submission is NSFW"] = False,
    spoiler: Annotated[Optional[bool], "Indicates if the post is marked as a spoiler"] = False,
    sendreplies: Annotated[Optional[bool], "If true, sends replies to the user's inbox"] = True,
) -> Annotated[dict, "Response from Reddit after submission"]:
    """Submit a text-based post to a subreddit"""

    client = RedditClient(context.get_auth_token_or_empty())

    params = {
        "api_type": "json",
        "sr": subreddit,
        "title": title,
        "kind": "self",
        "nsfw": nsfw,
        "spoiler": spoiler,
        "sendreplies": sendreplies,
        "text": text,
    }

    data = await client.post("api/submit", data=params)
    return cast(dict, data)


@tool(requires_auth=Reddit(scopes=["submit"]))
async def comment_on_post(
    context: ToolContext,
    post_id: Annotated[str, "The id of the Reddit post to comment on"],
    text: Annotated[str, "The body of the comment in markdown format"],
) -> Annotated[dict, "Response from Reddit after submission"]:
    """Comment on a Reddit post"""

    client = RedditClient(context.get_auth_token_or_empty())

    # TODO: Validate it is a LINK type (post).
    #       Probably should have some helper like is_valid_post_id
    fullname = post_id if post_id.startswith("t3_") else f"t3_{post_id}"

    params = {
        "api_type": "json",
        "thing_id": fullname,
        "text": text,
        "return_rtjson": True,
    }

    data = await client.post("api/comment", data=params)
    return cast(dict, data)
