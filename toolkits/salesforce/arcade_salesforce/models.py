import asyncio
import os
from dataclasses import dataclass
from typing import Any, cast

import httpx

from arcade_salesforce.constants import MAX_CONCURRENT_REQUESTS, SALESFORCE_API_VERSION
from arcade_salesforce.enums import SalesforceObject
from arcade_salesforce.exceptions import (
    BadRequestError,
    ResourceNotFoundError,
    SalesforceToolExecutionError,
)
from arcade_salesforce.utils import (
    build_soql_query,
    clean_contact_data,
    clean_lead_data,
    clean_note_data,
    clean_object_data,
    clean_opportunity_data,
    clean_task_data,
    expand_associations,
    get_ids_referenced,
    get_object_type,
    remove_none_values,
)


@dataclass
class SalesforceClient:
    auth_token: str
    org_subdomain: str | None = None
    api_version: str = SALESFORCE_API_VERSION
    max_concurrent_requests: int = MAX_CONCURRENT_REQUESTS

    # Internal state properties
    _state_object_fields: dict[SalesforceObject, list[str]] | None = None
    _state_is_person_account_enabled: bool | None = None
    _semaphore: asyncio.Semaphore | None = None

    def __post_init__(self) -> None:
        if self.org_subdomain is None:
            self.org_subdomain = os.getenv("SALESFORCE_ORG_SUBDOMAIN")
        if self.org_subdomain is None:
            raise ValueError(
                "Either `org_subdomain` argument or `SALESFORCE_ORG_SUBDOMAIN` env var must be set"
            )

        if self._state_object_fields is None:
            self._state_object_fields = {}

        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)

    @property
    def _base_url(self) -> str:
        return f"https://{self.org_subdomain}.my.salesforce.com/services/data/{self.api_version}"

    @property
    def object_fields(self) -> dict[SalesforceObject, list[str]]:
        return cast(dict, self._state_object_fields)

    def _endpoint_url(self, endpoint: str) -> str:
        return f"{self._base_url}/{endpoint.lstrip('/')}"

    def _build_headers(self, headers: dict | None = None) -> dict:
        headers = headers or {}
        headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _raise_salesforce_error(self, response: httpx.Response) -> None:
        """Raise a ToolExecutionError based on the Salesforce API response status code."""
        errors = [error.get("message") for error in response.json()]
        if response.status_code == 404:
            raise ResourceNotFoundError(errors)
        elif response.status_code == 400:
            raise BadRequestError(errors)
        raise SalesforceToolExecutionError(errors)

    async def get(
        self,
        endpoint: str,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        """Make a GET request to the Salesforce API.

        Args:
            endpoint: The Salesforce API endpoint to call.
            params: The query parameters to include in the request.
            headers: The headers to include in the request.

        Returns:
            The JSON-loaded representation of the response from the Salesforce API.
        """
        kwargs: dict[str, Any] = {
            "url": self._endpoint_url(endpoint),
            "headers": self._build_headers(headers),
        }
        if params:
            kwargs["params"] = params

        async with self._semaphore, httpx.AsyncClient() as client:  # type: ignore[union-attr]
            response = await client.get(**kwargs)

        if response.status_code >= 300:
            self._raise_salesforce_error(response)

        return cast(dict, response.json())

    async def post(
        self,
        endpoint: str,
        data: dict | None = None,
        json_data: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        """Make a POST request to the Salesforce API.

        Args:
            endpoint: The Salesforce API endpoint to call.
            data: The data for the request. (provide data or json_data, not both)
            json_data: The JSON data for the request. (provide data or json_data, not both)
            headers: The headers to include in the request.

        Returns:
            The JSON-loaded representation of the response from the Salesforce API.
        """
        kwargs: dict[str, Any] = {
            "url": self._endpoint_url(endpoint),
            "headers": self._build_headers(headers),
        }
        if data:
            kwargs["data"] = data
        if json_data:
            kwargs["json"] = json_data

        async with self._semaphore, httpx.AsyncClient() as client:  # type: ignore[union-attr]
            response = await client.post(**kwargs)

        if response.status_code >= 300:
            self._raise_salesforce_error(response)

        return cast(dict, response.json())

    async def get_object_fields(self, object_type: SalesforceObject) -> list[str]:
        """Get the fields available for a Salesforce object.

        Args:
            object_type: The Salesforce object to get the fields for.

        Returns:
            The list of fields available for a Salesforce object.
        """
        if object_type not in self.object_fields:
            response = await self._describe_object(object_type)
            self.object_fields[object_type] = [field["name"] for field in response["fields"]]

        return self.object_fields[object_type]

    async def _describe_object(self, object_type: SalesforceObject) -> dict:
        return await self.get(f"sobjects/{object_type.value}/describe/")

    async def _get_related_objects(
        self,
        child_object_type: SalesforceObject,
        parent_object_type: SalesforceObject,
        parent_object_id: str,
        limit: int | None = 10,
    ) -> list[dict]:
        """Get the objects that are associated with another Salesforce object.

        Args:
            child_object_type: The type of child object to retrieve.
            parent_object_type: The type of parent object.
            parent_object_id: The ID of the parent object.
            limit: The maximum number of related objects to retrieve.

        Returns:
            The list of related objects.
        """
        try:
            response = await self.get(
                f"sobjects/{parent_object_type.value}/{parent_object_id}/{child_object_type.plural.lower()}",
                params={"limit": limit},
            )
            return cast(list, response["records"])
        except ResourceNotFoundError:
            return []

    async def get_object_by_id(self, object_id: str) -> dict | None:
        """Get a Salesforce object by its ID.

        Args:
            object_id: The ID of the Salesforce object to retrieve.

        Returns:
            The Salesforce object.
        """
        try:
            response = await self.get(f"sobjects/{object_id}")
            return clean_object_data(response)
        except ResourceNotFoundError:
            if "User" not in object_id:
                return await self.get_object_by_id(f"User/{object_id}")
            return None

    async def get_account(self, account_id: str) -> dict[str, Any] | None:
        """Get an account by its ID.

        Args:
            account_id: The ID of the account to retrieve.

        Returns:
            The account.
        """
        try:
            return cast(dict, await self.get(f"sobjects/Account/{account_id}"))
        except ResourceNotFoundError:
            return None

    async def get_account_contacts(self, account_id: str, limit: int | None = 10) -> list[dict]:
        """Get the contacts associated with an account.

        Args:
            account_id: The ID of the account to retrieve the contacts for.
            limit: The maximum number of contacts to retrieve.

        Returns:
            The list of contacts with cleaned and standardized dictionaries.
        """
        contacts = await self._get_related_objects(
            SalesforceObject.CONTACT, SalesforceObject.ACCOUNT, account_id, limit
        )

        return [
            clean_contact_data(contact)
            for contact in await asyncio.gather(*[
                self.enrich_contact_with_notes(contact, limit) for contact in contacts
            ])
        ]

    async def enrich_contact_with_notes(self, contact: dict, limit: int | None = 10) -> dict:
        """Get the notes associated with a contact and add to the contact dictionary.

        Args:
            contact: The contact to retrieve the notes for.
            limit: The maximum number of notes to retrieve.

        Returns:
            The contact with the notes added to the dictionary in the key `Notes`.
        """
        notes = await self.get_notes(contact["Id"], limit)
        if notes:
            contact["Notes"] = notes
        return contact

    async def get_account_leads(self, account_id: str, limit: int | None = 10) -> list[dict]:
        """Get the leads associated with an account.

        Args:
            account_id: The ID of the account to retrieve the leads for.
            limit: The maximum number of leads to retrieve.

        Returns:
            The list of leads with cleaned and standardized dictionaries.
        """
        leads = await self._get_related_objects(
            SalesforceObject.LEAD, SalesforceObject.ACCOUNT, account_id, limit
        )
        return [clean_lead_data(lead) for lead in leads]

    async def get_notes(self, parent_id: str, limit: int | None = 10) -> list[dict]:
        """Get the notes associated with a Salesforce object.

        Args:
            parent_id: The ID of the Salesforce object to retrieve the notes for.
            limit: The maximum number of notes to retrieve.

        Returns:
            The list of notes with cleaned and standardized dictionaries.
        """
        query = build_soql_query(
            "SELECT Id, Title, Body, OwnerId, CreatedById, CreatedDate "
            "FROM Note "
            "WHERE ParentId = '{parent_id}' "
            "LIMIT {limit}",
            parent_id=parent_id,
            limit=limit,
        )
        response = await self.get("query", params={"q": query})
        notes = response["records"]
        return [clean_note_data(note) for note in notes]

    # TODO: Add support for retrieving Currency, when enabled in the org account.
    # If not enabled and we try to retrieve it, we get a 400 error.
    # More inf: https://developer.salesforce.com/docs/atlas.en-us.254.0.object_reference.meta/object_reference/sforce_api_objects_opportunity.htm#i1455437
    async def get_account_opportunities(
        self,
        account_id: str,
        limit: int | None = 10,
    ) -> list[dict]:
        """Get the opportunities associated with an account.

        Args:
            account_id: The ID of the account to retrieve the opportunities for.
            limit: The maximum number of opportunities to retrieve.

        Returns:
            The list of opportunities with cleaned and standardized dictionaries.
        """
        query = build_soql_query(
            "SELECT Id, Name, Type, StageName, OwnerId, CreatedById, LastModifiedById, "
            "Description, Amount, Probability, ExpectedRevenue, CloseDate, ContactId "
            "FROM Opportunity "
            "WHERE AccountId = '{account_id}' "
            "LIMIT {limit}",
            account_id=account_id,
            limit=limit,
        )
        response = await self.get("query", params={"q": query})
        opportunities = response["records"]
        return [clean_opportunity_data(opportunity) for opportunity in opportunities]

    async def get_account_tasks(
        self,
        account_id: str,
        limit: int | None = 10,
    ) -> list[dict]:
        """Get the tasks associated with an account.

        Args:
            account_id: The ID of the account to retrieve the tasks for.
            limit: The maximum number of tasks to retrieve.

        Returns:
            The list of tasks with cleaned and standardized dictionaries.
        """
        tasks = await self._get_related_objects(
            SalesforceObject.TASK, SalesforceObject.ACCOUNT, account_id, limit
        )
        return [clean_task_data(task) for task in tasks]

    async def enrich_account(
        self,
        account_id: str | None = None,
        account_data: dict[str, Any] | None = None,
        limit_per_association: int | None = 10,
    ) -> dict:
        """Enrich account dictionary with contacts, leads, opportunities, and tasks.

        Provide `account_id` or `account_data`, but not both.

        Args:
            account_id: The ID of the account to retrieve the associations for.
            account_data: The account data to enrich.
            limit_per_association: The maximum number of associations to retrieve.

        Returns:
            The account with the associations added to the dictionary.
        """
        if (account_id and account_data) or (not account_id and not account_data):
            raise ValueError("Must provide exactly one of `account_id` or `account_data`")

        if account_data is None:
            account_data = await self.get_account(cast(str, account_id))

            if not account_data:
                raise ResourceNotFoundError([f"Account not found with ID: {account_id}"])

        if not account_id:
            account_id = cast(str, account_data["Id"])

        associations = await asyncio.gather(
            self.get_account_contacts(account_id, limit=limit_per_association),
            self.get_account_leads(account_id, limit=limit_per_association),
            self.get_account_opportunities(account_id, limit=limit_per_association),
            self.get_account_tasks(account_id, limit=limit_per_association),
        )

        for association in associations:
            for item in association:
                try:
                    obj_type = SalesforceObject(get_object_type(item)).plural
                except ValueError:
                    obj_type = get_object_type(item) + "s"

                if obj_type not in account_data:
                    account_data[obj_type] = []
                account_data[obj_type].append(item)

        return await self.expand_account_associations(account_data)

    async def expand_account_associations(self, account: dict) -> dict:
        """Expand with metadata about objects referenced by ID in an account dictionary.

        This method will, for example, expand an `OwnerId` or `ContactId` referenced in an account
        dictionary with the owner or contact name, for example.

        Args:
            account: The account dictionary to expand.

        Returns:
            The account with the associations expanded.
        """
        objects_by_id = {
            obj["Id"]: obj
            for obj_type in SalesforceObject
            for obj in account.get(obj_type.plural, [])
        }
        objects_by_id[account["Id"]] = account

        referenced_ids = get_ids_referenced(
            account,
            *[account.get(obj_type.plural, []) for obj_type in SalesforceObject],
        )

        missing_referenced_ids = [ref for ref in referenced_ids if ref not in objects_by_id]

        if missing_referenced_ids:
            missing_objects = await asyncio.gather(*[
                self.get_object_by_id(missing_id) for missing_id in missing_referenced_ids
            ])
            objects_by_id.update({obj["Id"]: obj for obj in missing_objects if obj is not None})

        account = expand_associations(account, objects_by_id)

        for object_type in SalesforceObject:
            if object_type.plural not in account:
                continue

            expanded_items = []

            for item in account[object_type.plural]:
                if "AccountId" in item:
                    del item["AccountId"]

                expanded_items.append(expand_associations(item, objects_by_id))

            if object_type == SalesforceObject.CONTACT:
                for contact in expanded_items:
                    if "Notes" in contact:
                        contact["Notes"] = [
                            expand_associations(note, objects_by_id) for note in contact["Notes"]
                        ]

            account[object_type.plural] = expanded_items

        return account

    async def create_contact(
        self,
        account_id: str,
        last_name: str,
        first_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        mobile_phone: str | None = None,
        title: str | None = None,
        department: str | None = None,
        description: str | None = None,
    ) -> dict:
        """Create a contact in Salesforce.

        Args:
            account_id: The ID of the account to associate the contact with.
            last_name: The last name of the contact.
            first_name: The first name of the contact.
            email: The email of the contact.
            phone: The phone number of the contact.
            mobile_phone: The mobile phone number of the contact.
            title: The title of the contact.
            department: The department of the contact.
            description: The description of the contact.

        Returns:
            The created contact.
        """
        data = {
            "AccountId": account_id,
            "FirstName": first_name,
            "LastName": last_name,
            "Email": email,
            "Phone": phone,
            "MobilePhone": mobile_phone,
            "Title": title,
            "Department": department,
            "Description": description,
        }

        return await self.post(
            f"sobjects/{SalesforceObject.CONTACT.value}",
            json_data=remove_none_values(data),
        )
