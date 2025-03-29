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
