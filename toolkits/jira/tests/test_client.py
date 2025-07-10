import json

import httpx
import pytest

from arcade_jira.client import JiraClient
from arcade_jira.exceptions import JiraToolExecutionError


@pytest.mark.asyncio
async def test_get_cloud_data_from_available_resources_single_cloud(
    mock_httpx_client, fake_auth_token
):
    cloud = {"id": "123", "name": "Test Cloud", "url": "https://test.atlassian.net"}

    client = JiraClient(auth_token=fake_auth_token)

    mock_httpx_client.get.return_value = httpx.Response(
        status_code=200,
        json=[cloud],
    )

    response = await client._get_cloud_data_from_available_resources()
    assert response == cloud


@pytest.mark.asyncio
async def test_get_cloud_data_from_available_resources_multiple_clouds(
    mock_httpx_client, fake_auth_token
):
    cloud1 = {"id": "123", "name": "Test Cloud", "url": "https://test.atlassian.net"}
    cloud2 = {"id": "456", "name": "Test Cloud 2", "url": "https://test2.atlassian.net"}

    client = JiraClient(auth_token=fake_auth_token)

    mock_httpx_client.get.return_value = httpx.Response(
        status_code=200,
        json=[cloud1, cloud2],
    )

    with pytest.raises(JiraToolExecutionError) as error:
        await client._get_cloud_data_from_available_resources()

    assert "Multiple cloud IDs returned by Atlassian" in error.value.message
    assert json.dumps(cloud1) in error.value.message
    assert json.dumps(cloud2) in error.value.message


@pytest.mark.asyncio
async def test_get_cloud_data_from_available_resources_duplicate_cloud(
    mock_httpx_client, fake_auth_token
):
    cloud = {"id": "123", "name": "Test Cloud", "url": "https://test.atlassian.net"}

    client = JiraClient(auth_token=fake_auth_token)

    mock_httpx_client.get.return_value = httpx.Response(
        status_code=200,
        json=[cloud, cloud],
    )

    response = await client._get_cloud_data_from_available_resources()
    assert response == cloud
