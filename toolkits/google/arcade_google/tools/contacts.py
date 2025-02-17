import asyncio
from typing import Annotated, Optional

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Google
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


@tool(requires_auth=Google(scopes=["https://www.googleapis.com/auth/contacts.readonly"]))
async def search_contacts(
    context: ToolContext,
    query: Annotated[
        str,
        "The search query for filtering contacts.",
    ],
    limit: Annotated[
        Optional[int],
        "The maximum number of contacts to return (default 10, max 30)",
    ] = 10,
) -> Annotated[dict, "A dictionary containing the list of matching contacts"]:
    """
    Search the user's contacts using the People API.

    This tool queries the contacts with the provided query string.
    The API returns contacts that match based on names, email addresses, and more.
    """
    # Build the People API service
    service = build(
        "people",
        "v1",
        credentials=Credentials(
            context.authorization.token
            if context.authorization and context.authorization.token
            else ""
        ),
    )

    # Warm-up the cache before performing search.
    # TODO: Ideally we should warmup only if this user (or google domain?) hasn't warmed up recently
    await _warmup_cache(service)

    # Search primary contacts using searchContacts
    primary_response = (
        service.people()
        .searchContacts(query=query, pageSize=limit, readMask="names,emailAddresses")
        .execute()
    )
    primary_results = primary_response.get("results", [])

    return {"contacts": primary_results}


async def _warmup_cache(service) -> None:  # type: ignore[no-untyped-def]
    """
    Warm-up the search cache for contacts by sending a request with an empty query.
    This ensures that the lazy cache is updated for both primary contacts and other contacts.
    This is a real thing: https://developers.google.com/people/v1/contacts#search_the_users_contacts
    """
    service.people().searchContacts(query="", pageSize=1, readMask="names,emailAddresses").execute()
    await asyncio.sleep(3)  # TODO experiment with this value


@tool(requires_auth=Google(scopes=["https://www.googleapis.com/auth/contacts"]))
async def create_contact(
    context: ToolContext,
    given_name: Annotated[str, "The given name of the contact"],
    family_name: Annotated[Optional[str], "The family name of the contact"],
    email: Annotated[Optional[str], "The email address of the contact"],
) -> Annotated[dict, "A dictionary containing the details of the created contact"]:
    """
    Create a new contact in the user's Google Contacts using the People API.

    This tool creates a contact with the basic name fields.
    """
    # Build the People API service
    service = build(
        "people",
        "v1",
        credentials=Credentials(context.get_auth_token_or_empty()),
    )

    # Construct the person payload with the specified names
    name_body = {"givenName": given_name}
    if family_name:
        name_body["familyName"] = family_name
    contact_body = {"names": [name_body]}
    if email:
        contact_body["emailAddresses"] = [{"value": email, "type": "work"}]

    # Create the contact. The personFields parameter specifies what information
    # should be returned. Here, we return names and emailAddresses.
    created_contact = (
        service.people()
        .createContact(body=contact_body, personFields="names,emailAddresses")
        .execute()
    )

    return {"contact": created_contact}
