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
