from typing import Annotated
from arcade.core.errors import ToolExecutionError
from arcade.sdk.auth import X
import requests
from arcade.sdk import tool

from arcade.core.schema import ToolContext

TWEETS_URL = "https://api.x.com/2/tweets"


# Manage Tweets
@tool(requires_auth=X(scopes=["tweet.read", "tweet.write", "users.read"]))
def post_tweet(
    context: ToolContext,
    tweet_text: Annotated[str, "The text content of the tweet you want to post"],
) -> Annotated[str, "Success string and the URL of the tweet"]:
    """Post a tweet to X (formerly Twitter)."""

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

    return "Tweet posted successfully: https://TODO_the_tweet_url"
