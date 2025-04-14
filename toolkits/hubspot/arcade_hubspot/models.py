from dataclasses import dataclass
from typing import Optional

import httpx

from arcade_hubspot.constants import HUBSPOT_CRM_BASE_URL
from arcade_hubspot.enums import HubspotObject
from arcade_hubspot.exceptions import HubspotToolExecutionError, NotFoundError
from arcade_hubspot.utils import prepare_api_search_response


@dataclass
class HubspotClient:
    auth_token: str
    base_url: str = HUBSPOT_CRM_BASE_URL

    def _raise_for_status(self, response: httpx.Response):
        if response.status_code < 300:
            return

        if response.status_code == 404:
            raise NotFoundError(response.text)

        raise HubspotToolExecutionError(response.text)

    async def get(
        self,
        endpoint: str,
        params: dict,
        headers: Optional[dict] = None,
    ) -> dict:
        headers = headers or {}
        headers["Authorization"] = f"Bearer {self.auth_token}"

        kwargs = {
            "url": f"{self.base_url}/{endpoint}",
            "headers": headers,
        }

        if params:
            kwargs["params"] = params

        async with httpx.AsyncClient() as client:
            response = await client.get(**kwargs)
            self._raise_for_status(response)
        return response.json()

    async def post(
        self,
        endpoint: str,
        data: Optional[dict] = None,
        json_data: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> dict:
        headers = headers or {}
        headers["Authorization"] = f"Bearer {self.auth_token}"
        headers["Content-Type"] = "application/json"

        kwargs = {
            "url": f"{self.base_url}/{endpoint}",
            "headers": headers,
        }

        if data and json_data:
            raise ValueError("Cannot provide both data and json_data")

        if data:
            kwargs["data"] = data

        elif json_data:
            kwargs["json"] = json_data

        async with httpx.AsyncClient() as client:
            response = await client.post(**kwargs)
            self._raise_for_status(response)
        return response.json()

    async def search_by_keywords(
        self,
        object_type: HubspotObject,
        keywords: str,
        limit: int = 10,
        next_page_token: Optional[str] = None,
    ) -> dict:
        endpoint = f"objects/{object_type.plural}/search"
        request_data = {
            "query": keywords,
            "limit": limit,
            "sorts": [{"propertyName": "updatedAt", "direction": "DESCENDING"}],
        }

        if next_page_token:
            request_data["after"] = next_page_token

        return prepare_api_search_response(
            data=await self.post(endpoint, json_data=request_data),
            object_type=object_type,
        )
