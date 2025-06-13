import re
from urllib.parse import urlparse

import httpx
from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError

from arcade_reddit.client import RedditClient
from arcade_reddit.enums import RedditThingType


def remove_none_values(data: dict) -> dict:
    """Remove all keys with None values from a dictionary"""
    return {k: v for k, v in data.items() if v is not None}


def normalize_subreddit_name(subreddit: str) -> str:
    """Normalize a subreddit name"""
    return subreddit.lower().replace("r/", "").replace(" ", "")


def _simplify_post_data(post_data: dict, include_body: bool = False) -> dict:
    simplified_data = {
        "id": post_data.get("id"),
        "name": post_data.get("name"),
        "title": post_data.get("title"),
        "author": post_data.get("author"),
        "subreddit": post_data.get("subreddit"),
        "created_utc": post_data.get("created_utc"),
        "num_comments": post_data.get("num_comments"),
        "score": post_data.get("score"),
        "upvote_ratio": post_data.get("upvote_ratio"),
        "upvotes": post_data.get("ups"),
        "permalink": post_data.get("permalink"),
        "url": post_data.get("url"),
        "is_video": post_data.get("is_video"),
    }
    if include_body:
        simplified_data["body"] = post_data.get("selftext")
    return simplified_data


def parse_get_posts_in_subreddit_response(data: dict) -> dict:
    """Parse the response from the Reddit API for getting posts in a subreddit

    Associated Reddit API endpoints:
    https://www.reddit.com/dev/api/#GET_hot
    https://www.reddit.com/dev/api/#GET_new
    https://www.reddit.com/dev/api/#GET_rising
    https://www.reddit.com/dev/api/#GET_{sort}

    Args:
        data: The response from the Reddit API deserialized as a dictionary.
              NOTE: The response doesn't contain the body of the posts.

    Returns:
        A dictionary with a cursor for the next page and a list of posts
    """
    posts = []
    for child in data.get("data", {}).get("children", []):
        post_data = child.get("data", {})
        post = _simplify_post_data(post_data)
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
        return _simplify_post_data(post_data, include_body=True)
    except (IndexError, AttributeError, KeyError):
        return {}


def parse_get_content_of_multiple_posts_response(data: dict) -> list[dict]:
    """Parse the json representation of multiple Reddit posts to get the content of each post

    Args:
        data: The json representation of multiple Reddit posts
              (retrieved from the /api/info.json endpoint)

    Returns:
        A dictionary with the simplified content of each post
    """
    if not data or not isinstance(data, dict) or len(data) == 0:
        return []

    result = []
    for post in data.get("data", {}).get("children", []):
        post_data = post.get("data", {})
        result.append(_simplify_post_data(post_data, include_body=True))

    return result


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


def create_fullname_for_multiple_posts(post_identifiers: list[str]) -> tuple[list[str], list[dict]]:
    """
    Create fullnames for multiple Reddit posts.

    Args:
        post_identifiers: A list of Reddit post identifiers. The identifiers may be
        reddit URLs, permalinks, fullnames, or post ids.

    Returns:
        (fullnames, warnings): A tuple of a list of fullnames for the posts and
        a list of warnings if any of the identifiers are invalid.
    """
    fullnames = []
    warnings = []
    for identifier in post_identifiers:
        try:
            fullnames.append(create_fullname_for_post(identifier))
        except ToolExecutionError:
            message = f"'{identifier}' is not a valid Reddit post identifier."
            warnings.append({"message": message, "identifier": identifier})

    return fullnames, warnings


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


async def resolve_subreddit_access(client: RedditClient, subreddit: str) -> dict:
    """Checks whether the specified subreddit exists and is accessible.
    Helps abstract the logic of checking subreddit access.

    Args:
        client: The Reddit client
        subreddit: The subreddit to check

    Returns:
        A dictionary that specifies whether the subreddit exists and
        whether it is accessible to the user.
    """
    normalized_name = normalize_subreddit_name(subreddit)
    try:
        await client.get(f"r/{normalized_name}/about.json")
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (404, 302):
            return {"exists": False, "accessible": False}
        elif e.response.status_code == 403:
            return {"exists": True, "accessible": False}
        raise
    return {"exists": True, "accessible": True}


def parse_subreddit_rules_response(data: dict) -> dict:
    """
    Parse the response data from the Reddit API for subreddit rules.

    Args:
        data (dict): The raw API response containing subreddit rules.

    Returns:
        dict: A dictionary with a 'rules' key containing a list of parsed rules.
    """
    rules = []
    for rule in data.get("rules", []):
        rules.append({
            "priority": rule.get("priority"),
            "title": rule.get("short_name"),
            "body": rule.get("description"),
        })
    return {"rules": rules}


async def parse_user_posts_response(
    context: ToolContext, posts_data: dict, include_body: bool
) -> dict:
    """Parse the response from the Reddit API for user posts

    Args:
        context: The tool context
        posts_data: The response from the Reddit API for getting the authenticated user's posts
        include_body: Whether to include the body of the posts in the parsed response

    Returns:
        A dictionary with a cursor for the next page (if there is one) and a list of posts
    """
    next_cursor = posts_data.get("data", {}).get("after")
    parsed_response = {"cursor": next_cursor} if next_cursor else {}
    if not include_body:
        posts = []
        for child in posts_data.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            simplified = _simplify_post_data(post_data, include_body=False)
            posts.append(simplified)
        parsed_response["posts"] = posts
    else:
        post_ids = []
        for child in posts_data.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            identifier = post_data.get("name") or post_data.get("id")
            if identifier:
                post_ids.append(identifier)
        # Dynamically import get_content_of_multiple_posts to avoid circular dependency
        from arcade_reddit.tools.read import get_content_of_multiple_posts

        content_response = await get_content_of_multiple_posts(
            context=context, post_identifiers=post_ids
        )
        posts_with_body = content_response.get("posts", [])
        parsed_response["posts"] = posts_with_body

    return parsed_response
