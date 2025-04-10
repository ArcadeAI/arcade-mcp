import asyncio
import os
from dataclasses import dataclass
from typing import Any, Optional, cast

import httpx

from arcade_salesforce.constants import SALESFORCE_API_VERSION
from arcade_salesforce.enums import SalesforceObject
from arcade_salesforce.utils import clean_contact_data, clean_lead_data, clean_note_data


@dataclass
class SalesforceClient:
    auth_token: str
    org_domain: Optional[str] = None
    api_version: str = SALESFORCE_API_VERSION

    # Internal state properties
    _state_object_fields: Optional[dict[SalesforceObject, list[str]]] = None
    _state_is_person_account_enabled: Optional[bool] = None

    def __post_init__(self) -> None:
        if self.org_domain is None:
            self.org_domain = os.getenv("SALESFORCE_ORG_DOMAIN")
        if self.org_domain is None:
            raise ValueError(
                "Either `org_domain` argument or `SALESFORCE_ORG_DOMAIN` env var must be set"
            )

        if self._state_object_fields is None:
            self._state_object_fields = {}

    @property
    def _base_url(self) -> str:
        return f"https://{self.org_domain}.my.salesforce.com/services/data/{self.api_version}"

    @property
    def object_fields(self) -> dict[SalesforceObject, list[str]]:
        return cast(dict, self._state_object_fields)

    def _endpoint_url(self, endpoint: str) -> str:
        return f"{self._base_url}/{endpoint.lstrip('/')}"

    def _build_headers(self, headers: Optional[dict] = None) -> dict:
        headers = headers or {}
        headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def get(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> dict:
        with httpx.Client() as client:
            response = client.get(
                self._endpoint_url(endpoint),
                params=params,
                headers=self._build_headers(headers),
            )
            response.raise_for_status()
            return cast(dict, response.json())

    async def post(
        self,
        endpoint: str,
        data: Optional[dict] = None,
        json_data: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> dict:
        with httpx.Client() as client:
            response = client.post(
                self._endpoint_url(endpoint),
                data=data,
                json=json_data,
                headers=self._build_headers(headers),
            )
            response.raise_for_status()
            return cast(dict, response.json())

    async def get_object_fields(self, object_type: SalesforceObject) -> list[str]:
        if object_type not in self.object_fields:
            response = await self._describe_object(object_type)
            self.object_fields[object_type] = [field["name"] for field in response["fields"]]

        return self.object_fields[object_type]

    async def _describe_object(self, object_type: SalesforceObject) -> dict:
        return await self.get(f"sobjects/{object_type.value}/describe/")

    async def get_account(self, account_id: str) -> dict[str, Any]:
        return cast(dict, await self.get(f"sobjects/Account/{account_id}"))

    async def _get_related_objects(
        self,
        child_object_type: SalesforceObject,
        parent_object_type: SalesforceObject,
        parent_object_id: str,
    ) -> list[dict]:
        try:
            response = await self.get(
                f"sobjects/{parent_object_type.value}/{parent_object_id}/{child_object_type.value.lower()}s"
            )
            return cast(list, response["records"])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise

    async def get_account_contacts(self, account_id: str) -> list[dict]:
        contacts = await self._get_related_objects(
            SalesforceObject.CONTACT, SalesforceObject.ACCOUNT, account_id
        )
        return [clean_contact_data(contact) for contact in contacts]

    async def get_account_leads(self, account_id: str) -> list[dict]:
        leads = await self._get_related_objects(
            SalesforceObject.LEAD, SalesforceObject.ACCOUNT, account_id
        )
        return [clean_lead_data(lead) for lead in leads]

    async def get_account_notes(self, account_id: str) -> list[dict]:
        notes = await self._get_related_objects(
            SalesforceObject.NOTE, SalesforceObject.ACCOUNT, account_id
        )
        return [clean_note_data(note) for note in notes]

    async def enrich_account(
        self,
        account_id: Optional[str] = None,
        account_data: Optional[dict[str, Any]] = None,
    ) -> dict:
        """Enrich account dictionary with notes, leads, contacts, etc.

        Must provide either `account_id` or `account_data`.
        """
        if (account_id and account_data) or (not account_id and not account_data):
            raise ValueError("Must provide either `account_id` or `account_data`")

        if account_data is None:
            account_data = await self.get_account(cast(str, account_id))

        if not account_id:
            account_id = cast(str, account_data["Id"])

        associations = await asyncio.gather(
            self.get_account_contacts(account_id),
            self.get_account_leads(account_id),
            self.get_account_notes(account_id),
        )

        account_data[SalesforceObject.CONTACT.value + "s"] = []
        account_data[SalesforceObject.LEAD.value + "s"] = []
        account_data[SalesforceObject.NOTE.value + "s"] = []

        for association in associations:
            for item in association:
                account_data[item["ObjectType"] + "s"].append(item)

        return account_data
