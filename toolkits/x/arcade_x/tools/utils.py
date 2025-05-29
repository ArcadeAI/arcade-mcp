from typing import Any

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError


def get_tweet_url(tweet_id: str) -> str:
    """Get the URL of a tweet given its ID."""
    return f"https://x.com/x/status/{tweet_id}"


def get_headers_with_token(context: ToolContext) -> dict[str, str]:
    """Get the headers for a request to the X API."""
    if context.authorization is None or context.authorization.token is None:
        raise ToolExecutionError(
            "Missing Token. Authorization is required to post a tweet.",
            developer_message="Token is not set in the ToolContext.",
        )
    token = (
        context.authorization.token if context.authorization and context.authorization.token else ""
    )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def parse_search_recent_tweets_response(response_data: dict[str, Any]) -> dict[str, Any]:
    """
    Parses response from the X API search recent tweets endpoint.
    Returns the modified response data with added 'tweet_url', 'author_username', and 'author_name'.
    """
    if not sanity_check_tweets_data(response_data):
        return {"data": [], "next_token": ""}

    # Add 'tweet_url' to each tweet
    for tweet in response_data["data"]:
        tweet["tweet_url"] = get_tweet_url(tweet["id"])

    # Add 'author_username' and 'author_name' to each tweet
    for tweet_data, user_data in zip(
        response_data["data"], response_data["includes"]["users"], strict=False
    ):
        tweet_data["author_username"] = user_data["username"]
        tweet_data["author_name"] = user_data["name"]

    return response_data


def sanity_check_tweets_data(tweets_data: dict[str, Any]) -> bool:
    """
    Sanity check the tweets data.
    Returns True if the tweets data is valid and contains tweets, False otherwise.
    """
    if not tweets_data.get("data"):
        return False
    # prefer clarity over appeasing linter here
    if not tweets_data.get("includes", {}).get("users"):  # noqa: SIM103
        return False
    return True


def expand_long_tweet(tweet_data: dict[str, Any]) -> None:
    """Expand a long tweet.

    For tweets exceeding 280 characters,
    replace the truncated tweet text with the full tweet text.
    """
    if tweet_data.get("note_tweet"):
        tweet_data["text"] = tweet_data["note_tweet"]["text"]
        del tweet_data["note_tweet"]


def expand_urls_in_tweets(
    tweets_data: list[dict[str, Any]], delete_entities: bool = True
) -> list[dict[str, Any]]:
    """
    Returns a new list of tweets with expanded URLs.
    """
    new_tweets = []
    for tweet_data in tweets_data:
        new_tweet = tweet_data.copy()
        if "entities" in new_tweet and "urls" in new_tweet["entities"]:
            for url_entity in new_tweet["entities"]["urls"]:
                short_url = url_entity["url"]
                expanded_url = url_entity["expanded_url"]
                new_tweet["text"] = new_tweet["text"].replace(short_url, expanded_url)

        if delete_entities:
            new_tweet.pop("entities", None)
        new_tweets.append(new_tweet)
    return new_tweets


def expand_urls_in_user_description(user_data: dict, delete_entities: bool = True) -> dict:
    """
    Returns a new user data dict with expanded URLs in the description.
    """
    new_user_data = user_data.copy()
    description_urls = new_user_data.get("entities", {}).get("description", {}).get("urls", [])
    description = new_user_data.get("description", "")
    for url_info in description_urls:
        t_co_link = url_info["url"]
        expanded_url = url_info["expanded_url"]
        description = description.replace(t_co_link, expanded_url)
    new_user_data["description"] = description

    if delete_entities:
        new_user_data.pop("entities", None)
    return new_user_data


def expand_urls_in_user_url(user_data: dict, delete_entities: bool = True) -> dict:
    """
    Returns a new user data dict with expanded URLs in the URL field.
    """
    new_user_data = user_data.copy()
    url_urls = new_user_data.get("entities", {}).get("url", {}).get("urls", [])
    url = new_user_data.get("url", "")
    for url_info in url_urls:
        t_co_link = url_info["url"]
        expanded_url = url_info["expanded_url"]
        url = url.replace(t_co_link, expanded_url)
    new_user_data["url"] = url

    if delete_entities:
        new_user_data.pop("entities", None)
    return new_user_data


def remove_none_values(params: dict) -> dict:
    """
    Remove key/value pairs with None values from a dictionary.

    Args:
        params: The dictionary to clean

    Returns:
        A new dictionary with None values removed
    """
    return {k: v for k, v in params.items() if v is not None}


def expand_attached_media(params: dict) -> dict:
    """
    Include attached media metadata in the request parameters.
    """
    params["expansions"] += ",attachments.media_keys"
    params["tweet.fields"] += ",attachments"
    params["media.fields"] = ",".join([
        # media_key, url and type are returned by default, added here for clarity
        "media_key",
        "url",
        "type",
        "duration_ms",
        "height",
        "width",
        "preview_image_url",
        "alt_text",
        "public_metrics",
    ])
    return params
