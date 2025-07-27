from unittest.mock import MagicMock

import pytest

from arcade_todoist.tools.projects import get_projects

fake_projects_response = {
    "results": [
        {
            "id": "1",
            "name": "Project 1",
            "created_at": "2021-01-01",
            "can_assign_tasks": True,
            "child_order": 0,
            "color": "string",
            "creator_uid": "string",
            "is_archived": True,
            "is_deleted": True,
            "is_favorite": True,
        }
    ]
}

faked_parsed_projects = {"projects": [{"id": "1", "name": "Project 1", "created_at": "2021-01-01"}]}


@pytest.mark.asyncio
async def test_get_projects_success(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_projects_response
    httpx_mock.get.return_value = mock_response

    result = await get_projects(context=tool_context)

    assert result == faked_parsed_projects

    httpx_mock.get.assert_called_once()
