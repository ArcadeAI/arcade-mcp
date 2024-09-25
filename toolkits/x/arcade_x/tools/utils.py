import json

from requests import Response


def get_tweet_url(tweet_id: str) -> str:
    """Get the URL of a tweet given its ID."""
    return f"https://x.com/x/status/{tweet_id}"


def parse_search_recent_tweets_response(response: Response) -> str:
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
    if response.status_code != 200:
        return json.dumps({"tweets": []})

    tweets_data = json.loads(response.text)

    if not sanity_check_tweets_data(tweets_data):
        return json.dumps({"tweets": []})

    for tweet in tweets_data["data"]:
        tweet["tweet_url"] = get_tweet_url(tweet["id"])

    for tweet_data, user_data in zip(tweets_data["data"], tweets_data["includes"]["users"]):
        tweet_data["author_username"] = user_data["username"]
        tweet_data["author_name"] = user_data["name"]

    return json.dumps({"tweets": tweets_data["data"]})


def sanity_check_tweets_data(tweets_data: dict) -> bool:
    """
    Sanity check the tweets data.
    Returns True if the tweets data is valid and contains tweets, False otherwise.
    """
    if not tweets_data.get("data", []):
        return False
    if not tweets_data.get("includes", {}).get("users", []):
        return False
    return True
