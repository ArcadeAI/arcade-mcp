import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx

from arcade_hubspot.constants import HUBSPOT_CRM_BASE_URL, HUBSPOT_DEFAULT_API_VERSION
from arcade_hubspot.enums import HubspotObject
from arcade_hubspot.exceptions import HubspotToolExecutionError, NotFoundError
from arcade_hubspot.utils import clean_data, prepare_api_search_response


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

        async with httpx.AsyncClient() as client:
            response = await client.post(**kwargs)
            self._raise_for_status(response)
        return response.json()

    async def _get_associated_objects(
        self,
        parent_object: HubspotObject,
        parent_id: str,
        associated_object: HubspotObject,
        limit: int = 10,
        after: Optional[str] = None,
    ) -> list[dict]:
        endpoint = (
            f"objects/{parent_object.value}/{parent_id}/associations/{associated_object.value}"
        )
        params = {
            "limit": limit,
        }
        if after:
            params["after"] = after

        response = await self.get(endpoint, params=params, api_version="v4")

        if not response["results"]:
            return []

        return await asyncio.gather(*[
            self._get_object_by_id(associated_object, object_data["toObjectId"])
            for object_data in response["results"]
        ])

    async def _get_object_by_id(self, object_type: HubspotObject, object_id: str) -> dict:
        endpoint = f"objects/{object_type.value}/{object_id}"
        return clean_data(await self.get(endpoint), object_type)

    async def get_company_contacts(
        self,
        company_id: str,
        limit: int = 10,
        after: Optional[str] = None,
    ) -> dict:
        return await self._get_associated_objects(
            parent_object=HubspotObject.COMPANY,
            parent_id=company_id,
            associated_object=HubspotObject.CONTACT,
            limit=limit,
            after=after,
        )

    async def get_company_deals(
        self,
        company_id: str,
        limit: int = 10,
        after: Optional[str] = None,
    ) -> dict:
        return await self._get_associated_objects(
            parent_object=HubspotObject.COMPANY,
            parent_id=company_id,
            associated_object=HubspotObject.DEAL,
            limit=limit,
            after=after,
        )

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

        data = prepare_api_search_response(
            data=await self.post(endpoint, json_data=request_data),
            object_type=object_type,
        )

        for company in data[object_type.plural]:
            contacts = await self.get_company_contacts(company["id"], limit=10)
            deals = await self.get_company_deals(company["id"], limit=10)
            if contacts:
                company["contacts"] = contacts
            if deals:
                company["deals"] = deals

        return data
