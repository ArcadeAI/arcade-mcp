from unittest.mock import MagicMock

import httpx
import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_todoist.tools.tasks import (
    ProjectNotFoundError,
    TaskNotFoundError,
    close_task,
    close_task_by_task_id,
    create_task,
    create_task_in_project,
    delete_task,
    delete_task_by_task_id,
    get_all_tasks,
    get_tasks_by_project_id,
    get_tasks_by_project_name,
)

fake_tasks_response = {
    "results": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "priority": 1,
            "project_id": "project id",
            "checked": True,
            "description": "Description of the task",
        }
    ],
    "next_cursor": None
}

faked_parsed_tasks = {
    "tasks": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "project_id": "project id",
            "checked": True,
        }
    ],
    "next_page_token": None
}

fake_paginated_tasks_response = {
    "results": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "priority": 1,
            "project_id": "project id",
            "checked": True,
            "description": "Description of the task",
        }
    ],
    "next_cursor": "next_page_cursor_123"
}

faked_parsed_paginated_tasks = {
    "tasks": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "project_id": "project id",
            "checked": True,
        }
    ],
    "next_page_token": "next_page_cursor_123"
}

fake_create_task_response = {
    "id": "2",
    "content": "New Task",
    "added_at": "2024-01-01",
    "project_id": "project_123",
    "checked": False,
    "priority": 1,
    "description": "A new task description",
}

faked_parsed_create_task = {
    "id": "2",
    "content": "New Task",
    "added_at": "2024-01-01",
    "project_id": "project_123",
    "checked": False,
}

expected_close_task_response = {"message": "Task closed successfully"}

expected_delete_task_response = {"message": "Task deleted successfully"}


