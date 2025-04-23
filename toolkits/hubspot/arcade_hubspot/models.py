import asyncio
import json
from dataclasses import dataclass
from typing import Any, Optional, cast

import httpx

from arcade_hubspot.constants import (
    HUBSPOT_CRM_BASE_URL,
    HUBSPOT_DEFAULT_API_VERSION,
    HUBSPOT_MAX_CONCURRENT_REQUESTS,
)
from arcade_hubspot.enums import HubspotObject
from arcade_hubspot.exceptions import HubspotToolExecutionError, NotFoundError
from arcade_hubspot.properties import get_object_properties
from arcade_hubspot.utils import clean_data, prepare_api_search_response, remove_none_values


@dataclass
class HubspotCrmClient:
    auth_token: str
    base_url: str = HUBSPOT_CRM_BASE_URL
    max_concurrent_requests: int = HUBSPOT_MAX_CONCURRENT_REQUESTS
    _semaphore: asyncio.Semaphore | None = None

    def __post_init__(self) -> None:
        self._semaphore = self._semaphore or asyncio.Semaphore(self.max_concurrent_requests)

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 300:
            return

        try:
            data = response.json()
            error_message = data["message"]
            developer_message = json.dumps(data["errors"])
        except Exception:
            error_message = response.text
            developer_message = None

        if response.status_code == 404:
            raise NotFoundError(error_message, developer_message)

        raise HubspotToolExecutionError(error_message, developer_message)

    async def get(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        api_version: str = HUBSPOT_DEFAULT_API_VERSION,
    ) -> dict:
        headers = headers or {}
        headers["Authorization"] = f"Bearer {self.auth_token}"

        kwargs = {
            "url": f"{self.base_url}/{api_version}/{endpoint}",
            "headers": headers,
        }

        if isinstance(params, dict):
            kwargs["params"] = params

        async with self._semaphore, httpx.AsyncClient() as client:  # type: ignore[union-attr]
            response = await client.get(**kwargs)  # type: ignore[arg-type]
            self._raise_for_status(response)
        return cast(dict, response.json())

    async def post(
        self,
        endpoint: str,
        data: Optional[dict] = None,
        json_data: Optional[dict] = None,
        headers: Optional[dict] = None,
        api_version: str = HUBSPOT_DEFAULT_API_VERSION,
    ) -> dict:
        headers = headers or {}
        headers["Authorization"] = f"Bearer {self.auth_token}"
        headers["Content-Type"] = "application/json"

        kwargs = {
            "url": f"{self.base_url}/{api_version}/{endpoint}",
            "headers": headers,
        }

        if data and json_data:
            raise ValueError("Cannot provide both data and json_data")

        if data:
            kwargs["data"] = data

        elif json_data:
            kwargs["json"] = json_data

        async with self._semaphore, httpx.AsyncClient() as client:  # type: ignore[union-attr]
            response = await client.post(**kwargs)  # type: ignore[arg-type]
            self._raise_for_status(response)
        return cast(dict, response.json())

    async def get_associated_objects(
        self,
        parent_object: HubspotObject,
        parent_id: str,
        associated_object: HubspotObject,
        limit: int = 10,
        after: Optional[str] = None,
        properties: Optional[list[str]] = None,
    ) -> list[dict]:
        endpoint = (
            f"objects/{parent_object.value}/{parent_id}/associations/{associated_object.value}"
        )
        params = {
            "limit": limit,
        }
        if after:
            params["after"] = after  # type: ignore[assignment]

        response = await self.get(endpoint, params=params, api_version="v4")

        if not response["results"]:
            return []

        return await self.batch_get_objects(
            object_type=associated_object,
            object_ids=[object_data["toObjectId"] for object_data in response["results"]],
            properties=properties or get_object_properties(associated_object),
        )

    async def get_object_by_id(
        self,
        object_type: HubspotObject,
        object_id: str,
        properties: Optional[list[str]] = None,
    ) -> dict:
        endpoint = f"objects/{object_type.plural}/{object_id}"
        params = {}
        if properties:
            params["properties"] = properties
        return clean_data(await self.get(endpoint, params=params), object_type)

    async def batch_get_objects(
        self,
        object_type: HubspotObject,
        object_ids: list[str],
        properties: Optional[list[str]] = None,
    ) -> list[dict]:
        endpoint = f"objects/{object_type.plural}/batch/read"
        data: dict[str, Any] = {"inputs": [{"id": object_id} for object_id in object_ids]}
        if properties:
            data["properties"] = properties
        response = await self.post(endpoint, json_data=data)
        return [clean_data(object_data, object_type) for object_data in response["results"]]

    async def search_by_keywords(
        self,
        object_type: HubspotObject,
        keywords: str,
        limit: int = 10,
        next_page_token: Optional[str] = None,
        associations: Optional[list[HubspotObject]] = None,
    ) -> dict:
        if not keywords:
            raise HubspotToolExecutionError("`keywords` must be a non-empty string")

        associations = associations or []

        endpoint = f"objects/{object_type.plural}/search"
        request_data = {
            "query": keywords,
            "limit": limit,
            "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}],
            "properties": get_object_properties(object_type),
        }

        if next_page_token:
            request_data["after"] = next_page_token

        data = prepare_api_search_response(
            data=await self.post(endpoint, json_data=request_data),
            object_type=object_type,
        )

        for object_ in data[object_type.plural]:
            for association in associations:
                results = await self.get_associated_objects(
                    parent_object=object_type,
                    parent_id=object_["id"],
                    associated_object=association,
                    limit=10,
                )
                if results:
                    object_[association.plural] = results

        return data

    async def create_contact(
        self,
        company_id: str,
        first_name: str,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        mobile_phone: Optional[str] = None,
        job_title: Optional[str] = None,
    ) -> dict:
        request_data = {
            "associations": [
                {
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": "1",
                        }
                    ],
                    "to": {"id": company_id},
                },
            ],
            "properties": remove_none_values({
                "firstname": first_name,
                "lastname": last_name,
                "email": email,
                "phone": phone,
                "mobilephone": mobile_phone,
                "jobtitle": job_title,
            }),
        }
        endpoint = "objects/contacts"
        return await self.post(endpoint, json_data=request_data)
