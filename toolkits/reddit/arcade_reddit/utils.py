import re
from urllib.parse import urlparse

from arcade.sdk.errors import ToolExecutionError

from arcade_reddit.enums import RedditThingType


def remove_none_values(data: dict) -> dict:
    """Remove all keys with None values from a dictionary"""
    return {k: v for k, v in data.items() if v is not None}


def parse_get_posts_in_subreddit_response(data: dict) -> dict:
    """Parse the response from the Reddit API for getting posts in a subreddit

    Associated Reddit API endpoints:
    https://www.reddit.com/dev/api/#GET_hot
    https://www.reddit.com/dev/api/#GET_new
    https://www.reddit.com/dev/api/#GET_rising
    https://www.reddit.com/dev/api/#GET_{sort}

    Args:
        data: The response from the Reddit API deserialized as a dictionary

    Returns:
        A dictionary with a cursor for the next page and a list of posts
    """
    posts = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        post = {
            "id": d.get("id"),
            "name": d.get("name"),
            "title": d.get("title"),
            "author": d.get("author"),
            "subreddit": d.get("subreddit"),
            "created_utc": d.get("created_utc"),
            "num_comments": d.get("num_comments"),
            "score": d.get("score"),
            "upvote_ratio": d.get("upvote_ratio"),
            "upvotes": d.get("ups"),
            "permalink": d.get("permalink"),
            "url": d.get("url"),
            "is_video": d.get("is_video"),
        }
        posts.append(post)
    result = {"cursor": data.get("data", {}).get("after"), "posts": posts}
    return result


def parse_get_content_of_post_response(data: list) -> dict:
    """Parse the json representation of a Reddit post to get the content of a post

    Args:
        data: The json representation of a Reddit post
        (retrieved by appending .json to the permalink)

    Returns:
        A dictionary with the content of the post
    """
    if not data or not isinstance(data, list) or len(data) == 0:
        return {}

    try:
        post_data = data[0].get("data", {}).get("children", [{}])[0].get("data", {})
        return {
            "title": post_data.get("title"),
            "body": post_data.get("selftext"),
            "author": post_data.get("author"),
            "url": post_data.get("url"),
            "permalink": post_data.get("permalink"),
            "id": post_data.get("id"),
            "name": post_data.get("name"),
        }
    except (IndexError, AttributeError, KeyError):
        return {}


def parse_get_top_level_comments_response(data: list) -> dict:
    """Parse the json representation of a Reddit post to get the top-level comments

    Args:
        data: The json representation of a Reddit post

    Returns:
        A dictionary with a list of top-level comments
    """
    try:
        comments_listing = data[1]["data"]["children"]
    except (IndexError, KeyError):
        return {"comments": [], "num_comments": 0}

    comments = []
    for comment in comments_listing:
        if comment.get("kind") != RedditThingType.COMMENT.value:
            continue
        comment_data = comment.get("data", {})
        comments.append({
            "id": comment_data.get("id"),
            "author": comment_data.get("author"),
            "body": comment_data.get("body"),
            "score": comment_data.get("score"),
            "created_utc": comment_data.get("created_utc"),
        })

    return {"comments": comments, "num_comments": len(comments)}


def parse_api_comment_response(data: dict) -> dict:
    """Parse the response from the Reddit API's /api/comment endpoint

    Args:
        data: The response from the Reddit API deserialized as a dictionary

    Returns:
        A dictionary with the comment data
    """
    result = {
        "created_utc": data.get("created_utc"),
        "name": data.get("name"),
        "parent_id": data.get("parent_id"),
        "permalink": data.get("permalink"),
        "subreddit": data.get("subreddit"),
        "subreddit_id": data.get("subreddit_id"),
        "subreddit_name_prefixed": data.get("subreddit_name_prefixed"),
    }

    return result


def _extract_id_from_url(identifier: str, regex: str, error_msg: str) -> str:
    """
    Extract an ID from a Reddit URL using the provided regular expression.

    Args:
        identifier: The URL string from which to extract the ID.
        regex: The regular expression pattern containing a capturing group for the ID.
        error_msg: The error message to use if no ID can be extracted.

    Returns:
        The extracted ID as a string.

    Raises:
        ToolExecutionError: If the URL is not a Reddit URL or the pattern does not match.
    """
    parsed = urlparse(identifier)
    if not parsed.netloc.endswith("reddit.com"):
        raise ToolExecutionError(
            message=f"Expected a reddit URL, but got: {identifier}",
            developer_message="The identifier should be a valid Reddit URL.",
        )
    match = re.search(regex, parsed.path)
    if not match:
        raise ToolExecutionError(
            message=f"Could not extract id from URL: {identifier}",
            developer_message=error_msg,
        )
    return match.group(1)


