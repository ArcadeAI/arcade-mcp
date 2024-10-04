from typing import Any


def get_tweet_url(tweet_id: str) -> str:
    """Get the URL of a tweet given its ID."""
    return f"https://x.com/x/status/{tweet_id}"


def parse_search_recent_tweets_response(response_data: Any) -> dict:
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
        return {"data": []}

    for tweet in response_data["data"]:
        tweet["tweet_url"] = get_tweet_url(tweet["id"])

    for tweet_data, user_data in zip(response_data["data"], response_data["includes"]["users"]):
        tweet_data["author_username"] = user_data["username"]
        tweet_data["author_name"] = user_data["name"]

    return response_data


def sanity_check_tweets_data(tweets_data: dict) -> bool:
    """
    Sanity check the tweets data.
    Returns True if the tweets data is valid and contains tweets, False otherwise.
    """
    if not tweets_data.get("data", []):
        return False
    return tweets_data.get("includes", {}).get("users", [])


def expand_urls_in_tweets(tweets_data: list[dict], delete_entities: bool = True) -> None:
    """
    Expands the urls in the test of the provided tweets.
    X shortens urls, and consequently, this can cause language models to hallucinate.
    See more about X's link shortner at https://help.x.com/en/using-x/url-shortener
    """
    for tweet_data in tweets_data:
        if "entities" in tweet_data and "urls" in tweet_data["entities"]:
            for url_entity in tweet_data["entities"]["urls"]:
                short_url = url_entity["url"]
                expanded_url = url_entity["expanded_url"]
                tweet_data["text"] = tweet_data["text"].replace(short_url, expanded_url)

        if delete_entities:
            tweet_data.pop(
                "entities", None
            )  # Now that we've expanded the urls in the tweet, we no longer need the entities


def expand_urls_in_user_description(user_data: dict, delete_entities: bool = True) -> None:
    """
    Expands the urls in the description of the provided user.
    X shortens urls, and consequently, this can cause language models to hallucinate.
    See more about X's link shortner at https://help.x.com/en/using-x/url-shortener
    """
    description_urls = user_data.get("entities", {}).get("description", {}).get("urls", [])
    description = user_data.get("description", "")
    for url_info in description_urls:
        t_co_link = url_info["url"]
        expanded_url = url_info["expanded_url"]
        description = description.replace(t_co_link, expanded_url)
    user_data["description"] = description

    if delete_entities:
        # Entities is no longer needed now that we have expanded the t.co links
        user_data.pop("entities", None)


def expand_urls_in_user_url(user_data: dict, delete_entities: bool = True) -> None:
    """
    Expands the urls in the url section of the provided user.
    X shortens urls, and consequently, this can cause language models to hallucinate.
    See more about X's link shortner at https://help.x.com/en/using-x/url-shortener
    """
    url_urls = user_data.get("entities", {}).get("url", {}).get("urls", [])
    url = user_data.get("url", "")
    for url_info in url_urls:
        t_co_link = url_info["url"]
        expanded_url = url_info["expanded_url"]
        url = url.replace(t_co_link, expanded_url)
    user_data["url"] = url

    if delete_entities:
        # Entities is no longer needed now that we have expanded the t.co links
        user_data.pop("entities", None)
