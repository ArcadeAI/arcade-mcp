from typing import Annotated

import httpx

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import X
from arcade.sdk.errors import ToolExecutionError
from arcade_x.tools.utils import (
    expand_urls_in_tweets,
    get_tweet_url,
    parse_search_recent_tweets_response,
)

TWEETS_URL = "https://api.x.com/2/tweets"


# Manage Tweets Tools. See developer docs for additional available parameters: https://developer.x.com/en/docs/x-api/tweets/manage-tweets/api-reference
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

    headers = {
        "Authorization": f"Bearer {context.authorization.token}",
        "Content-Type": "application/json",
    }
    payload = {"text": tweet_text}

    async with httpx.AsyncClient() as client:
        response = await client.post(TWEETS_URL, headers=headers, json=payload, timeout=10)

    if response.status_code != 201:
        raise ToolExecutionError(
            f"Failed to post a tweet during execution of '{post_tweet.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    tweet_id = response.json()["data"]["id"]
    return f"Tweet with id {tweet_id} posted successfully. URL: {get_tweet_url(tweet_id)}"


@tool(requires_auth=X(scopes=["tweet.read", "tweet.write", "users.read"]))
async def delete_tweet_by_id(
    context: ToolContext,
    tweet_id: Annotated[str, "The ID of the tweet you want to delete"],
) -> Annotated[str, "Success string confirming the tweet deletion"]:
    """Delete a tweet on X (Twitter)."""

    headers = {"Authorization": f"Bearer {context.authorization.token}"}
    url = f"{TWEETS_URL}/{tweet_id}"

    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=headers, timeout=10)

    if response.status_code != 200:
        raise ToolExecutionError(
            f"Failed to delete the tweet during execution of '{delete_tweet_by_id.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    return f"Tweet with id {tweet_id} deleted successfully."


@tool(requires_auth=X(scopes=["tweet.read", "users.read"]))
async def search_recent_tweets_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the X (Twitter) user to look up"],
    max_results: Annotated[
        int, "The maximum number of results to return. Cannot be less than 10"
    ] = 10,
) -> Annotated[dict, "Dictionary containing the search results"]:
    """Search for recent tweets (last 7 days) on X (Twitter) by username. Includes replies and reposts."""

    headers = {
        "Authorization": f"Bearer {context.authorization.token}",
        "Content-Type": "application/json",
    }
    params = {
        "query": f"from:{username}",
        "max_results": max(max_results, 10),  # X API does not allow 'max_results' less than 10
    }
    url = "https://api.x.com/2/tweets/search/recent?expansions=author_id&user.fields=id,name,username,entities&tweet.fields=entities"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params, timeout=10)

    if response.status_code != 200:
        raise ToolExecutionError(
            f"Failed to search recent tweets during execution of '{search_recent_tweets_by_username.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    response_data = response.json()

    # Expand the urls that are in the tweets
    expand_urls_in_tweets(response_data.get("data", []), delete_entities=True)

    parse_search_recent_tweets_response(response_data)

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
        int, "The maximum number of results to return. Cannot be less than 10"
    ] = 10,
) -> Annotated[dict, "Dictionary containing the search results"]:
    """
    Search for recent tweets (last 7 days) on X (Twitter) by required keywords and phrases. Includes replies and reposts
    One of the following input parametersMUST be provided: keywords, phrases
    """

    if not any([keywords, phrases]):
        raise ValueError(
            "At least one of keywords or phrases must be provided to the '{search_recent_tweets_by_keywords.__name__}' tool."
        )

    headers = {
        "Authorization": f"Bearer {context.authorization.token}",
        "Content-Type": "application/json",
    }
    query = "".join([f'"{phrase}" ' for phrase in (phrases or [])])
    if keywords:
        query += " ".join(keywords or [])

    params = {
        "query": query,
        "max_results": max(max_results, 10),  # X API does not allow 'max_results' less than 10
    }
    url = "https://api.x.com/2/tweets/search/recent?expansions=author_id&user.fields=id,name,username,entities&tweet.fields=entities"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params, timeout=10)

    if response.status_code != 200:
        raise ToolExecutionError(
            f"Failed to search recent tweets during execution of '{search_recent_tweets_by_keywords.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    response_data = response.json()

    # Expand the urls that are in the tweets
    expand_urls_in_tweets(response_data.get("data", []), delete_entities=True)

    parse_search_recent_tweets_response(response_data)

    return response_data
