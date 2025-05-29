from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Reddit

from arcade_reddit.client import RedditClient
from arcade_reddit.utils import (
    create_fullname_for_comment,
    create_fullname_for_post,
    normalize_subreddit_name,
    parse_api_comment_response,
    remove_none_values,
)


@tool(requires_auth=Reddit(scopes=["submit"]))
async def submit_text_post(
    context: ToolContext,
    subreddit: Annotated[str, "The name of the subreddit to which the post will be submitted"],
    title: Annotated[str, "The title of the submission"],
    body: Annotated[
        str | None,
        "The body of the post in markdown format. Should never be the same as the title",
    ] = None,
    nsfw: Annotated[
        bool | None,
        "Indicates if the submission has content that is 'Not Safe For Work' (NSFW). "
        "Default is False",
    ] = False,
    spoiler: Annotated[
        bool | None,
        "Indicates if the post is marked as a spoiler. Default is False",
    ] = False,
    send_replies: Annotated[
        bool | None, "If true, sends replies to the user's inbox. Default is True"
    ] = True,
) -> Annotated[dict, "Response from Reddit after submission"]:
    """Submit a text-based post to a subreddit"""

    client = RedditClient(context.get_auth_token_or_empty())

    subreddit = normalize_subreddit_name(subreddit)

    params = {
        "api_type": "json",
        "sr": subreddit,
        "title": title,
        "kind": "self",
        "nsfw": nsfw,
        "spoiler": spoiler,
        "sendreplies": send_replies,
        "text": body,
    }
    params = remove_none_values(params)

    data = await client.post("api/submit", data=params)
    return {"data": data["json"].get("data", {}), "errors": data["json"].get("errors", [])}


@tool(requires_auth=Reddit(scopes=["submit"]))
async def comment_on_post(
    context: ToolContext,
    post_identifier: Annotated[
        str,
        "The identifier of the Reddit post. "
        "The identifier may be a reddit URL, a permalink, a fullname, or a post id.",
    ],
    text: Annotated[str, "The body of the comment in markdown format"],
) -> Annotated[dict, "Response from Reddit after submission"]:
    """Comment on a Reddit post"""

    client = RedditClient(context.get_auth_token_or_empty())

    fullname = create_fullname_for_post(post_identifier)

    params = {
        "api_type": "json",
        "thing_id": fullname,
        "text": text,
        "return_rtjson": True,
    }

    data = await client.post("api/comment", data=params)

    return parse_api_comment_response(data)


@tool(requires_auth=Reddit(scopes=["submit"]))
async def reply_to_comment(
    context: ToolContext,
    comment_identifier: Annotated[
        str,
        "The identifier of the Reddit comment to reply to. "
        "The identifier may be a comment ID, a reddit URL to the comment, "
        "a permalink to the comment, or the fullname of the comment.",
    ],
    text: Annotated[str, "The body of the reply in markdown format"],
) -> Annotated[dict, "Response from Reddit after submission"]:
    """Reply to a Reddit comment"""

    client = RedditClient(context.get_auth_token_or_empty())

    fullname = create_fullname_for_comment(comment_identifier)

    params = {
        "api_type": "json",
        "thing_id": fullname,
        "text": text,
        "return_rtjson": True,
    }

    data = await client.post("api/comment", data=params)
    return parse_api_comment_response(data)
