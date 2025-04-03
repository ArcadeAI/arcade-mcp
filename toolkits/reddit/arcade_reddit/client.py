from typing import Any

import httpx


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
                method, f"{self.BASE_URL}/{path.lstrip('/')}", headers=headers, **kwargs
            )
            response.raise_for_status()
            return response.json()

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Any:
        return await self.request("POST", path, **kwargs)
