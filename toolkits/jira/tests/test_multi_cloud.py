import asyncio
import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from arcade_tdk import ToolContext
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_jira.utils import check_if_cloud_is_authorized, resolve_cloud_id


@pytest.fixture
def mock_httpx_client():
    with patch("arcade_jira.utils.httpx") as mock_httpx:
        yield mock_httpx.AsyncClient().__aenter__.return_value


@patch("arcade_jira.tools.cloud.get_available_atlassian_clouds")
@pytest.mark.asyncio
async def test_resolve_cloud_id_with_value_already_provided(
    mock_get_available_atlassian_clouds: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    another_cloud_id = str(uuid.uuid4())
    mock_get_available_atlassian_clouds.return_value = {
        "clouds_available": [
            {
                "atlassian_cloud_id": fake_cloud_id,
                "atlassian_cloud_name": fake_cloud_name,
                "atlassian_cloud_url": f"https://{fake_cloud_name}.atlassian.net",
            }
        ]
    }

    cloud_id = await resolve_cloud_id(mock_context, another_cloud_id)
    assert cloud_id == another_cloud_id


@patch("arcade_jira.tools.cloud.get_available_atlassian_clouds")
@pytest.mark.asyncio
async def test_resolve_cloud_id_providing_cloud_name(
    mock_get_available_atlassian_clouds: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    mock_get_available_atlassian_clouds.return_value = {
        "clouds_available": [
            {
                "atlassian_cloud_id": fake_cloud_id,
                "atlassian_cloud_name": fake_cloud_name,
                "atlassian_cloud_url": f"https://{fake_cloud_name}.atlassian.net",
            }
        ]
    }

    cloud_id = await resolve_cloud_id(mock_context, fake_cloud_name)
    assert cloud_id == fake_cloud_id


@patch("arcade_jira.tools.cloud.get_available_atlassian_clouds")
@pytest.mark.asyncio
async def test_resolve_cloud_id_with_single_cloud_available(
    mock_get_available_atlassian_clouds: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    mock_get_available_atlassian_clouds.return_value = {
        "clouds_available": [
            {
                "atlassian_cloud_id": fake_cloud_id,
                "atlassian_cloud_name": fake_cloud_name,
                "atlassian_cloud_url": f"https://{fake_cloud_name}.atlassian.net",
            }
        ]
    }

    cloud_id = await resolve_cloud_id(mock_context, None)
    assert cloud_id == fake_cloud_id


@patch("arcade_jira.tools.cloud.get_available_atlassian_clouds")
@pytest.mark.asyncio
async def test_resolve_cloud_id_with_multiple_distinct_clouds_available(
    mock_get_available_atlassian_clouds: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    cloud_id_2 = str(uuid.uuid4())
    mock_get_available_atlassian_clouds.return_value = {
        "clouds_available": [
            {
                "atlassian_cloud_id": fake_cloud_id,
                "atlassian_cloud_name": fake_cloud_name,
                "atlassian_cloud_url": f"https://{fake_cloud_name}.atlassian.net",
            },
            {
                "atlassian_cloud_id": cloud_id_2,
                "atlassian_cloud_name": "Cloud 2",
                "atlassian_cloud_url": "https://cloud2.atlassian.net",
            },
        ]
    }

    with pytest.raises(RetryableToolError) as exc:
        await resolve_cloud_id(mock_context, None)

    assert "Multiple Atlassian Clouds are available" in exc.value.message
    assert fake_cloud_id in exc.value.additional_prompt_content
    assert fake_cloud_name in exc.value.additional_prompt_content
    assert cloud_id_2 in exc.value.additional_prompt_content
    assert "Cloud 2" in exc.value.additional_prompt_content


@patch("arcade_jira.tools.cloud.get_available_atlassian_clouds")
@pytest.mark.asyncio
async def test_resolve_cloud_id_with_no_clouds_available(
    mock_get_available_atlassian_clouds: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    mock_get_available_atlassian_clouds.return_value = {"clouds_available": []}

    with pytest.raises(ToolExecutionError) as exc:
        await resolve_cloud_id(mock_context, None)

    assert "No Atlassian Cloud is available" in exc.value.message


@pytest.mark.asyncio
async def test_check_if_cloud_is_authorized_success(
    mock_httpx_client: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    cloud = {
        "atlassian_cloud_id": fake_cloud_id,
        "atlassian_cloud_name": fake_cloud_name,
        "atlassian_cloud_url": f"https://{fake_cloud_name}.atlassian.net",
    }
    fake_user_id = uuid.uuid4()
    mock_httpx_client.get.return_value.status_code = 200
    mock_httpx_client.get.return_value.json.return_value = {
        "self": f"https://api.atlassian.com/ex/jira/{fake_cloud_id}/rest/api/3/user?accountId={fake_user_id!s}",
        "accountId": fake_user_id,
        "accountType": "atlassian",
        "emailAddress": f"john.doe@{fake_cloud_name}.com",
        "displayName": "John Doe",
    }

    semaphore = asyncio.Semaphore(1)

    response = await check_if_cloud_is_authorized(mock_context, cloud, semaphore)

    assert response == cloud


@pytest.mark.asyncio
async def test_check_if_cloud_is_authorized_returning_401_error(
    mock_httpx_client: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    cloud = {
        "atlassian_cloud_id": fake_cloud_id,
        "atlassian_cloud_name": fake_cloud_name,
        "atlassian_cloud_url": f"https://{fake_cloud_name}.atlassian.net",
    }

    mock_httpx_client.get.return_value.status_code = 401
    mock_httpx_client.get.return_value.json.return_value = {
        "code": 401,
        "message": "Unauthorized",
    }

    semaphore = asyncio.Semaphore(1)

    response = await check_if_cloud_is_authorized(mock_context, cloud, semaphore)

    assert response is False


@pytest.mark.asyncio
async def test_check_if_cloud_is_authorized_returning_404_no_message_available_error(
    mock_httpx_client: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    cloud = {
        "atlassian_cloud_id": fake_cloud_id,
        "atlassian_cloud_name": fake_cloud_name,
        "atlassian_cloud_url": f"https://{fake_cloud_name}.atlassian.net",
    }

    def mock_response_json() -> dict[str, Any]:
        return {
            "code": 404,
            "message": "No message available",
        }

    mock_httpx_client.get.return_value.status_code = 404
    mock_httpx_client.get.return_value.json = mock_response_json

    semaphore = asyncio.Semaphore(1)

    response = await check_if_cloud_is_authorized(mock_context, cloud, semaphore)

    assert response is False


@pytest.mark.asyncio
async def test_check_if_cloud_is_authorized_returning_404_unrecognized_error(
    mock_httpx_client: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    cloud = {
        "atlassian_cloud_id": fake_cloud_id,
        "atlassian_cloud_name": fake_cloud_name,
        "atlassian_cloud_url": f"https://{fake_cloud_name}.atlassian.net",
    }

    response_data = {
        "code": 404,
        "message": "Something else was not found",
    }

    def mock_response_json() -> dict[str, Any]:
        return response_data

    mock_httpx_client.get.return_value.status_code = 404
    mock_httpx_client.get.return_value.text = json.dumps(response_data)
    mock_httpx_client.get.return_value.json = mock_response_json

    semaphore = asyncio.Semaphore(1)

    response = await check_if_cloud_is_authorized(mock_context, cloud, semaphore)

    assert response is False


@pytest.mark.asyncio
async def test_check_if_cloud_is_authorized_raising_unexpected_exception(
    mock_httpx_client: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    cloud = {
        "atlassian_cloud_id": fake_cloud_id,
        "atlassian_cloud_name": fake_cloud_name,
        "atlassian_cloud_url": f"https://{fake_cloud_name}.atlassian.net",
    }

    mock_httpx_client.get.side_effect = Exception("Something went wrong")

    semaphore = asyncio.Semaphore(1)

    with pytest.raises(ToolExecutionError) as exc:
        await check_if_cloud_is_authorized(mock_context, cloud, semaphore)

    assert fake_cloud_id in exc.value.message
    assert fake_cloud_id in exc.value.developer_message
    assert "Something went wrong" in exc.value.developer_message