def _extract_id_from_permalink(identifier: str, regex: str, error_msg: str) -> str:
    """
    Extract an ID from a Reddit permalink using the provided regular expression.

    Args:
        identifier: The permalink string from which to extract the ID.
        regex: The regular expression pattern containing a capturing group for the ID.
        error_msg: The error message to use if no ID can be extracted.

    Returns:
        The extracted ID as a string.

    Raises:
        ToolExecutionError: If the pattern does not match the permalink.
    """
    match = re.search(regex, identifier)
    if not match:
        raise ToolExecutionError(
            message=f"Could not extract id from permalink: {identifier}",
            developer_message=error_msg,
        )
    return match.group(1)


def _get_post_id(identifier: str) -> str:
    """
    Retrieve the post ID from various types of Reddit post identifiers.

    The identifier can be a Reddit URL to the post, a permalink for the post,
    a fullname for the post (starting with 't3_'), or a raw post ID.

    Args:
        identifier: The Reddit post identifier.

    Returns:
        The post ID as a string.

    Raises:
        ToolExecutionError: If the identifier does not contain a valid post ID.
    """
    if identifier.startswith("http://") or identifier.startswith("https://"):
        return _extract_id_from_url(
            identifier,
            r"/comments/([A-Za-z0-9]+)",
            "The reddit URL does not contain a valid post id.",
        )
    elif identifier.startswith("/r/"):
        return _extract_id_from_permalink(
            identifier,
            r"/comments/([A-Za-z0-9]+)",
            "The permalink does not contain a valid post id.",
        )
    else:
        pattern = re.compile(r"^(t3_)?([A-Za-z0-9]+)$")
        match = pattern.match(identifier)
        if match:
            return match.group(2)
    raise ToolExecutionError(
        message=f"Invalid identifier: {identifier}",
        developer_message=(
            "The identifier should be a valid Reddit URL, permalink, fullname, or post id."
        ),
    )


def _get_comment_id(identifier: str) -> str:
    """
    Retrieve the comment ID from various types of Reddit comment identifiers.

    The identifier can be a Reddit URL to the comment, a permalink for the comment,
    a fullname for the comment (starting with 't1_'), or a raw comment ID.

    Args:
        identifier: The Reddit comment identifier.

    Returns:
        The comment ID as a string.

    Raises:
        ToolExecutionError: If the identifier does not contain a valid comment ID.
    """
    if identifier.startswith("http://") or identifier.startswith("https://"):
        return _extract_id_from_url(
            identifier,
            r"/comment/([A-Za-z0-9]+)",
            "The reddit URL does not contain a valid comment id.",
        )
    elif identifier.startswith("/r/"):
        return _extract_id_from_permalink(
            identifier,
            r"/comment/([A-Za-z0-9]+)",
            "The permalink does not contain a valid comment id.",
        )
    else:
        if identifier.startswith("t1_"):
            return identifier[3:]
        if re.fullmatch(r"[A-Za-z0-9]+", identifier):
            return identifier
    raise ToolExecutionError(
        message=f"Invalid identifier: {identifier}",
        developer_message=(
            "The identifier should be a valid Reddit URL, permalink, fullname, or comment id."
        ),
    )


def create_path_for_post(identifier: str) -> str:
    """
    Create a path for a Reddit post.

    Args:
        identifier: The identifier of the post. The identifier may be a reddit URL,
        a permalink for the post, a fullname for the post, or a post id.

    Returns:
        The path for the post.
    """
    if identifier.startswith("http://") or identifier.startswith("https://"):
        parsed = urlparse(identifier)
        if not parsed.netloc.endswith("reddit.com"):
            raise ToolExecutionError(
                message=f"Expected a reddit URL, but got: {identifier}",
                developer_message="The identifier should be a valid Reddit URL.",
            )
        return parsed.path
    if identifier.startswith("/r/"):
        return identifier
    post_id = _get_post_id(identifier)
    return f"/comments/{post_id}"


def create_fullname_for_post(identifier: str) -> str:
    """
    Create a fullname for a Reddit post.

    Args:
        identifier: The identifier of the post. The identifier may be a reddit URL,
        a permalink for the post, a fullname for the post, or a post id.

    Returns:
        The fullname for the post.
    """
    if identifier.startswith("t3_"):
        return identifier
    post_id = _get_post_id(identifier)
    return f"t3_{post_id}"


def create_fullname_for_comment(identifier: str) -> str:
    """
    Create a fullname for a Reddit comment.

    Args:
        identifier: The identifier of the comment. The identifier may be a
        reddit URL to the comment, a permalink for the comment, a fullname for
        the comment, or a comment id.

    Returns:
        The fullname for the comment.
    """
    if identifier.startswith("t1_"):
        return identifier
    comment_id = _get_comment_id(identifier)
    return f"t1_{comment_id}"
