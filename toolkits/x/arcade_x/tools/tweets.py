import json
from typing import Annotated
from arcade.core.errors import ToolExecutionError
from arcade.sdk.auth import X
import requests
from arcade.sdk import tool

from arcade.core.schema import ToolContext

from arcade_x.tools.utils import get_tweet_url

TWEETS_URL = "https://api.x.com/2/tweets"


# Manage Tweets Tools. See developer docs for additional available parameters: https://developer.x.com/en/docs/x-api/tweets/manage-tweets/api-reference
@tool(requires_auth=X(scopes=["tweet.read", "tweet.write", "users.read"]))
def post_tweet(
    context: ToolContext,
    tweet_text: Annotated[str, "The text content of the tweet you want to post"],
) -> Annotated[str, "Success string and the URL of the tweet"]:
    """Post a tweet to X (Twitter)."""

    headers = {
        "Authorization": f"Bearer {context.authorization.token}",
        "Content-Type": "application/json",
    }
    payload = {"text": tweet_text}

    response = requests.post(TWEETS_URL, headers=headers, json=payload)

    if response.status_code != 201:
        raise ToolExecutionError(
            f"Failed to post a tweet during execution of '{post_tweet.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    tweet_id = response.json()["data"]["id"]
    return (
        f"Tweet with id {tweet_id} posted successfully. URL: {get_tweet_url(tweet_id)}"
    )


@tool(requires_auth=X(scopes=["tweet.read", "tweet.write", "users.read"]))
def delete_tweet_by_id(
    context: ToolContext,
    tweet_id: Annotated[str, "The ID of the tweet you want to delete"],
) -> Annotated[str, "Success string confirming the tweet deletion"]:
    """Delete a tweet on X (Twitter)."""

    headers = {"Authorization": f"Bearer {context.authorization.token}"}
    url = f"{TWEETS_URL}/{tweet_id}"

    response = requests.delete(url, headers=headers)

    if response.status_code != 200:
        raise ToolExecutionError(
            f"Failed to delete the tweet during execution of '{delete_tweet_by_id.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    return f"Tweet with id {tweet_id} deleted successfully."


# Users Lookup Tools. See developer docs for additional available query parameters: https://developer.x.com/en/docs/x-api/users/lookup/api-reference
@tool(requires_auth=X(scopes=["users.read", "tweet.read"]))
def lookup_single_user_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the X (Twitter) user to look up"],
) -> Annotated[str, "User information including id, name, username, and description"]:
    """Look up a user on X (Twitter) by their username."""

    headers = {
        "Authorization": f"Bearer {context.authorization.token}",
    }
    url = f"https://api.x.com/2/users/by/username/{username}?user.fields=created_at,description,id,location,most_recent_tweet_id,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,verified_type,withheld"

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise ToolExecutionError(
            f"Failed to look up user during execution of '{lookup_single_user_by_username.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    return response.text


@tool(requires_auth=X(scopes=["tweet.read", "users.read"]))
def search_recent_tweets_by_query(
    context: ToolContext,
    query: Annotated[
        str,
        "The search query to match tweets. Queries are made up of operators that are used to match on a variety of Post attributes",
    ],
    max_results: Annotated[int, "The maximum number of results to return"] = 10,
) -> Annotated[str, "JSON string of the search results"]:
    """
    Search for recent tweets on X (Twitter) by query. A query is made up of operators that are used to match on a variety of Post attributes.
    """

    headers = {
        "Authorization": f"Bearer {context.authorization.token}",
        "Content-Type": "application/json",
    }
    params = {
        "query": query,  # max 512 character query for non enterprise X accounts
        "max_results": max_results,
    }

    response = requests.get(
        "https://api.x.com/2/tweets/search/recent?expansions=author_id&user.fields=id,name,username",
        headers=headers,
        params=params,
    )

    if response.status_code != 200:
        raise ToolExecutionError(
            f"Failed to search recent tweets during execution of '{search_recent_tweets_by_query.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    # TODO: Write utility function to parse tweets
    tweets_data = json.loads(response.text)
    for tweet in tweets_data["data"]:
        tweet["tweet_url"] = get_tweet_url(tweet["id"])

    return json.dumps(tweets_data)


@tool(requires_auth=X(scopes=["tweet.read", "users.read"]))
def search_recent_tweets_by_username(
    context: ToolContext,
    username: Annotated[str, "The username of the X (Twitter) user to look up"],
    max_results: Annotated[
        int, "The maximum number of results to return. Cannot be less than 10"
    ] = 10,
) -> Annotated[str, "JSON string of the search results"]:
    """Search for recent tweets (last 7 days) on X (Twitter) by username. Includes replies and reposts."""

    headers = {
        "Authorization": f"Bearer {context.authorization.token}",
        "Content-Type": "application/json",
    }
    params = {
        "query": f"from:{username}",
        "max_results": max(
            max_results, 10
        ),  # X API does not allow 'max_results' less than 10
    }
    url = "https://api.x.com/2/tweets/search/recent?expansions=author_id&user.fields=id,name,username"

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise ToolExecutionError(
            f"Failed to search recent tweets during execution of '{search_recent_tweets_by_username.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    tweets_data = json.loads(response.text)
    for tweet in tweets_data["data"]:
        tweet["tweet_url"] = get_tweet_url(tweet["id"])

    return json.dumps(tweets_data)


@tool(requires_auth=X(scopes=["tweet.read", "users.read"]))
def search_recent_tweets_by_keywords(
    context: ToolContext,
    required_keywords: Annotated[
        list[str], "List of keywords that must be present in the tweet"
    ] = None,
    required_phrases: Annotated[
        list[str], "List of phrases that must be present in the tweet"
    ] = None,
    max_results: Annotated[
        int, "The maximum number of results to return. Cannot be less than 10"
    ] = 10,
) -> Annotated[str, "JSON string of the search results"]:
    """
    Search for recent tweets (last 7 days) on X (Twitter) by required keywords and phrases. Includes replies and reposts
    One of the following MUST be provided: required_keywords, required_phrases
    """

    if not any([required_keywords, required_phrases]):
        raise ValueError(
            "At least one of required_keywords or required_phrases must be provided to the '{search_recent_tweets_by_keywords.__name__}' tool."
        )

    headers = {
        "Authorization": f"Bearer {context.authorization.token}",
        "Content-Type": "application/json",
    }
    query = " ".join([f'"{phrase}"' for phrase in required_phrases]) + " ".join(
        required_keywords
    )
    params = {
        "query": query,
        "max_results": max(
            max_results, 10
        ),  # X API does not allow 'max_results' less than 10
    }
    url = "https://api.x.com/2/tweets/search/recent?expansions=author_id&user.fields=id,name,username"

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise ToolExecutionError(
            f"Failed to search recent tweets during execution of '{search_recent_tweets_by_keywords.__name__}' tool. Request returned an error: {response.status_code} {response.text}"
        )

    tweets_data = json.loads(response.text)
    for tweet in tweets_data["data"]:
        tweet["tweet_url"] = get_tweet_url(tweet["id"])

    return json.dumps(tweets_data)
