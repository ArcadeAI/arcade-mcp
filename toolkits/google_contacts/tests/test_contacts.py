"""Tests for Google Contacts tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arcade_tdk import ToolContext

from arcade_google_contacts.tools.contacts import (
    create_contact,
    get_contact,
    list_contacts,
    update_contact,
)


@pytest.fixture
def mock_context():
    """Create a mock ToolContext."""
    context = MagicMock(spec=ToolContext)
    context.get_google_oauth_credentials = MagicMock()
    return context


@pytest.fixture
def mock_service():
    """Create a mock Google People API service."""
    with patch("arcade_google_contacts.tools.contacts.build") as mock_build:
        service = MagicMock()
        mock_build.return_value = service
        yield service


@pytest.mark.asyncio
async def test_create_contact_with_phone_numbers(mock_context, mock_service):
    """Test creating a contact with phone numbers."""
    # Setup mock response
    expected_response = {
        "resourceName": "people/123456",
        "names": [{"givenName": "John", "familyName": "Doe"}],
        "phoneNumbers": [{"value": "+1234567890", "type": "mobile"}],
        "emailAddresses": [{"value": "john@example.com", "type": "home"}],
    }
    mock_service.people().createContact().execute.return_value = expected_response

    # Call the tool
    result = await create_contact(
        context=mock_context,
        given_name="John",
        family_name="Doe",
        email_addresses=["john@example.com"],
        phone_numbers=["+1234567890"],
    )

    # Verify the result
    assert result == expected_response
    assert result["resourceName"] == "people/123456"

    # Verify the API was called with correct parameters
    mock_service.people().createContact.assert_called_once()
    call_kwargs = mock_service.people().createContact.call_args[1]
    body = call_kwargs["body"]

    # Verify phone numbers are included in the request
    assert "phoneNumbers" in body
    assert len(body["phoneNumbers"]) == 1
    assert body["phoneNumbers"][0]["value"] == "+1234567890"
    assert body["phoneNumbers"][0]["type"] == "mobile"


@pytest.mark.asyncio
async def test_create_contact_with_multiple_phone_numbers(mock_context, mock_service):
    """Test creating a contact with multiple phone numbers."""
    expected_response = {
        "resourceName": "people/123456",
        "names": [{"givenName": "Jane", "familyName": "Smith"}],
        "phoneNumbers": [
            {"value": "+1234567890", "type": "mobile"},
            {"value": "+0987654321", "type": "mobile"},
        ],
    }
    mock_service.people().createContact().execute.return_value = expected_response

    result = await create_contact(
        context=mock_context,
        given_name="Jane",
        family_name="Smith",
        phone_numbers=["+1234567890", "+0987654321"],
    )

    assert result == expected_response

    # Verify multiple phone numbers were sent
    call_kwargs = mock_service.people().createContact.call_args[1]
    body = call_kwargs["body"]
    assert len(body["phoneNumbers"]) == 2


@pytest.mark.asyncio
async def test_create_contact_with_all_fields(mock_context, mock_service):
    """Test creating a contact with all fields including phone numbers."""
    expected_response = {
        "resourceName": "people/123456",
        "names": [{"givenName": "Alice", "familyName": "Johnson"}],
        "phoneNumbers": [{"value": "+1555123456", "type": "mobile"}],
        "emailAddresses": [{"value": "alice@example.com", "type": "home"}],
        "organizations": [{"name": "Acme Corp", "title": "Engineer"}],
        "biographies": [{"value": "Test notes", "contentType": "TEXT_PLAIN"}],
    }
    mock_service.people().createContact().execute.return_value = expected_response

    result = await create_contact(
        context=mock_context,
        given_name="Alice",
        family_name="Johnson",
        email_addresses=["alice@example.com"],
        phone_numbers=["+1555123456"],
        organization="Acme Corp",
        job_title="Engineer",
        notes="Test notes",
    )

    assert result == expected_response

    # Verify all fields were sent
    call_kwargs = mock_service.people().createContact.call_args[1]
    body = call_kwargs["body"]
    assert "names" in body
    assert "phoneNumbers" in body
    assert "emailAddresses" in body
    assert "organizations" in body
    assert "biographies" in body


@pytest.mark.asyncio
async def test_create_contact_without_phone_numbers(mock_context, mock_service):
    """Test creating a contact without phone numbers (optional field)."""
    expected_response = {
        "resourceName": "people/123456",
        "names": [{"givenName": "Bob"}],
        "emailAddresses": [{"value": "bob@example.com", "type": "home"}],
    }
    mock_service.people().createContact().execute.return_value = expected_response

    result = await create_contact(
        context=mock_context,
        given_name="Bob",
        email_addresses=["bob@example.com"],
    )

    assert result == expected_response

    # Verify phone numbers are not in the request when not provided
    call_kwargs = mock_service.people().createContact.call_args[1]
    body = call_kwargs["body"]
    assert "phoneNumbers" not in body


@pytest.mark.asyncio
async def test_get_contact(mock_context, mock_service):
    """Test getting a contact."""
    expected_response = {
        "resourceName": "people/123456",
        "names": [{"givenName": "John", "familyName": "Doe"}],
        "phoneNumbers": [{"value": "+1234567890", "type": "mobile"}],
        "emailAddresses": [{"value": "john@example.com", "type": "home"}],
    }
    mock_service.people().get().execute.return_value = expected_response

    result = await get_contact(context=mock_context, resource_name="people/123456")

    assert result == expected_response
    mock_service.people().get.assert_called_once()


@pytest.mark.asyncio
async def test_list_contacts(mock_context, mock_service):
    """Test listing contacts."""
    expected_response = {
        "connections": [
            {
                "resourceName": "people/123456",
                "names": [{"givenName": "John"}],
                "phoneNumbers": [{"value": "+1234567890"}],
            },
            {
                "resourceName": "people/789012",
                "names": [{"givenName": "Jane"}],
                "phoneNumbers": [{"value": "+0987654321"}],
            },
        ],
        "nextPageToken": "token123",
    }
    mock_service.people().connections().list().execute.return_value = expected_response

    result = await list_contacts(context=mock_context, page_size=10)

    assert result == expected_response
    assert len(result["connections"]) == 2
    mock_service.people().connections().list.assert_called_once()


@pytest.mark.asyncio
async def test_update_contact_with_phone_numbers(mock_context, mock_service):
    """Test updating a contact with phone numbers."""
    existing_contact = {
        "resourceName": "people/123456",
        "etag": "etag123",
        "names": [{"givenName": "Old"}],
    }
    updated_contact = {
        "resourceName": "people/123456",
        "names": [{"givenName": "New"}],
        "phoneNumbers": [{"value": "+1111111111", "type": "mobile"}],
    }

    mock_service.people().get().execute.return_value = existing_contact
    mock_service.people().updateContact().execute.return_value = updated_contact

    result = await update_contact(
        context=mock_context,
        resource_name="people/123456",
        given_name="New",
        phone_numbers=["+1111111111"],
    )

    assert result == updated_contact

    # Verify update was called with phone numbers
    mock_service.people().updateContact.assert_called_once()
    call_kwargs = mock_service.people().updateContact.call_args[1]
    body = call_kwargs["body"]
    assert "phoneNumbers" in body
    assert body["phoneNumbers"][0]["value"] == "+1111111111"
