from unittest.mock import patch

import pytest
from arcade_tdk.errors import RetryableToolError

from arcade_asana.utils import (
    get_project_by_name_or_raise_error,
    get_tag_ids,
    get_unique_workspace_id_or_raise_error,
)


@pytest.mark.asyncio
@patch("arcade_asana.utils.find_tags_by_name")
async def test_get_tag_ids(mock_find_tags_by_name, mock_context):
    assert await get_tag_ids(mock_context, None) is None
    assert await get_tag_ids(mock_context, ["1234567890", "1234567891"]) == [
        "1234567890",
        "1234567891",
    ]

    mock_find_tags_by_name.return_value = {
        "matches": {
            "tags": [
                {"id": "1234567890", "name": "My Tag"},
                {"id": "1234567891", "name": "My Other Tag"},
            ]
        },
        "not_found": {"tags": []},
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
            {"id": "1234567890", "name": "My Workspace"},
        ]
    }
    assert await get_unique_workspace_id_or_raise_error(mock_context) == "1234567890"

    mock_list_workspaces.return_value = {
        "workspaces": [
            {"id": "1234567890", "name": "My Workspace"},
            {"id": "1234567891", "name": "My Other Workspace"},
        ]
    }
    with pytest.raises(RetryableToolError) as exc_info:
        await get_unique_workspace_id_or_raise_error(mock_context)

    assert "My Other Workspace" in exc_info.value.additional_prompt_content


@pytest.mark.asyncio
@patch("arcade_asana.utils.find_projects_by_name")
async def test_get_project_by_name_or_raise_error(mock_find_projects_by_name, mock_context):
    project1 = {"id": "1234567890", "name": "My Project"}

    mock_find_projects_by_name.return_value = {
        "matches": {"projects": [project1], "count": 1},
        "not_matched": {"projects": [], "count": 0},
    }
    assert await get_project_by_name_or_raise_error(mock_context, project1["name"]) == project1

    mock_find_projects_by_name.return_value = {
        "matches": {"projects": [], "count": 0},
        "not_matched": {"projects": [project1], "count": 1},
    }
    with pytest.raises(RetryableToolError) as exc_info:
        await get_project_by_name_or_raise_error(mock_context, "Inexistent Project")

    assert project1["name"] in exc_info.value.additional_prompt_content
