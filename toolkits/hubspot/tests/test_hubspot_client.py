from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest

from arcade_hubspot.enums import HubspotObject
from arcade_hubspot.exceptions import HubspotToolExecutionError, NotFoundError
from arcade_hubspot.models import HubspotCrmClient


@pytest.mark.asyncio
async def test_get_success(mock_context, mock_httpx_client):
    client = HubspotCrmClient(mock_context.get_auth_token_or_empty())

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": []}
    mock_httpx_client.get.return_value = mock_response

    response = await client.get("objects/contacts", params={"id": "123"})

    assert response == {"data": []}
    mock_httpx_client.get.assert_called_once_with(
        url="https://api.hubapi.com/crm/v3/objects/contacts",
        params={"id": "123"},
        headers={"Authorization": f"Bearer {mock_context.get_auth_token_or_empty()}"},
    )


@pytest.mark.asyncio
async def test_get_not_found_error(mock_context, mock_httpx_client):
    client = HubspotCrmClient(mock_context.get_auth_token_or_empty())

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.json.return_value = {"message": "Not Found", "errors": [{"message": "Not Found"}]}
    mock_httpx_client.get.return_value = mock_response

    with pytest.raises(NotFoundError) as exc_info:
        await client.get("objects/contacts", params={"id": "123"})

    assert exc_info.value.message == "Not Found"
    assert exc_info.value.developer_message == '[{"message": "Not Found"}]'


@pytest.mark.asyncio
async def test_get_internal_server_error(mock_context, mock_httpx_client):
    client = HubspotCrmClient(mock_context.get_auth_token_or_empty())

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.json.return_value = {
        "message": "Internal Server Error",
        "errors": [{"message": "Internal Server Error"}],
    }
    mock_httpx_client.get.return_value = mock_response

    with pytest.raises(HubspotToolExecutionError) as exc_info:
        await client.get("objects/contacts", params={"id": "123"})

    assert exc_info.value.message == "Internal Server Error"
    assert exc_info.value.developer_message == '[{"message": "Internal Server Error"}]'


@pytest.mark.asyncio
async def test_get_with_invalid_json_error_response(mock_context, mock_httpx_client):
    client = HubspotCrmClient(mock_context.get_auth_token_or_empty())

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.text = "Text error message"
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_httpx_client.get.return_value = mock_response

    with pytest.raises(HubspotToolExecutionError) as exc_info:
        await client.get("objects/contacts", params={"id": "123"})

    assert exc_info.value.message == "Text error message"
    assert exc_info.value.developer_message is None


@pytest.mark.asyncio
async def test_post_success(mock_context, mock_httpx_client):
    client = HubspotCrmClient(mock_context.get_auth_token_or_empty())

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": []}
    mock_httpx_client.post.return_value = mock_response

    response = await client.post("objects/contacts", json_data={"id": "123"})

    assert response == {"data": []}
    mock_httpx_client.post.assert_called_once_with(
        url="https://api.hubapi.com/crm/v3/objects/contacts",
        json={"id": "123"},
        headers={
            "Authorization": f"Bearer {mock_context.get_auth_token_or_empty()}",
            "Content-Type": "application/json",
        },
    )


@pytest.mark.asyncio
async def test_post_not_found_error(mock_context, mock_httpx_client):
    client = HubspotCrmClient(mock_context.get_auth_token_or_empty())

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.json.return_value = {"message": "Not Found", "errors": [{"message": "Not Found"}]}
    mock_httpx_client.post.return_value = mock_response

    with pytest.raises(NotFoundError) as exc_info:
        await client.post("objects/contacts", json_data={"id": "123"})

    assert exc_info.value.message == "Not Found"
    assert exc_info.value.developer_message == '[{"message": "Not Found"}]'


@pytest.mark.asyncio
async def test_post_internal_server_error(mock_context, mock_httpx_client):
    client = HubspotCrmClient(mock_context.get_auth_token_or_empty())

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.json.return_value = {
        "message": "Internal Server Error",
        "errors": [{"message": "Internal Server Error"}],
    }
    mock_httpx_client.post.return_value = mock_response

    with pytest.raises(HubspotToolExecutionError) as exc_info:
        await client.post("objects/contacts", json_data={"id": "123"})

    assert exc_info.value.message == "Internal Server Error"
    assert exc_info.value.developer_message == '[{"message": "Internal Server Error"}]'


@pytest.mark.asyncio
@patch("arcade_hubspot.models.clean_data")
async def test_batch_get_objects(mock_clean_data, mock_context, mock_httpx_client):
    mock_results = [MagicMock(spec=dict) for _ in range(3)]

    clean_data_response = [MagicMock(spec=dict) for _ in range(3)]
    mock_clean_data.side_effect = clean_data_response

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": mock_results,
    }
    mock_httpx_client.post.return_value = mock_response

    client = HubspotCrmClient(mock_context.get_auth_token_or_empty())
    response = await client.batch_get_objects(
        HubspotObject.CONTACT, ["123", "456"], ["email", "firstname"]
    )

    assert response == clean_data_response
    mock_clean_data.assert_has_calls([
        call(result, HubspotObject.CONTACT) for result in mock_results
    ])

    mock_httpx_client.post.assert_called_once_with(
        url="https://api.hubapi.com/crm/v3/objects/contacts/batch/read",
        json={
            "inputs": [{"id": "123"}, {"id": "456"}],
            "properties": ["email", "firstname"],
        },
        headers={
            "Authorization": f"Bearer {mock_context.get_auth_token_or_empty()}",
            "Content-Type": "application/json",
        },
    )


