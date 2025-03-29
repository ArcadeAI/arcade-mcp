import time
from typing import Any

import httpx
import praw


class RedditClient:
    BASE_URL = "https://oauth.reddit.com/"

    def __init__(self, token: str):
        self.token = token

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "arcade-reddit",
        }
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, f"{self.BASE_URL}/{path}", headers=headers, **kwargs
            )
            response.raise_for_status()
            return response.json()

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Any:
        return await self.request("POST", path, **kwargs)


class PRAWClient:
    def __init__(self, token: str, scopes: list[str]):
        self.token = token
        # Create the Reddit instance with your app credentials.
        self.reddit = praw.Reddit(
            client_id="NA",
            client_secret="NA",  # noqa: S106
            user_agent="arcade-reddit",
        )

        self.reddit._core._authorizer.access_token = token
        self.reddit._core._authorizer.scopes = scopes
        self.reddit._core._authorizer._expiration_timestamp = time.time() + 3600
