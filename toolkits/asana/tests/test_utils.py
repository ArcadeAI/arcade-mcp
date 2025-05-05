from unittest.mock import patch

import pytest
from arcade.sdk.errors import RetryableToolError

from arcade_asana.utils import (
    get_project_by_name_or_raise_error,
    get_tag_ids,
    get_unique_workspace_id_or_raise_error,
    handle_task_project_association,
)


@pytest.mark.asyncio
@patch("arcade_asana.tools.tags.search_tags_by_name")
async def test_get_tag_ids(mock_search_tags_by_name, mock_context):
    assert await get_tag_ids(mock_context, None) is None
    assert await get_tag_ids(mock_context, ["1234567890", "1234567891"]) == [
        "1234567890",
        "1234567891",
    ]

    mock_search_tags_by_name.return_value = {
        "matches": {
            "tags": [
                {"gid": "1234567890", "name": "My Tag"},
                {"gid": "1234567891", "name": "My Other Tag"},
            ]
        }
    }

    assert await get_tag_ids(mock_context, ["My Tag", "My Other Tag"]) == [
        "1234567890",
        "1234567891",
    ]


@pytest.mark.asyncio
@patch("arcade_asana.tools.workspaces.list_workspaces")
async def test_get_unique_workspace_id_or_raise_error(mock_list_workspaces, mock_context):
    mock_list_workspaces.return_value = {
        "workspaces": [
            {"gid": "1234567890", "name": "My Workspace"},
        ]
    }
    assert await get_unique_workspace_id_or_raise_error(mock_context) == "1234567890"

    mock_list_workspaces.return_value = {
        "workspaces": [
            {"gid": "1234567890", "name": "My Workspace"},
            {"gid": "1234567891", "name": "My Other Workspace"},
        ]
    }
    with pytest.raises(RetryableToolError) as exc_info:
        await get_unique_workspace_id_or_raise_error(mock_context)

    assert "My Other Workspace" in exc_info.value.additional_prompt_content


@pytest.mark.asyncio
@patch("arcade_asana.tools.projects.search_projects_by_name")
async def test_get_project_by_name_or_raise_error(mock_search_projects_by_name, mock_context):
    project1 = {"gid": "1234567890", "name": "My Project"}

    mock_search_projects_by_name.return_value = {
        "matches": {"projects": [project1]},
        "not_matched": {"projects": []},
    }
    assert await get_project_by_name_or_raise_error(mock_context, project1["name"]) == project1

    mock_search_projects_by_name.return_value = {
        "matches": {"projects": []},
        "not_matched": {"projects": [project1]},
    }
    with pytest.raises(RetryableToolError) as exc_info:
        await get_project_by_name_or_raise_error(mock_context, "Inexistent Project")

    assert project1["name"] in exc_info.value.additional_prompt_content


@pytest.mark.asyncio
@patch("arcade_asana.tools.projects.get_project_by_id")
@patch("arcade_asana.utils.get_project_by_name_or_raise_error")
async def test_handle_task_project_association_by_project_id(
    mock_get_project_by_name_or_raise_error, mock_get_project_by_id, mock_context
):
    mock_get_project_by_id.return_value = {"project": {"workspace": {"gid": "9999999999"}}}
    assert await handle_task_project_association(mock_context, "1234567890", None, None) == (
        "1234567890",
        "9999999999",
    )
    mock_get_project_by_id.assert_called_once_with(mock_context, "1234567890")
    mock_get_project_by_name_or_raise_error.assert_not_called()


@pytest.mark.asyncio
@patch("arcade_asana.tools.projects.get_project_by_id")
@patch("arcade_asana.utils.get_project_by_name_or_raise_error")
async def test_handle_task_project_association_by_project_name(
    mock_get_project_by_name_or_raise_error, mock_get_project_by_id, mock_context
):
    mock_get_project_by_name_or_raise_error.return_value = {
        "gid": "1234567890",
        "workspace": {"gid": "9999999999"},
    }
    assert await handle_task_project_association(mock_context, None, "hello project", None) == (
        "1234567890",
        "9999999999",
    )
    mock_get_project_by_name_or_raise_error.assert_called_once_with(mock_context, "hello project")
    mock_get_project_by_id.assert_not_called()
