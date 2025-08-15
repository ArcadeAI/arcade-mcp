import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import cast

import httpx

from arcade_tdk import ToolContext
from arcade_tdk.errors import RetryableToolError, ToolExecutionError, ToolRuntimeError

logger = logging.getLogger(__name__)


class BaseHttpClient(ABC):
    def __init__(
        self,
        context: ToolContext,
        max_concurrent_requests: int = 3,
    ) -> None:
        self.context: ToolContext = context

        # max_concurrent_requests value set by the context takes precedence
        secret_key = f"{self.service_name}_max_concurrent_requests"

        try:
            secret_value = context.get_secret(secret_key)
        except ValueError:
            pass
        else:
            try:
                max_concurrent_requests = int(secret_value)
            except ValueError:
                raise ValueError(
                    f"Invalid value set for the secret '{secret_key}'. "
                    f"Expected a numeric string, got '{secret_value}'."
                )

        if max_concurrent_requests < 1:
            raise ValueError(
                "Invalid value set for 'max_concurrent_requests'. "
                f"Expected a positive integer, got '{max_concurrent_requests}'."
            )

        self.max_concurrent_requests = max_concurrent_requests
        self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)

    @property
    @abstractmethod
    def service_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def default_api_version(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def default_headers(self) -> dict[str, str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def base_url(self) -> str:
        raise NotImplementedError

    @property
    def auth_token(self) -> str | None:
        return self.context.get_auth_token_or_empty()

    @abstractmethod
    def _build_url(self, path: str) -> str:
        raise NotImplementedError

    async def request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> dict:
        headers = {**self.default_headers, **(headers or {})}
        url = self._build_url(path=path)
        async with self._semaphore, httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            self._raise_for_status(response)
            return self._format_response_dict(response)

    async def get(self, path: str, headers: dict[str, str] | None = None, **kwargs) -> dict:
        return await self.request("GET", path, headers=headers, **kwargs)

    async def post(self, path: str, headers: dict[str, str] | None = None, **kwargs) -> dict:
        return await self.request("POST", path, headers=headers, **kwargs)

    async def put(self, path: str, headers: dict[str, str] | None = None, **kwargs) -> dict:
        return await self.request("PUT", path, headers=headers, **kwargs)

    async def delete(self, path: str, headers: dict[str, str] | None = None, **kwargs) -> dict:
        return await self.request("DELETE", path, headers=headers, **kwargs)

    def _format_response_dict(self, response: httpx.Response) -> dict:
        try:
            return cast(dict, response.json())
        except (UnicodeDecodeError, json.decoder.JSONDecodeError):
            return {"response": response.text}

    def _raise_for_status(self, response: httpx.Response) -> None:
        try:
            if response.status_code < 300:
                return

            if response.status_code == 404:
                message = f"Not found error: {response.text}"
            elif response.status_code == 429:
                message = "Too many requests, the service is busy. Please try again later."
            elif response.status_code < 500:
                message = f"Bad request error: {response.text}"
            else:
                message = f"Server error: {response.text}"

            developer_message = (
                f"Request to '{response.request.url}' failed "
                f"with status code {response.status_code}: {response.text}. "
                f"Response headers: {response.headers}. "
            )

            retry_after = self._retry_after_header_to_milliseconds(
                response.headers.get("Retry-After")
            )
            if retry_after:
                raise RetryableToolError(message, developer_message, retry_after_ms=retry_after)  # noqa: TRY301

            raise ToolExecutionError(message, developer_message)  # noqa: TRY301
        except ToolRuntimeError:
            raise
        except Exception:
            logger.exception()
            message = f"There was an error: {response.text}"
            raise ToolExecutionError(message, developer_message)

    def _retry_after_header_to_milliseconds(self, header: str | None) -> int | None:
        if not header:
            return None

        if header.isdigit():
            return int(header)
        else:
            try:
                datetime_obj = datetime.strptime(header, "%a, %d %b %Y %H:%M:%S GMT")
                datetime_obj = datetime_obj.replace(tzinfo=timezone.utc)
                return int(datetime_obj.timestamp() * 1000)
            except ValueError:
                return None
