from unittest.mock import MagicMock, patch

import httpx
import pytest

from arcade_salesforce.constants import SALESFORCE_API_VERSION
from arcade_salesforce.enums import SalesforceObject
from arcade_salesforce.exceptions import ResourceNotFoundError, SalesforceToolExecutionError
from arcade_salesforce.models import SalesforceClient


@pytest.mark.asyncio
async def test_get_account_success(mock_context, mock_httpx_client):
    account_id = "001gK000003DIn0QAG"
    account = {
        "attributes": {
            "type": "Account",
        },
        "Id": account_id,
        "Name": "Acme, Inc.",
    }

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = account
    mock_httpx_client.get.return_value = mock_response

    client = SalesforceClient(
        auth_token=mock_context.authorization.token,
        org_subdomain="org_domain",
    )
    response = await client.get_account(account_id)

    assert response == account

    mock_httpx_client.get.assert_called_once_with(
        url=f"https://org_domain.my.salesforce.com/services/data/{SALESFORCE_API_VERSION}/sobjects/Account/{account_id}",
        headers={"Authorization": f"Bearer {mock_context.authorization.token}"},
    )


@pytest.mark.asyncio
async def test_get_account_not_found_error(mock_context, mock_httpx_client):
    account_id = "001gK000003DIn0QAG"
    response_data = [{"message": "Account not found"}]

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.json.return_value = response_data
    mock_httpx_client.get.return_value = mock_response

    client = SalesforceClient(
        auth_token=mock_context.authorization.token,
        org_subdomain="org_domain",
    )
    response = await client.get_account(account_id)
    assert response is None


@pytest.mark.asyncio
async def test_get_account_bad_request_error(mock_context, mock_httpx_client):
    account_id = "001gK000003DIn0QAG"
    response_data = [{"message": "Bad request"}]

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 400
    mock_response.json.return_value = response_data
    mock_httpx_client.get.return_value = mock_response

    client = SalesforceClient(
        auth_token=mock_context.authorization.token,
        org_subdomain="org_domain",
    )
    with pytest.raises(SalesforceToolExecutionError) as exc_info:
        await client.get_account(account_id)
    assert exc_info.value.errors == ["Bad request"]


@pytest.mark.asyncio
async def test_get_account_internal_server_error(mock_context, mock_httpx_client):
    account_id = "001gK000003DIn0QAG"
    response_data = [{"message": "Internal server error"}]

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.json.return_value = response_data
    mock_httpx_client.get.return_value = mock_response

    client = SalesforceClient(
        auth_token=mock_context.authorization.token,
        org_subdomain="org_domain",
    )
    with pytest.raises(SalesforceToolExecutionError) as exc_info:
        await client.get_account(account_id)
    assert exc_info.value.errors == ["Internal server error"]


@pytest.mark.asyncio
async def test_create_contact(mock_context, mock_httpx_client):
    account_id = "001gK000003DIn0QAG"

    client = SalesforceClient(
        auth_token=mock_context.authorization.token,
        org_subdomain="org_domain",
    )

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_httpx_client.post.return_value = mock_response

    response = await client.create_contact(
        account_id=account_id,
        last_name="Doe",
        first_name="John",
        email="john.doe@acme.net",
    )

    assert response == mock_response.json.return_value

    mock_httpx_client.post.assert_called_once_with(
        url=f"https://org_domain.my.salesforce.com/services/data/{SALESFORCE_API_VERSION}/sobjects/Contact",
        headers={"Authorization": f"Bearer {mock_context.authorization.token}"},
        json={
            "AccountId": account_id,
            "FirstName": "John",
            "LastName": "Doe",
            "Email": "john.doe@acme.net",
        },
    )


