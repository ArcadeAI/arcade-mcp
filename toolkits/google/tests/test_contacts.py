from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arcade.sdk import ToolContext

from arcade_google.tools.contacts import create_contact, search_contacts


@pytest.fixture
def mock_context():
    context = AsyncMock(spec=ToolContext)
    context.authorization = MagicMock()
    context.authorization.token = "mock_token"  # noqa: S105
    return context


@pytest.mark.asyncio
async def test_search_contacts_success(mock_context):
    search_response_data = {
        "results": [
            {
                "resourceName": "people/1",
                "names": [{"displayName": "John Doe"}],
                "emailAddresses": [{"value": "john@example.com"}],
            },
            {
                "resourceName": "people/2",
                "names": [{"displayName": "Jane Doe"}],
                "emailAddresses": [{"value": "jane@example.com"}],
            },
        ]
    }
    search_call = MagicMock()
    search_call.execute.return_value = search_response_data

    people_mock = MagicMock()
    people_mock.searchContacts.return_value = search_call

    service_mock = MagicMock()
    service_mock.people.return_value = people_mock

    with (
        patch("arcade_google.tools.contacts.build", return_value=service_mock) as mock_build,
        patch(
            "arcade_google.tools.contacts._warmup_cache", new=AsyncMock(return_value=None)
        ) as mock_warmup,
    ):
        result = await search_contacts(mock_context, query="Doe", limit=2)
        assert "contacts" in result
        assert result["contacts"] == search_response_data["results"]

        assert mock_warmup.call_count == 1
        assert people_mock.searchContacts.call_count == 1

        # Check that the People API service was built with the expected parameters.
        mock_build.assert_called_once()


@pytest.mark.asyncio
async def test_search_contacts_error(mock_context):
    error_call = MagicMock()
    error_call.execute.side_effect = Exception("Search error")

    people_mock = MagicMock()
    people_mock.searchContacts.return_value = error_call

    service_mock = MagicMock()
    service_mock.people.return_value = people_mock

    with (
        patch("arcade_google.tools.contacts.build", return_value=service_mock),
        patch("arcade_google.tools.contacts._warmup_cache", new=AsyncMock(return_value=None)),
        pytest.raises(Exception, match="Error in execution of SearchContacts"),
    ):
        await search_contacts(mock_context, query="Doe")


@pytest.mark.asyncio
async def test_create_contact_success(mock_context):
    # Test create_contact with all parameters (given, family names and email)
    created_contact_data = {"resourceName": "people/123", "etag": "abc"}

    create_contact_call = MagicMock()
    create_contact_call.execute.return_value = created_contact_data

    people_mock = MagicMock()
    people_mock.createContact.return_value = create_contact_call

    service_mock = MagicMock()
    service_mock.people.return_value = people_mock

    with patch("arcade_google.tools.contacts.build", return_value=service_mock) as mock_build:
        result = await create_contact(
            mock_context,
            given_name="Alice",
            family_name="Smith",
            email="alice@example.com",
        )
        assert "contact" in result
        assert result["contact"] == created_contact_data

        # Verify that the createContact API was called with the correct body contents.
        expected_body = {
            "names": [{"givenName": "Alice", "familyName": "Smith"}],
            "emailAddresses": [{"value": "alice@example.com", "type": "work"}],
        }
        people_mock.createContact.assert_called_once_with(
            body=expected_body, personFields="names,emailAddresses"
        )
        mock_build.assert_called_once()


@pytest.mark.asyncio
async def test_create_contact_success_without_optional(mock_context):
    # Test create_contact without optional parameters family_name and email.
    created_contact_data = {"resourceName": "people/456", "etag": "def"}

    create_contact_call = MagicMock()
    create_contact_call.execute.return_value = created_contact_data

    people_mock = MagicMock()
    people_mock.createContact.return_value = create_contact_call

    service_mock = MagicMock()
    service_mock.people.return_value = people_mock

    with patch("arcade_google.tools.contacts.build", return_value=service_mock):
        result = await create_contact(mock_context, given_name="Bob", family_name=None, email=None)
        assert "contact" in result
        assert result["contact"] == created_contact_data

        # Expected body should only include the givenName when family_name and email are omitted.
        expected_body = {"names": [{"givenName": "Bob"}]}
        people_mock.createContact.assert_called_once_with(
            body=expected_body, personFields="names,emailAddresses"
        )


@pytest.mark.asyncio
async def test_create_contact_error(mock_context):
    # Simulate an error thrown by createContact
    error_call = MagicMock()
    error_call.execute.side_effect = Exception("Create error")

    people_mock = MagicMock()
    people_mock.createContact.return_value = error_call

    service_mock = MagicMock()
    service_mock.people.return_value = people_mock

    with (
        patch("arcade_google.tools.contacts.build", return_value=service_mock),
        pytest.raises(Exception, match="Error in execution of CreateContact"),
    ):
        await create_contact(mock_context, given_name="Alice", family_name="Doe", email=None)
