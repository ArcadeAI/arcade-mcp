from unittest.mock import MagicMock, patch

import pytest
from arcade_tdk import ToolContext
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_jira.utils import resolve_cloud_id


@patch("arcade_jira.tools.cloud.get_available_atlassian_clouds")
@pytest.mark.asyncio
async def test_resolve_cloud_id_with_value_already_provided(
    mock_get_available_atlassian_clouds: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    mock_get_available_atlassian_clouds.return_value = [
        {
            "id": fake_cloud_id,
            "name": fake_cloud_name,
            "url": f"https://{fake_cloud_name}.atlassian.net",
        }
    ]

    cloud_id = await resolve_cloud_id(mock_context, "cloud_id_provided")
    assert cloud_id == "cloud_id_provided"


@patch("arcade_jira.tools.cloud.get_available_atlassian_clouds")
@pytest.mark.asyncio
async def test_resolve_cloud_id_with_single_cloud_available(
    mock_get_available_atlassian_clouds: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    mock_get_available_atlassian_clouds.return_value = [
        {
            "id": fake_cloud_id,
            "name": fake_cloud_name,
            "url": f"https://{fake_cloud_name}.atlassian.net",
        }
    ]

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
    mock_get_available_atlassian_clouds.return_value = [
        {
            "id": fake_cloud_id,
            "name": fake_cloud_name,
            "url": f"https://{fake_cloud_name}.atlassian.net",
        },
        {
            "id": "cloud_id_2",
            "name": "Cloud 2",
            "url": "https://cloud2.atlassian.net",
        },
    ]

    with pytest.raises(RetryableToolError) as exc:
        await resolve_cloud_id(mock_context, None)

    assert "Multiple Atlassian Clouds are available" in exc.value.message
    assert fake_cloud_id in exc.value.additional_prompt_content
    assert fake_cloud_name in exc.value.additional_prompt_content
    assert "cloud_id_2" in exc.value.additional_prompt_content
    assert "Cloud 2" in exc.value.additional_prompt_content


@patch("arcade_jira.tools.cloud.get_available_atlassian_clouds")
@pytest.mark.asyncio
async def test_resolve_cloud_id_with_no_clouds_available(
    mock_get_available_atlassian_clouds: MagicMock,
    mock_context: ToolContext,
    fake_cloud_id: str,
    fake_cloud_name: str,
):
    mock_get_available_atlassian_clouds.return_value = []

    with pytest.raises(ToolExecutionError) as exc:
        await resolve_cloud_id(mock_context, None)

    assert "No Atlassian Cloud is available" in exc.value.message