@pytest.mark.asyncio
async def test_get_related_objects_success(mock_context, mock_httpx_client):
    client = SalesforceClient(
        auth_token=mock_context.authorization.token,
        org_subdomain="org_domain",
    )

    parent_object_id = "001gK000003DIn0QAG"
    parent_object = SalesforceObject.ACCOUNT
    child_object = SalesforceObject.CONTACT

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"records": []}
    mock_httpx_client.get.return_value = mock_response

    response = await client._get_related_objects(
        child_object_type=child_object,
        parent_object_type=parent_object,
        parent_object_id=parent_object_id,
        limit=10,
    )

    assert response == []

    mock_httpx_client.get.assert_called_once_with(
        url=f"https://org_domain.my.salesforce.com/services/data/{SALESFORCE_API_VERSION}/sobjects/{parent_object.value}/{parent_object_id}/{child_object.plural.lower()}",
        headers={"Authorization": f"Bearer {mock_context.authorization.token}"},
        params={"limit": 10},
    )


@pytest.mark.asyncio
async def test_get_related_objects_not_found_error(mock_context, mock_httpx_client):
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.json.return_value = [{"message": "Not found"}]
    mock_httpx_client.get.return_value = mock_response

    client = SalesforceClient(
        auth_token=mock_context.authorization.token,
        org_subdomain="org_domain",
    )

    parent_object_id = "001gK000003DIn0QAG"
    parent_object = SalesforceObject.ACCOUNT
    child_object = SalesforceObject.CONTACT

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"records": []}
    mock_httpx_client.get.return_value = mock_response

    response = await client._get_related_objects(
        child_object_type=child_object,
        parent_object_type=parent_object,
        parent_object_id=parent_object_id,
        limit=10,
    )

    assert response == []

    mock_httpx_client.get.assert_called_once_with(
        url=f"https://org_domain.my.salesforce.com/services/data/{SALESFORCE_API_VERSION}/sobjects/{parent_object.value}/{parent_object_id}/{child_object.plural.lower()}",
        headers={"Authorization": f"Bearer {mock_context.authorization.token}"},
        params={"limit": 10},
    )


@pytest.mark.asyncio
@patch("arcade_salesforce.models.build_soql_query")
async def test_get_notes_success(mock_build_soql_query, mock_context, mock_httpx_client):
    client = SalesforceClient(
        auth_token=mock_context.authorization.token,
        org_subdomain="org_domain",
    )

    note_data = {
        "Id": "003gK000003DIn0QAG",
        "Title": "Note 1",
        "Body": "Note 1 body",
        "OwnerId": "005gK000003DIn0QAG",
        "CreatedById": "005gK000003DIn0QAG",
        "CreatedDate": "2025-01-01T00:00:00Z",
        "attributes": {
            "type": "Note",
        },
    }

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"records": [note_data]}
    mock_httpx_client.get.return_value = mock_response

    parent_id = "003gK000003DIn0QAG"
    response = await client.get_notes(parent_id=parent_id, limit=10)
    assert response == [
        {
            "Id": note_data["Id"],
            "Title": note_data["Title"],
            "Body": note_data["Body"],
            "OwnerId": note_data["OwnerId"],
            "ObjectType": SalesforceObject.NOTE.value,
        }
    ]

    mock_httpx_client.get.assert_called_once_with(
        url=f"https://org_domain.my.salesforce.com/services/data/{SALESFORCE_API_VERSION}/query",
        headers={"Authorization": f"Bearer {mock_context.authorization.token}"},
        params={"q": mock_build_soql_query.return_value},
    )

    mock_build_soql_query.assert_called_once_with(
        "SELECT Id, Title, Body, OwnerId, CreatedById, CreatedDate "
        "FROM Note "
        "WHERE ParentId = '{parent_id}' "
        "LIMIT {limit}",
        parent_id=parent_id,
        limit=10,
    )


@pytest.mark.asyncio
@patch("arcade_salesforce.models.build_soql_query")
async def test_get_notes_not_found_error(mock_build_soql_query, mock_context, mock_httpx_client):
    client = SalesforceClient(
        auth_token=mock_context.authorization.token,
        org_subdomain="org_domain",
    )

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.json.return_value = [{"message": "Not found"}]
    mock_httpx_client.get.return_value = mock_response

    parent_id = "003gK000003DIn0QAG"
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await client.get_notes(parent_id=parent_id, limit=10)
    assert exc_info.value.errors == ["Not found"]