@pytest.mark.asyncio
@patch("arcade_hubspot.models.clean_data")
async def test_get_associated_objects(mock_clean_data, mock_context, mock_httpx_client):
    # Mock stuff from the batch_get_objects function
    mock_batch_results = [MagicMock(spec=dict) for _ in range(3)]
    clean_data_response = [MagicMock(spec=dict) for _ in range(3)]
    mock_clean_data.side_effect = clean_data_response
    mock_post_response = MagicMock(spec=httpx.Response)
    mock_post_response.status_code = 200
    mock_post_response.json.return_value = {
        "results": mock_batch_results,
    }
    mock_httpx_client.post.return_value = mock_post_response

    # Mock stuff from the get_associated_objects function
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [{"toObjectId": "123"}, {"toObjectId": "456"}],
    }
    mock_httpx_client.get.return_value = mock_response

    client = HubspotCrmClient(mock_context.get_auth_token_or_empty())
    response = await client.get_associated_objects(
        parent_object=HubspotObject.COMPANY,
        parent_id="parent_id",
        associated_object=HubspotObject.CONTACT,
        limit=5,
        after=5,
        properties=["email", "firstname"],
    )

    assert response == clean_data_response
    mock_clean_data.assert_has_calls([
        call(result, HubspotObject.CONTACT) for result in mock_batch_results
    ])

    mock_httpx_client.get.assert_called_once_with(
        url="https://api.hubapi.com/crm/v4/objects/company/parent_id/associations/contact",
        params={
            "limit": 5,
            "after": 5,
        },
        headers={
            "Authorization": f"Bearer {mock_context.get_auth_token_or_empty()}",
        },
    )

    mock_httpx_client.post.assert_called_once_with(
        url="https://api.hubapi.com/crm/v3/objects/contacts/batch/read",
        json={
            "inputs": [{"id": "123"}, {"id": "456"}],
            "properties": ["email", "firstname"],
        },
        headers={
            "Authorization": f"Bearer {mock_context.get_auth_token_or_empty()}",
            "Content-Type": "application/json",
        },
    )


@pytest.mark.asyncio
@patch("arcade_hubspot.models.prepare_api_search_response")
@patch("arcade_hubspot.models.get_object_properties")
async def test_search_by_keywords(
    mock_get_object_properties,
    mock_prepare_api_search_response,
    mock_context,
    mock_httpx_client,
):
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_httpx_client.post.return_value = mock_response

    mock_prepared_api_response = {
        "contacts": [
            {
                "id": "123",
                "first_name": "Jason",
                "last_name": "Bourne",
                "email": "jason.bourne@acme.com",
            }
        ]
    }
    mock_prepare_api_search_response.return_value = mock_prepared_api_response
    mock_get_object_properties.return_value = ["email", "firstname"]

    mock_calls = [{"id": f"call_{i}"} for i in range(3)]
    mock_emails = [{"id": f"email_{i}"} for i in range(3)]
    mock_notes = [{"id": f"note_{i}"} for i in range(3)]

    mock_get_associated_objects = AsyncMock()
    mock_get_associated_objects.side_effect = [mock_calls, mock_emails, mock_notes]

    client = HubspotCrmClient(mock_context.get_auth_token_or_empty())
    client.get_associated_objects = mock_get_associated_objects

    response = await client.search_by_keywords(
        object_type=HubspotObject.CONTACT,
        keywords="test",
        limit=10,
        associations=[
            HubspotObject.CALL,
            HubspotObject.EMAIL,
            HubspotObject.NOTE,
        ],
    )

    expected_response = deepcopy(mock_prepared_api_response)
    expected_response["contacts"][0]["calls"] = mock_calls
    expected_response["contacts"][0]["emails"] = mock_emails
    expected_response["contacts"][0]["notes"] = mock_notes

    assert response == expected_response

    mock_httpx_client.post.assert_called_once_with(
        url="https://api.hubapi.com/crm/v3/objects/contacts/search",
        headers={
            "Authorization": f"Bearer {mock_context.get_auth_token_or_empty()}",
            "Content-Type": "application/json",
        },
        json={
            "query": "test",
            "limit": 10,
            "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}],
            "properties": ["email", "firstname"],
        },
    )

    mock_get_associated_objects.assert_has_calls([
        call(
            parent_object=HubspotObject.CONTACT,
            parent_id="123",
            associated_object=HubspotObject.CALL,
            limit=10,
        ),
        call(
            parent_object=HubspotObject.CONTACT,
            parent_id="123",
            associated_object=HubspotObject.EMAIL,
            limit=10,
        ),
        call(
            parent_object=HubspotObject.CONTACT,
            parent_id="123",
            associated_object=HubspotObject.NOTE,
            limit=10,
        ),
    ])
