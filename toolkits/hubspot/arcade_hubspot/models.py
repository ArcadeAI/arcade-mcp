from dataclasses import dataclass
from typing import Optional

import httpx

from arcade_hubspot.constants import HUBSPOT_CRM_BASE_URL, HUBSPOT_DEFAULT_API_VERSION
from arcade_hubspot.enums import HubspotObject
from arcade_hubspot.exceptions import HubspotToolExecutionError, NotFoundError
from arcade_hubspot.utils import clean_data, prepare_api_search_response


@dataclass
class HubspotCrmClient:
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
            params["after"] = after

        response = await self.get(endpoint, params=params, api_version="v4")

        if not response["results"]:
            return []

        return await self.batch_get_objects(
            associated_object,
            [object_data["toObjectId"] for object_data in response["results"]],
            properties,
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
        data = {"inputs": [{"id": object_id} for object_id in object_ids]}
        if properties:
            data["properties"] = properties
        response = await self.post(endpoint, json_data=data)
        return [clean_data(object_data, object_type) for object_data in response["results"]]

    async def get_company_contacts(
        self,
        company_id: str,
        limit: int = 10,
        after: Optional[str] = None,
    ) -> dict:
        return await self.get_associated_objects(
            parent_object=HubspotObject.COMPANY,
            parent_id=company_id,
            associated_object=HubspotObject.CONTACT,
            limit=limit,
            after=after,
            properties=[
                "salutation",
                "email",
                "work_email",
                "hs_additional_emails",
                "mobilephone",
                "phone",
                "firstname",
                "lastname",
                "lifecyclestage",
                "annualrevenue",
                "address",
                "date_of_birth",
                "degree",
                "gender",
                "buying_role",
                "hs_language",
                "hs_lead_status",
                "hs_timezone",
                "hubspot_owner_id",
                "hubspot_owner_name",
                "job_function",
                "jobtitle",
                "seniority",
                "industry",
                "twitterhandle",
            ],
        )

    async def get_company_deals(
        self,
        company_id: str,
        limit: int = 10,
        after: Optional[str] = None,
    ) -> dict:
        return await self.get_associated_objects(
            parent_object=HubspotObject.COMPANY,
            parent_id=company_id,
            associated_object=HubspotObject.DEAL,
            limit=limit,
            after=after,
            properties=[
                "dealname",
                "dealstage",
                "dealtype",
                "closedate",
                "closed_lost_reason",
                "closed_won_reason",
                "hs_is_closed_won",
                "hs_is_closed_lost",
                "hs_closed_amount",
                "pipeline",
                "hubspot_owner_id",
                "description",
                "hs_deal_score",
                "amount",
                "hs_forecast_probability",
                "hs_forecast_amount",
            ],
        )

    async def get_company_calls(
        self,
        company_id: str,
        limit: int = 10,
        after: Optional[str] = None,
    ) -> dict:
        return await self.get_associated_objects(
            parent_object=HubspotObject.COMPANY,
            parent_id=company_id,
            associated_object=HubspotObject.CALL,
            limit=limit,
            after=after,
            properties=[
                "hs_body_preview",
                "hs_call_direction",
                "hs_call_status",
                "hs_call_summary",
                "hs_call_title",
                "hs_createdate",
                "hubspot_owner_id",
                "hs_call_disposition",
                "hs_timestamp",
            ],
        )

    async def get_company_emails(
        self,
        company_id: str,
        limit: int = 10,
        after: Optional[str] = None,
    ) -> dict:
        return await self.get_associated_objects(
            parent_object=HubspotObject.COMPANY,
            parent_id=company_id,
            associated_object=HubspotObject.EMAIL,
            limit=limit,
            after=after,
            properties=[
                "hs_object_id",
                "hs_body_preview",
                "hs_email_sender_raw",
                "hs_email_from_raw",
                "hs_email_to_raw",
                "hs_email_bcc_raw",
                "hs_email_cc_raw",
                "hs_email_subject",
                "hs_email_status",
                "hs_timestamp",
                "hubspot_owner_id",
                "hs_email_associated_contact_id",
            ],
        )

    async def get_company_notes(
        self,
        company_id: str,
        limit: int = 10,
        after: Optional[str] = None,
    ) -> dict:
        return await self.get_associated_objects(
            parent_object=HubspotObject.COMPANY,
            parent_id=company_id,
            associated_object=HubspotObject.NOTE,
            limit=limit,
            after=after,
            properties=[
                "hs_object_id",
                "hs_meeting_body",
                "hs_timestamp",
                "hubspot_owner_id",
            ],
        )

    async def get_company_meetings(
        self,
        company_id: str,
        limit: int = 10,
        after: Optional[str] = None,
    ) -> dict:
        return await self.get_associated_objects(
            parent_object=HubspotObject.COMPANY,
            parent_id=company_id,
            associated_object=HubspotObject.MEETING,
            limit=limit,
            after=after,
            properties=[
                "hs_object_id",
                "hs_meeting_title",
                "hs_body_preview",
                "hs_meeting_location",
                "hs_meeting_outcome",
                "hubspot_owner_id",
                "hs_meeting_start_time",
                "hs_meeting_end_time",
            ],
        )

    async def get_company_tasks(
        self,
        company_id: str,
        limit: int = 10,
        after: Optional[str] = None,
    ) -> dict:
        return await self.get_associated_objects(
            parent_object=HubspotObject.COMPANY,
            parent_id=company_id,
            associated_object=HubspotObject.TASK,
            limit=limit,
            after=after,
            properties=[
                "hs_object_id",
                "hs_body_preview",
                "hs_timestamp",
                "hubspot_owner_id",
                "hs_associated_contact_labels",
                "hs_task_is_overdue",
                "hs_task_priority",
                "hs_task_status",
                "hs_task_subject",
                "hs_task_type",
            ],
        )

    async def search_company_by_keywords(
        self,
        keywords: str,
        limit: int = 10,
        next_page_token: Optional[str] = None,
    ) -> dict:
        endpoint = f"objects/{HubspotObject.COMPANY.plural}/search"
        request_data = {
            "query": keywords,
            "limit": limit,
            "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}],
            "properties": [
                "type",
                "name",
                "about_us",
                "address",
                "city",
                "state",
                "zip",
                "country",
                "annualrevenue",
                "hs_annual_revenue_currency_code",
                "industry",
                "phone",
                "website",
                "domain",
                "numberofemployees",
                "hs_lead_status",
                "lifecyclestage",
                "linkedin_company_page",
                "twitterhandle",
            ],
        }

        if next_page_token:
            request_data["after"] = next_page_token

        data = prepare_api_search_response(
            data=await self.post(endpoint, json_data=request_data),
            object_type=HubspotObject.COMPANY,
        )

        for company in data[HubspotObject.COMPANY.plural]:
            associated = {
                "calls": await self.get_company_calls(company["id"], limit=10),
                "contacts": await self.get_company_contacts(company["id"], limit=10),
                "deals": await self.get_company_deals(company["id"], limit=10),
                "emails": await self.get_company_emails(company["id"], limit=10),
                "meetings": await self.get_company_meetings(company["id"], limit=10),
                "notes": await self.get_company_notes(company["id"], limit=10),
                "tasks": await self.get_company_tasks(company["id"], limit=10),
            }
            for key, value in associated.items():
                if value:
                    company[key] = value

        return data
