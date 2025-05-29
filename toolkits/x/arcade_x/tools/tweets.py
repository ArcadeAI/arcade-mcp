from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import X
from arcade_tdk.errors import RetryableToolError

from arcade_x.tools.constants import TWEETS_URL
from arcade_x.tools.utils import (
    expand_attached_media,
    expand_long_tweet,
    expand_urls_in_tweets,
    get_headers_with_token,
    get_tweet_url,
    parse_search_recent_tweets_response,
    remove_none_values,
)

# Manage Tweets Tools. See developer docs for additional available parameters:
# https://developer.x.com/en/docs/x-api/tweets/manage-tweets/api-reference


@tool(
    requires_auth=X(
        scopes=["tweet.read", "tweet.write", "users.read"],
    )
)
async def post_tweet(
    context: ToolContext,
    tweet_text: Annotated[str, "The text content of the tweet you want to post"],
) -> Annotated[str, "Success string and the URL of the tweet"]:
    """Post a tweet to X (Twitter)."""

    headers = get_headers_with_token(context)
    payload = {"text": tweet_text}

    async with httpx.AsyncClient() as client:
        response = await client.post(TWEETS_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()

    tweet_id = response.json()["data"]["id"]
    return f"Tweet with id {tweet_id} posted successfully. URL: {get_tweet_url(tweet_id)}"


@tool(requires_auth=X(scopes=["tweet.read", "tweet.write", "users.read"]))
async def delete_tweet_by_id(
    context: ToolContext,
    tweet_id: Annotated[str, "The ID of the tweet you want to delete"],
) -> Annotated[str, "Success string confirming the tweet deletion"]:
    """Delete a tweet on X (Twitter)."""

    headers = get_headers_with_token(context)
    url = f"{TWEETS_URL}/{tweet_id}"

    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=headers, timeout=10)
        response.raise_for_status()

    return f"Tweet with id {tweet_id} deleted successfully."


@tool(requires_auth=X(scopes=["tweet.read", "users.read"]))
async def search_recent_tweets_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the X (Twitter) user to look up"],
    max_results: Annotated[
        int, "The maximum number of results to return. Must be in range [1, 100] inclusive"
    ] = 10,
    next_token: Annotated[
        str | None, "The pagination token starting from which to return results"
    ] = None,
) -> Annotated[dict[str, Any], "Dictionary containing the search results"]:
    """Search for recent tweets (last 7 days) on X (Twitter) by username.
    Includes replies and reposts."""

    headers = get_headers_with_token(context)
    params: dict[str, Any] = {
        "query": f"from:{username}",
        "max_results": min(
            max(max_results, 10), 100
        ),  # X API does not allow 'max_results' less than 10 or greater than 100
        "next_token": next_token,
        "expansions": "author_id",
        "user.fields": "id,name,username,entities",
        "tweet.fields": "entities,note_tweet",
    }
    params = expand_attached_media(remove_none_values(params))

    url = f"{TWEETS_URL}/search/recent"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

    response_data: dict[str, Any] = response.json()

    for tweet in response_data.get("data", []):
        expand_long_tweet(tweet)

    # Expand the URLs that are in the tweets
    response_data["data"] = expand_urls_in_tweets(
        response_data.get("data", []), delete_entities=True
    )

    # Parse the response data
    response_data = parse_search_recent_tweets_response(response_data)

    return response_data


@tool(requires_auth=X(scopes=["tweet.read", "users.read"]))
async def search_recent_tweets_by_keywords(
    context: ToolContext,
    keywords: Annotated[
        list[str] | None, "List of keywords that must be present in the tweet"
    ] = None,
    phrases: Annotated[
        list[str] | None, "List of phrases that must be present in the tweet"
    ] = None,
    max_results: Annotated[
        int, "The maximum number of results to return. Must be in range [1, 100] inclusive"
    ] = 10,
    next_token: Annotated[
        str | None, "The pagination token starting from which to return results"
    ] = None,
) -> Annotated[dict[str, Any], "Dictionary containing the search results"]:
    """
    Search for recent tweets (last 7 days) on X (Twitter) by required keywords and phrases.
    Includes replies and reposts.
    One of the following input parameters MUST be provided: keywords, phrases
    """

    if not any([keywords, phrases]):
        raise RetryableToolError(
            "No keywords or phrases provided",
            developer_message="Predicted inputs didn't contain any keywords or phrases",
            additional_prompt_content="Please provide at least one keyword or phrase for search",
            retry_after_ms=500,  # Play nice with X API rate limits
        )

    headers = get_headers_with_token(context)

    query = "".join([f'"{phrase}" ' for phrase in (phrases or [])])
    if keywords:
        query += " ".join(keywords or [])

    params: dict[str, Any] = {
        "query": query.strip(),
        "max_results": min(
            max(max_results, 10), 100
        ),  # X API does not allow 'max_results' less than 10 or greater than 100
        "next_token": next_token,
        "expansions": "author_id",
        "user.fields": "id,name,username,entities",
        "tweet.fields": "entities,note_tweet",
    }
    params = expand_attached_media(remove_none_values(params))

    url = f"{TWEETS_URL}/search/recent"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

    response_data: dict[str, Any] = response.json()

    for tweet in response_data.get("data", []):
        expand_long_tweet(tweet)

    # Expand the URLs that are in the tweets
    response_data["data"] = expand_urls_in_tweets(
        response_data.get("data", []), delete_entities=True
    )

    # Parse the response data
    response_data = parse_search_recent_tweets_response(response_data)

    return response_data


@tool(requires_auth=X(scopes=["tweet.read", "users.read"]))
async def lookup_tweet_by_id(
    context: ToolContext,
    tweet_id: Annotated[str, "The ID of the tweet you want to look up"],
) -> Annotated[dict[str, Any], "Dictionary containing the tweet data"]:
    """Look up a tweet on X (Twitter) by tweet ID."""

    headers = get_headers_with_token(context)
    params = {
        "expansions": "author_id",
        "user.fields": "id,name,username,entities",
        "tweet.fields": "entities,note_tweet",
    }
    params = expand_attached_media(params)

    url = f"{TWEETS_URL}/{tweet_id}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

    response_data: dict[str, Any] = response.json()

    # Get the tweet data
    tweet_data = response_data.get("data")
    if tweet_data:
        expand_long_tweet(tweet_data)

        # Expand the URLs that are in the tweet
        expanded_tweet_list = expand_urls_in_tweets([tweet_data], delete_entities=True)
        response_data["data"] = expanded_tweet_list[0]
    else:
        response_data["data"] = {}

    return response_data
