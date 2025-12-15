"""Google Contacts management tools."""

from typing import Annotated, Any, Optional

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Google
from arcade_tdk.providers.google import GoogleErrorAdapter


@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/contacts",
        ]
    ),
    error_adapters=[GoogleErrorAdapter()],
)
async def create_contact(
    context: ToolContext,
    given_name: Annotated[str, "The person's given name (first name)"],
    family_name: Annotated[Optional[str], "The person's family name (last name)"] = None,
    email_addresses: Annotated[
        Optional[list[str]], "List of email addresses for the contact"
    ] = None,
    phone_numbers: Annotated[
        Optional[list[str]], "List of phone numbers for the contact (e.g., '+1234567890')"
    ] = None,
    organization: Annotated[Optional[str], "The person's organization/company"] = None,
    job_title: Annotated[Optional[str], "The person's job title"] = None,
    notes: Annotated[Optional[str], "Notes about the contact"] = None,
) -> Annotated[dict[str, Any], "The created contact information including resource name"]:
    """
    Create a new contact in Google Contacts with comprehensive information.
    
    This tool creates a contact with the provided information including names,
    email addresses, phone numbers, organization details, and notes.
    Phone numbers should be in E.164 format (e.g., '+14155552671') for best results.
    """
    from googleapiclient.discovery import build

    # Build the People API service
    credentials = context.get_google_oauth_credentials()
    service = build("people", "v1", credentials=credentials)

    # Build the person resource
    person_resource: dict[str, Any] = {}

    # Add names
    names = []
    name_obj: dict[str, Any] = {}
    if given_name:
        name_obj["givenName"] = given_name
    if family_name:
        name_obj["familyName"] = family_name
    if name_obj:
        names.append(name_obj)
    if names:
        person_resource["names"] = names

    # Add email addresses
    if email_addresses:
        person_resource["emailAddresses"] = [
            {"value": email, "type": "home"} for email in email_addresses
        ]

    # Add phone numbers - THIS IS THE KEY FIX FOR THE BUG
    if phone_numbers:
        person_resource["phoneNumbers"] = [
            {"value": phone, "type": "mobile"} for phone in phone_numbers
        ]

    # Add organization
    if organization or job_title:
        org_obj: dict[str, Any] = {}
        if organization:
            org_obj["name"] = organization
        if job_title:
            org_obj["title"] = job_title
        person_resource["organizations"] = [org_obj]

    # Add notes (biography)
    if notes:
        person_resource["biographies"] = [{"value": notes, "contentType": "TEXT_PLAIN"}]

    # Create the contact
    result = (
        service.people()
        .createContact(body=person_resource, personFields="names,emailAddresses,phoneNumbers")
        .execute()
    )

    return result


@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/contacts.readonly",
        ]
    ),
    error_adapters=[GoogleErrorAdapter()],
)
async def get_contact(
    context: ToolContext,
    resource_name: Annotated[str, "The resource name of the contact (e.g., 'people/123456')"],
) -> Annotated[dict[str, Any], "The contact information"]:
    """
    Get a contact's information from Google Contacts.
    
    Retrieves comprehensive contact information including names, emails,
    phone numbers, and other details.
    """
    from googleapiclient.discovery import build

    credentials = context.get_google_oauth_credentials()
    service = build("people", "v1", credentials=credentials)

    result = (
        service.people()
        .get(
            resourceName=resource_name,
            personFields="names,emailAddresses,phoneNumbers,organizations,biographies",
        )
        .execute()
    )

    return result


@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/contacts.readonly",
        ]
    ),
    error_adapters=[GoogleErrorAdapter()],
)
async def list_contacts(
    context: ToolContext,
    page_size: Annotated[int, "Maximum number of contacts to return (1-1000)"] = 10,
    page_token: Annotated[Optional[str], "Token for pagination"] = None,
) -> Annotated[
    dict[str, Any], "List of contacts with names, emails, and phone numbers"
]:
    """
    List contacts from Google Contacts.
    
    Returns a paginated list of contacts including their names, email addresses,
    and phone numbers.
    """
    from googleapiclient.discovery import build

    credentials = context.get_google_oauth_credentials()
    service = build("people", "v1", credentials=credentials)

    # Ensure page_size is within valid range
    page_size = max(1, min(page_size, 1000))

    params: dict[str, Any] = {
        "resourceName": "people/me",
        "pageSize": page_size,
        "personFields": "names,emailAddresses,phoneNumbers",
    }
    if page_token:
        params["pageToken"] = page_token

    result = service.people().connections().list(**params).execute()

    return result


@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/contacts",
        ]
    ),
    error_adapters=[GoogleErrorAdapter()],
)
async def update_contact(
    context: ToolContext,
    resource_name: Annotated[str, "The resource name of the contact (e.g., 'people/123456')"],
    given_name: Annotated[Optional[str], "The person's given name (first name)"] = None,
    family_name: Annotated[Optional[str], "The person's family name (last name)"] = None,
    email_addresses: Annotated[
        Optional[list[str]], "List of email addresses (replaces existing)"
    ] = None,
    phone_numbers: Annotated[
        Optional[list[str]], "List of phone numbers (replaces existing)"
    ] = None,
    organization: Annotated[Optional[str], "The person's organization/company"] = None,
    job_title: Annotated[Optional[str], "The person's job title"] = None,
    notes: Annotated[Optional[str], "Notes about the contact"] = None,
) -> Annotated[dict[str, Any], "The updated contact information"]:
    """
    Update an existing contact in Google Contacts.
    
    Updates the specified fields of a contact. Only provided fields will be updated.
    Phone numbers and email addresses will replace existing values if provided.
    """
    from googleapiclient.discovery import build

    credentials = context.get_google_oauth_credentials()
    service = build("people", "v1", credentials=credentials)

    # First, get the existing contact to get the etag
    existing_contact = (
        service.people()
        .get(
            resourceName=resource_name,
            personFields="names,emailAddresses,phoneNumbers,organizations,biographies,metadata",
        )
        .execute()
    )

    # Build the update resource
    person_resource: dict[str, Any] = {"etag": existing_contact.get("etag")}
    update_mask = []

    # Update names
    if given_name is not None or family_name is not None:
        name_obj: dict[str, Any] = {}
        if given_name is not None:
            name_obj["givenName"] = given_name
        if family_name is not None:
            name_obj["familyName"] = family_name
        person_resource["names"] = [name_obj]
        update_mask.append("names")

    # Update email addresses
    if email_addresses is not None:
        person_resource["emailAddresses"] = [
            {"value": email, "type": "home"} for email in email_addresses
        ]
        update_mask.append("emailAddresses")

    # Update phone numbers
    if phone_numbers is not None:
        person_resource["phoneNumbers"] = [
            {"value": phone, "type": "mobile"} for phone in phone_numbers
        ]
        update_mask.append("phoneNumbers")

    # Update organization
    if organization is not None or job_title is not None:
        org_obj: dict[str, Any] = {}
        if organization is not None:
            org_obj["name"] = organization
        if job_title is not None:
            org_obj["title"] = job_title
        person_resource["organizations"] = [org_obj]
        update_mask.append("organizations")

    # Update notes
    if notes is not None:
        person_resource["biographies"] = [{"value": notes, "contentType": "TEXT_PLAIN"}]
        update_mask.append("biographies")

    # Perform the update
    result = (
        service.people()
        .updateContact(
            resourceName=resource_name,
            body=person_resource,
            updatePersonFields=",".join(update_mask),
            personFields="names,emailAddresses,phoneNumbers",
        )
        .execute()
    )

    return result
