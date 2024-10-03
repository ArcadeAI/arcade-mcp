import json
from typing import Any


def get_tweet_url(tweet_id: str) -> str:
    """Get the URL of a tweet given its ID."""
    return f"https://x.com/x/status/{tweet_id}"


def parse_search_recent_tweets_response(response_data: Any) -> str:
    """
    Parses response from the X API search recent tweets endpoint.
    Returns a JSON string with the tweets data.

    Example parsed response:
    "tweets": [
        {
            "author_id": "558248927",
            "id": "1838272933141319832",
            "edit_history_tweet_ids": [
                "1838272933141319832"
            ],
            "text": "PR pending on @LangChainAI, will be integrated there soon! https://t.co/DPWd4lccQo",
            "tweet_url": "https://x.com/x/status/1838272933141319832",
            "author_username": "tomas_hk",
            "author_name": "Tomas Hernando Kofman"
        },
    ]
    """

    if not sanity_check_tweets_data(response_data):
        return json.dumps({"tweets": []})

    for tweet in response_data["data"]:
        tweet["tweet_url"] = get_tweet_url(tweet["id"])

    for tweet_data, user_data in zip(response_data["data"], response_data["includes"]["users"]):
        tweet_data["author_username"] = user_data["username"]
        tweet_data["author_name"] = user_data["name"]

    return {"tweets": response_data["data"]}


def sanity_check_tweets_data(tweets_data: dict) -> bool:
    """
    Sanity check the tweets data.
    Returns True if the tweets data is valid and contains tweets, False otherwise.
    """
    if not tweets_data.get("data", []):
        return False
    return tweets_data.get("includes", {}).get("users", [])