@pytest.mark.asyncio
async def test_get_all_tasks_success(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_tasks_response
    httpx_mock.get.return_value = mock_response

    result = await get_all_tasks(context=tool_context)

    assert result == faked_parsed_tasks

    httpx_mock.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_tasks_failure(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {}
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Not Found", request=httpx.Request("GET", "http://test.com"), response=mock_response
    )
    httpx_mock.get.return_value = mock_response

    with pytest.raises(ToolExecutionError):
        await get_all_tasks(context=tool_context)

    httpx_mock.get.assert_called_once()


@pytest.mark.asyncio
async def test_create_task_in_project_success(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_create_task_response
    httpx_mock.post.return_value = mock_response

    result = await create_task_in_project(
        context=tool_context, description="New Task", project_id="project_123"
    )

    assert result == faked_parsed_create_task

    httpx_mock.post.assert_called_once()


@pytest.mark.asyncio
async def test_create_task_in_project_failure(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {}
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Bad Request",
        request=httpx.Request("POST", "http://test.com"),
        response=mock_response,
    )
    httpx_mock.post.return_value = mock_response

    with pytest.raises(ToolExecutionError):
        await create_task_in_project(
            context=tool_context, description="New Task", project_id="project_123"
        )

    httpx_mock.post.assert_called_once()


@pytest.mark.asyncio
async def test_close_task_by_task_id_success(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    httpx_mock.post.return_value = mock_response

    result = await close_task_by_task_id(context=tool_context, task_id="task_123")

    assert result == expected_close_task_response

    httpx_mock.post.assert_called_once()


@pytest.mark.asyncio
async def test_close_task_by_task_id_failure(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {}
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Not Found",
        request=httpx.Request("POST", "http://test.com"),
        response=mock_response,
    )
    httpx_mock.post.return_value = mock_response

    with pytest.raises(ToolExecutionError):
        await close_task_by_task_id(context=tool_context, task_id="task_123")

    httpx_mock.post.assert_called_once()


@pytest.mark.asyncio
async def test_delete_task_by_task_id_success(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    httpx_mock.delete.return_value = mock_response

    result = await delete_task_by_task_id(context=tool_context, task_id="task_123")

    assert result == expected_delete_task_response

    httpx_mock.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_task_by_task_id_failure(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {}
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Not Found",
        request=httpx.Request("DELETE", "http://test.com"),
        response=mock_response,
    )
    httpx_mock.delete.return_value = mock_response

    with pytest.raises(ToolExecutionError):
        await delete_task_by_task_id(context=tool_context, task_id="task_123")

    httpx_mock.delete.assert_called_once()


# Additional test data for project-based and description-based tests
fake_projects_response = {
    "projects": [
        {"id": "project_123", "name": "Work Project", "created_at": "2021-01-01"},
        {"id": "project_456", "name": "Personal Tasks", "created_at": "2021-01-01"},
    ]
}

fake_multiple_tasks_response = {
    "tasks": [
        {
            "id": "1",
            "content": "Buy groceries",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": False,
        },
        {
            "id": "2",
            "content": "Grocery shopping",
            "added_at": "2021-01-01",
            "project_id": "project_456",
            "checked": False,
        },
        {
            "id": "3",
            "content": "Meeting notes",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": False,
        },
    ],
    "next_page_token": None
}


@pytest.mark.asyncio
async def test_create_task_success_exact_project_match(tool_context, mocker) -> None:
    # Mock get_projects
    mock_get_projects = mocker.patch("arcade_todoist.tools.tasks.get_projects")
    mock_get_projects.return_value = fake_projects_response

    # Mock create_task_in_project
    mock_create_task_in_project = mocker.patch("arcade_todoist.tools.tasks.create_task_in_project")
    mock_create_task_in_project.return_value = faked_parsed_create_task

    result = await create_task(
        context=tool_context, description="New Task", project_name="Work Project"
    )

    assert result == faked_parsed_create_task
    mock_get_projects.assert_called_once_with(context=tool_context)
    mock_create_task_in_project.assert_called_once_with(
        context=tool_context, description="New Task", project_id="project_123"
    )


@pytest.mark.asyncio
async def test_create_task_success_no_project(tool_context, mocker) -> None:
    # Mock create_task_in_project
    mock_create_task_in_project = mocker.patch("arcade_todoist.tools.tasks.create_task_in_project")
    mock_create_task_in_project.return_value = faked_parsed_create_task

    result = await create_task(context=tool_context, description="New Task", project_name=None)

    assert result == faked_parsed_create_task
    mock_create_task_in_project.assert_called_once_with(
        context=tool_context, description="New Task", project_id=None
    )


@pytest.mark.asyncio
async def test_create_task_project_not_found(tool_context, mocker) -> None:
    # Mock get_projects
    mock_get_projects = mocker.patch("arcade_todoist.tools.tasks.get_projects")
    mock_get_projects.return_value = fake_projects_response

    with pytest.raises(ProjectNotFoundError) as exc_info:
        await create_task(
            context=tool_context, description="New Task", project_name="Nonexistent Project"
        )

    assert "Project not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_task_project_partial_match(tool_context, mocker) -> None:
    # Mock get_projects
    mock_get_projects = mocker.patch("arcade_todoist.tools.tasks.get_projects")
    mock_get_projects.return_value = fake_projects_response

    with pytest.raises(ProjectNotFoundError) as exc_info:
        await create_task(context=tool_context, description="New Task", project_name="Work")

    assert "Project not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_close_task_success_exact_match(tool_context, mocker) -> None:
    # Mock get_all_tasks
    mock_get_all_tasks = mocker.patch("arcade_todoist.tools.tasks.get_all_tasks")
    mock_get_all_tasks.return_value = fake_multiple_tasks_response

    # Mock close_task_by_task_id
    mock_close_task_by_task_id = mocker.patch("arcade_todoist.tools.tasks.close_task_by_task_id")
    mock_close_task_by_task_id.return_value = expected_close_task_response

    result = await close_task(context=tool_context, task_description="Buy groceries")

    assert result == expected_close_task_response
    mock_get_all_tasks.assert_called_once_with(context=tool_context)
    mock_close_task_by_task_id.assert_called_once_with(context=tool_context, task_id="1")


@pytest.mark.asyncio
async def test_close_task_not_found(tool_context, mocker) -> None:
    # Mock get_all_tasks
    mock_get_all_tasks = mocker.patch("arcade_todoist.tools.tasks.get_all_tasks")
    mock_get_all_tasks.return_value = fake_multiple_tasks_response

    with pytest.raises(TaskNotFoundError) as exc_info:
        await close_task(context=tool_context, task_description="Nonexistent task")

    assert "Task not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_close_task_partial_match(tool_context, mocker) -> None:
    # Mock get_all_tasks
    mock_get_all_tasks = mocker.patch("arcade_todoist.tools.tasks.get_all_tasks")
    mock_get_all_tasks.return_value = fake_multiple_tasks_response

    with pytest.raises(TaskNotFoundError) as exc_info:
        await close_task(context=tool_context, task_description="grocery")

    error_message = str(exc_info.value)
    assert "Task not found" in error_message


@pytest.mark.asyncio
async def test_delete_task_success_exact_match(tool_context, mocker) -> None:
    # Mock get_all_tasks
    mock_get_all_tasks = mocker.patch("arcade_todoist.tools.tasks.get_all_tasks")
    mock_get_all_tasks.return_value = fake_multiple_tasks_response

    # Mock delete_task_by_task_id
    mock_delete_task_by_task_id = mocker.patch("arcade_todoist.tools.tasks.delete_task_by_task_id")
    mock_delete_task_by_task_id.return_value = expected_delete_task_response

    result = await delete_task(context=tool_context, task_description="Meeting notes")

    assert result == expected_delete_task_response
    mock_get_all_tasks.assert_called_once_with(context=tool_context)
    mock_delete_task_by_task_id.assert_called_once_with(context=tool_context, task_id="3")


@pytest.mark.asyncio
async def test_delete_task_not_found(tool_context, mocker) -> None:
    # Mock get_all_tasks
    mock_get_all_tasks = mocker.patch("arcade_todoist.tools.tasks.get_all_tasks")
    mock_get_all_tasks.return_value = fake_multiple_tasks_response

    with pytest.raises(TaskNotFoundError) as exc_info:
        await delete_task(context=tool_context, task_description="Nonexistent task")

    assert "Task not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_task_partial_match(tool_context, mocker) -> None:
    # Mock get_all_tasks
    mock_get_all_tasks = mocker.patch("arcade_todoist.tools.tasks.get_all_tasks")
    mock_get_all_tasks.return_value = fake_multiple_tasks_response

    with pytest.raises(TaskNotFoundError) as exc_info:
        await delete_task(context=tool_context, task_description="notes")

    assert "Task not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_tasks_by_project_id_success(tool_context, httpx_mock) -> None:
    # Mock API response for specific project
    project_tasks_response = {
        "results": [
            {
                "id": "1",
                "content": "Buy groceries",
                "added_at": "2021-01-01",
                "priority": 1,
                "project_id": "project_123",
                "checked": False,
                "description": "Description of the task",
            },
            {
                "id": "3",
                "content": "Meeting notes",
                "added_at": "2021-01-01",
                "priority": 1,
                "project_id": "project_123",
                "checked": False,
                "description": "Description of the task",
            },
        ],
        "next_cursor": None
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = project_tasks_response
    httpx_mock.get.return_value = mock_response

    result = await get_tasks_by_project_id(context=tool_context, project_id="project_123")

    # Should only return tasks from project_123
    expected_filtered_tasks = {
        "tasks": [
            {
                "id": "1",
                "content": "Buy groceries",
                "added_at": "2021-01-01",
                "project_id": "project_123",
                "checked": False,
            },
            {
                "id": "3",
                "content": "Meeting notes",
                "added_at": "2021-01-01",
                "project_id": "project_123",
                "checked": False,
            },
        ],
        "next_page_token": None
    }

    assert result == expected_filtered_tasks
    httpx_mock.get.assert_called_once()

    # Verify the API was called with the correct query parameter
    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {"limit": 50, "project_id": "project_123"}


@pytest.mark.asyncio
async def test_get_tasks_by_project_id_empty_result(tool_context, httpx_mock) -> None:
    # Mock API response with no tasks for the project
    empty_tasks_response = {"results": [], "next_cursor": None}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = empty_tasks_response
    httpx_mock.get.return_value = mock_response

    result = await get_tasks_by_project_id(context=tool_context, project_id="empty_project")

    # Should return empty tasks list
    expected_empty_result = {"tasks": [], "next_page_token": None}

    assert result == expected_empty_result
    httpx_mock.get.assert_called_once()

    # Verify the API was called with the correct query parameter
    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {"limit": 50, "project_id": "empty_project"}


@pytest.mark.asyncio
async def test_get_tasks_by_project_id_failure(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {}
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Not Found", request=httpx.Request("GET", "http://test.com"), response=mock_response
    )
    httpx_mock.get.return_value = mock_response

    with pytest.raises(ToolExecutionError):
        await get_tasks_by_project_id(context=tool_context, project_id="project_123")

    httpx_mock.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_tasks_by_project_name_success(tool_context, mocker) -> None:
    # Mock get_projects
    mock_get_projects = mocker.patch("arcade_todoist.tools.tasks.get_projects")
    mock_get_projects.return_value = fake_projects_response

    # Mock get_tasks_by_project_id
    expected_filtered_tasks = {
        "tasks": [
            {
                "id": "1",
                "content": "Buy groceries",
                "added_at": "2021-01-01",
                "project_id": "project_123",
                "checked": False,
            },
            {
                "id": "3",
                "content": "Meeting notes",
                "added_at": "2021-01-01",
                "project_id": "project_123",
                "checked": False,
            },
        ],
        "next_page_token": None
    }
    mock_get_tasks_by_project_id = mocker.patch(
        "arcade_todoist.tools.tasks.get_tasks_by_project_id"
    )
    mock_get_tasks_by_project_id.return_value = expected_filtered_tasks

    result = await get_tasks_by_project_name(context=tool_context, project_name="Work Project")

    assert result == expected_filtered_tasks
    mock_get_projects.assert_called_once_with(context=tool_context)
    mock_get_tasks_by_project_id.assert_called_once_with(
        context=tool_context, project_id="project_123", limit=50, next_page_token=None
    )


@pytest.mark.asyncio
async def test_get_tasks_by_project_name_not_found(tool_context, mocker) -> None:
    # Mock get_projects
    mock_get_projects = mocker.patch("arcade_todoist.tools.tasks.get_projects")
    mock_get_projects.return_value = fake_projects_response

    with pytest.raises(ProjectNotFoundError) as exc_info:
        await get_tasks_by_project_name(context=tool_context, project_name="Nonexistent Project")

    assert "Project not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_tasks_by_project_name_partial_match(tool_context, mocker) -> None:
    # Mock get_projects
    mock_get_projects = mocker.patch("arcade_todoist.tools.tasks.get_projects")
    mock_get_projects.return_value = fake_projects_response

    with pytest.raises(ProjectNotFoundError) as exc_info:
        await get_tasks_by_project_name(context=tool_context, project_name="Work")

    assert "Project not found" in str(exc_info.value)


# Pagination-specific tests
@pytest.mark.asyncio
async def test_get_all_tasks_with_custom_limit(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_tasks_response
    httpx_mock.get.return_value = mock_response

    result = await get_all_tasks(context=tool_context, limit=25)

    assert result == faked_parsed_tasks
    httpx_mock.get.assert_called_once()

    # Verify the API was called with the correct limit parameter
    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {"limit": 25}


@pytest.mark.asyncio
async def test_get_all_tasks_with_pagination(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_paginated_tasks_response
    httpx_mock.get.return_value = mock_response

    result = await get_all_tasks(context=tool_context, next_page_token="page_token_123")

    assert result == faked_parsed_paginated_tasks
    httpx_mock.get.assert_called_once()

    # Verify the API was called with the cursor parameter
    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {"limit": 50, "cursor": "page_token_123"}


@pytest.mark.asyncio
async def test_get_tasks_by_project_id_with_custom_limit(tool_context, httpx_mock) -> None:
    project_tasks_response = {
        "results": [
            {
                "id": "1",
                "content": "Task 1",
                "added_at": "2021-01-01",
                "priority": 1,
                "project_id": "project_123",
                "checked": False,
                "description": "Description",
            },
        ],
        "next_cursor": None
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = project_tasks_response
    httpx_mock.get.return_value = mock_response

    result = await get_tasks_by_project_id(
        context=tool_context, project_id="project_123", limit=100
    )

    expected_result = {
        "tasks": [
            {
                "id": "1",
                "content": "Task 1",
                "added_at": "2021-01-01",
                "project_id": "project_123",
                "checked": False,
            },
        ],
        "next_page_token": None
    }

    assert result == expected_result
    httpx_mock.get.assert_called_once()

    # Verify the API was called with custom limit and project_id
    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {"limit": 100, "project_id": "project_123"}


@pytest.mark.asyncio
async def test_get_tasks_by_project_id_with_pagination(tool_context, httpx_mock) -> None:
    project_tasks_response = {
        "results": [
            {
                "id": "1",
                "content": "Task 1",
                "added_at": "2021-01-01",
                "priority": 1,
                "project_id": "project_123",
                "checked": False,
                "description": "Description",
            },
        ],
        "next_cursor": "next_page_token_456"
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = project_tasks_response
    httpx_mock.get.return_value = mock_response

    result = await get_tasks_by_project_id(
        context=tool_context, 
        project_id="project_123", 
        limit=25,
        next_page_token="previous_page_token"
    )

    expected_result = {
        "tasks": [
            {
                "id": "1",
                "content": "Task 1",
                "added_at": "2021-01-01",
                "project_id": "project_123",
                "checked": False,
            },
        ],
        "next_page_token": "next_page_token_456"
    }

    assert result == expected_result
    httpx_mock.get.assert_called_once()

    # Verify the API was called with all pagination parameters
    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {
        "limit": 25, 
        "cursor": "previous_page_token",
        "project_id": "project_123"
    }


@pytest.mark.asyncio
async def test_get_tasks_by_project_name_with_pagination(tool_context, mocker) -> None:
    # Mock get_projects
    mock_get_projects = mocker.patch("arcade_todoist.tools.tasks.get_projects")
    mock_get_projects.return_value = fake_projects_response

    # Mock get_tasks_by_project_id
    expected_result = {
        "tasks": [
            {
                "id": "1",
                "content": "Task 1",
                "added_at": "2021-01-01",
                "project_id": "project_123",
                "checked": False,
            },
        ],
        "next_page_token": "next_token_789"
    }
    mock_get_tasks_by_project_id = mocker.patch(
        "arcade_todoist.tools.tasks.get_tasks_by_project_id"
    )
    mock_get_tasks_by_project_id.return_value = expected_result

    result = await get_tasks_by_project_name(
        context=tool_context, 
        project_name="Work Project",
        limit=10,
        next_page_token="some_token"
    )

    assert result == expected_result
    mock_get_projects.assert_called_once_with(context=tool_context)
    mock_get_tasks_by_project_id.assert_called_once_with(
        context=tool_context, 
        project_id="project_123", 
        limit=10, 
        next_page_token="some_token"
    )
