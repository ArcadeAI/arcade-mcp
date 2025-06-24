import asyncio
import json
import json.decoder
from dataclasses import dataclass
from typing import Any, cast

import httpx

import arcade_jira.cache as cache
from arcade_jira.constants import JIRA_API_VERSION, JIRA_BASE_URL, JIRA_MAX_CONCURRENT_REQUESTS
from arcade_jira.exceptions import JiraToolExecutionError, NotFoundError


@dataclass
class JiraClient:
    auth_token: str
    base_url: str = JIRA_BASE_URL
    api_version: str = JIRA_API_VERSION
    max_concurrent_requests: int = JIRA_MAX_CONCURRENT_REQUESTS
    _semaphore: asyncio.Semaphore | None = None
    _cloud_id: str | None = None

    def __post_init__(self) -> None:
        if not self._semaphore:
            cached_semaphore = cache.get_jira_client_semaphore(self.auth_token)

            if cached_semaphore:
                self._semaphore = cached_semaphore
            else:
                self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
                cache.set_jira_client_semaphore(self.auth_token, self._semaphore)

        self.base_url = self.base_url.rstrip("/")
        self.api_version = self.api_version.strip("/")

    async def get_cloud_id(self) -> str:
        if self._cloud_id is None:
            if (cloud_id := await cache.async_get_cloud_id(self.auth_token)) is not None:
                self._cloud_id = cloud_id
            else:
                cloud = await self._get_cloud_data_from_available_resources()
                self._cloud_id = cloud["id"]
                await cache.async_set_cloud_id(self.auth_token, cloud["id"])
                await cache.async_set_cloud_name(self.auth_token, cloud["name"])

        return self._cloud_id

    async def _build_url(self, endpoint: str) -> str:
        cloud_id = await self.get_cloud_id()
        return f"{self.base_url}/{cloud_id}/rest/api/{self.api_version}/{endpoint.lstrip('/')}"

    async def _get_cloud_data_from_available_resources(self) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers={"Authorization": f"Bearer {self.auth_token}"},
            )

            available_resources = deduplicate_available_resources(response.json())

            if len(available_resources) == 0:
                raise JiraToolExecutionError(
                    message="No cloud ID returned by Atlassian, cannot make API calls"
                )
            if len(available_resources) > 1:
                cloud_ids_found = json.dumps([
                    {
                        "id": resource["id"],
                        "name": resource["name"],
                        "url": resource["url"],
                    }
                    for resource in available_resources
                ])
                raise JiraToolExecutionError(
                    message=(
                        "Multiple cloud IDs returned by Atlassian, cannot resolve which one "
                        "to use. Please revoke your authorization access and authorize a single "
                        f"Atlassian Cloud. Available cloud IDs: {cloud_ids_found}. "
                    )
                )
            return cast(dict[str, Any], available_resources[0])

    def _build_error_messages(self, response: httpx.Response) -> tuple[str, str | None]:
        try:
            data = response.json()
            developer_message = None

            if "errorMessages" in data:
                if len(data["errorMessages"]) == 1:
                    error_message = cast(str, data["errorMessages"][0])
                elif "errors" in data:
                    error_message = json.dumps(data["errors"])
                else:
                    error_message = "Unknown error"

            elif "message" in data:
                error_message = cast(str, data["message"])

            else:
                error_message = json.dumps(data)

        except Exception as e:
            error_message = "Failed to parse Jira error response"
            developer_message = (
                f"Failed to parse Jira error response: {type(e).__name__}: {e!s}. "
                f"API Response: {response.text}"
            )

        return error_message, developer_message

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 300:
            return

        error_message, developer_message = self._build_error_messages(response)

        if response.status_code == 404:
            raise NotFoundError(error_message, developer_message)

        raise JiraToolExecutionError(error_message, developer_message)

    def _set_request_body(self, kwargs: dict, data: dict | None, json_data: dict | None) -> dict:
        if data and json_data:
            raise ValueError("Cannot provide both data and json_data")  # noqa: TRY003

        if data:
            kwargs["data"] = data

        elif json_data:
            kwargs["json"] = json_data

        return kwargs

    def _format_response_dict(self, response: httpx.Response) -> dict:
        try:
            return cast(dict, response.json())
        except (UnicodeDecodeError, json.decoder.JSONDecodeError):
            return {"text": response.text}

    async def get(
        self,
        endpoint: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        default_headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json",
        }
        headers = {**default_headers, **(headers or {})}

        kwargs = {
            "url": await self._build_url(endpoint),
            "headers": headers,
        }

        if params:
            kwargs["params"] = params

        async with self._semaphore, httpx.AsyncClient() as client:  # type: ignore[union-attr]
            response = await client.get(**kwargs)  # type: ignore[arg-type]
            self._raise_for_status(response)

        return self._format_response_dict(response)

    async def post(
        self,
        endpoint: str,
        data: dict | None = None,
        json_data: dict | None = None,
        files: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        default_headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json",
        }

        if files is None and json_data is not None:
            default_headers["Content-Type"] = "application/json"

        headers = {**default_headers, **(headers or {})}

        kwargs = {
            "url": await self._build_url(endpoint),
            "headers": headers,
        }

        if files is not None:
            kwargs["files"] = files
            if data is not None:
                kwargs["data"] = data
        else:
            kwargs = self._set_request_body(kwargs, data, json_data)

        async with self._semaphore, httpx.AsyncClient() as client:  # type: ignore[union-attr]
            response = await client.post(**kwargs)  # type: ignore[arg-type]
            self._raise_for_status(response)

        return self._format_response_dict(response)

    async def put(
        self,
        endpoint: str,
        data: dict | None = None,
        json_data: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        headers = headers or {}
        headers["Authorization"] = f"Bearer {self.auth_token}"
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"

        kwargs = {
            "url": await self._build_url(endpoint),
            "headers": headers,
        }

        kwargs = self._set_request_body(kwargs, data, json_data)

        if params:
            kwargs["params"] = params

        async with self._semaphore, httpx.AsyncClient() as client:  # type: ignore[union-attr]
            response = await client.put(**kwargs)  # type: ignore[arg-type]
            self._raise_for_status(response)

        return self._format_response_dict(response)


def deduplicate_available_resources(available_resources: list[dict]) -> list[dict]:
    account_ids_seen = set()
    deduplicated = []

    for item in available_resources:
        if item["id"] not in account_ids_seen:
            deduplicated.append(item)
            account_ids_seen.add(item["id"])

    return deduplicated
