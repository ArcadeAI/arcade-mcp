import os
from typing import Any, Generic, TypeVar
from urllib.parse import urljoin

import httpx
from httpx import Timeout

from arcade.client.errors import (
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnauthorizedError,
)

T = TypeVar("T")
ResponseT = TypeVar("ResponseT")

API_VERSION = "v1"
BASE_URL = "http://localhost:9099"


class BaseResource(Generic[T]):
    """Base class for all resources."""

    def __init__(self, client: T):
        self._client = client


class BaseArcadeClient:
    """Base class for Arcade clients."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        api_key: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | Timeout = 10.0,
        retries: int = 3,
    ):
        """
        Initialize the BaseArcadeClient.

        Args:
            base_url: The base URL for the Arcade API.
            api_key: The API key for authentication.
            headers: Additional headers to include in requests.
            timeout: Request timeout in seconds.
            retries: Number of retries for failed requests.
        """
        self._base_url = base_url
        self._api_key = api_key or os.environ.get("ARCADE_API_KEY")
        self._headers = headers or {}
        self._headers.setdefault("Authorization", f"Bearer {self._api_key}")
        self._headers.setdefault("Content-Type", "application/json")
        self._timeout = timeout
        self._retries = retries

    def _build_url(self, path: str) -> str:
        """
        Build the full URL for a given path.
        """
        return urljoin(self._base_url, path)

    def _chat_url(self, base_url: str) -> str:
        chat_url = str(base_url)
        if not base_url.endswith(API_VERSION):
            chat_url = f"{base_url}/{API_VERSION}"
        return chat_url

    def _handle_http_error(self, e: httpx.HTTPStatusError) -> None:
        error_map = {
            400: BadRequestError,
            401: UnauthorizedError,
            403: PermissionDeniedError,
            404: NotFoundError,
            429: RateLimitError,
            500: InternalServerError,
        }
        status_code = e.response.status_code
        error_class = error_map.get(status_code, InternalServerError)
        raise error_class(str(e), response=e.response)


class SyncArcadeClient(BaseArcadeClient):
    """Synchronous Arcade client."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._client = httpx.Client(
            base_url=self._base_url,
            headers=self._headers,
            timeout=self._timeout,
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """
        Make a synchronous HTTP request.
        """
        url = self._build_url(path)
        for attempt in range(self._retries):
            try:
                response = self._client.request(method, url, **kwargs)
                response.raise_for_status()
                return response  # noqa: TRY300
            except httpx.HTTPStatusError:
                if attempt == self._retries - 1:
                    raise
        raise RuntimeError("This should never be reached")

    def close(self) -> None:
        """Close the client session."""
        self._client.close()

    def __enter__(self) -> "SyncArcadeClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


class AsyncArcadeClient(BaseArcadeClient):
    """Asynchronous Arcade client."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create an asynchronous HTTP client.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=self._timeout,
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """
        Make an asynchronous HTTP request.
        """
        client = await self._get_client()
        url = self._build_url(path)
        for attempt in range(self._retries):
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response  # noqa: TRY300
            except httpx.HTTPStatusError:
                if attempt == self._retries - 1:
                    raise
        raise RuntimeError("This should never be reached")

    async def close(self) -> None:
        """Close the client session."""
        if self._client:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncArcadeClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
