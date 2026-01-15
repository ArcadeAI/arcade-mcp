from unittest.mock import MagicMock

import httpx
import pytest
from arcade_tdk.errors import ToolExecutionError
from arcade_todoist.errors import ProjectNotFoundError
from arcade_todoist.tools.tasks import (
    _close_task_by_task_id,
    _create_task_in_project,
    _delete_task_by_task_id,
    _get_tasks_by_project_id,
    close_task,
    create_task,
    delete_task,
    get_all_tasks,
    get_tasks_by_filter,
    get_tasks_by_project,
)

from tests.fakes import (
    CLOSE_TASK_SUCCESS_RESPONSE,
    CREATE_TASK_API_RESPONSE,
    CREATE_TASK_PARSED_RESPONSE,
    CUSTOM_LIMIT_TASK_API_RESPONSE,
    CUSTOM_LIMIT_TASK_PARSED_RESPONSE,
    DELETE_TASK_SUCCESS_RESPONSE,
    EMPTY_TASKS_API_RESPONSE,
    EMPTY_TASKS_PARSED_RESPONSE,
    PAGINATED_TASKS_API_RESPONSE,
    PAGINATED_TASKS_PARSED_RESPONSE,
    PROJECT_SPECIFIC_TASKS_API_RESPONSE,
    PROJECT_SPECIFIC_TASKS_PARSED_RESPONSE,
    PROJECTS_PARSED_RESPONSE,
    SINGLE_TASK_API_RESPONSE,
    SINGLE_TASK_PARSED_RESPONSE,
    TASKS_WITH_PAGINATION_API_RESPONSE,
    TASKS_WITH_PAGINATION_PARSED_RESPONSE,
)


@pytest.mark.asyncio
async def test_get_all_tasks_success(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SINGLE_TASK_API_RESPONSE
    httpx_mock.get.return_value = mock_response

    result = await get_all_tasks(context=tool_context)

    assert result == SINGLE_TASK_PARSED_RESPONSE

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
    mock_response.json.return_value = CREATE_TASK_API_RESPONSE
    httpx_mock.post.return_value = mock_response

    result = await _create_task_in_project(
        context=tool_context, description="New Task", project_id="project_123"
    )

    assert result == CREATE_TASK_PARSED_RESPONSE

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

    with pytest.raises(httpx.HTTPStatusError):
        await _create_task_in_project(
            context=tool_context, description="New Task", project_id="project_123"
        )

    httpx_mock.post.assert_called_once()


@pytest.mark.asyncio
async def test_close_task_by_task_id_success(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    httpx_mock.post.return_value = mock_response

    result = await _close_task_by_task_id(context=tool_context, task_id="task_123")

    assert result == CLOSE_TASK_SUCCESS_RESPONSE

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

    with pytest.raises(httpx.HTTPStatusError):
        await _close_task_by_task_id(context=tool_context, task_id="task_123")

    httpx_mock.post.assert_called_once()


@pytest.mark.asyncio
async def test_delete_task_by_task_id_success(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    httpx_mock.delete.return_value = mock_response

    result = await _delete_task_by_task_id(context=tool_context, task_id="task_123")

    assert result == DELETE_TASK_SUCCESS_RESPONSE

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

    with pytest.raises(httpx.HTTPStatusError):
        await _delete_task_by_task_id(context=tool_context, task_id="task_123")

    httpx_mock.delete.assert_called_once()


@pytest.mark.asyncio
async def test_create_task_success_exact_project_match(tool_context, mocker) -> None:
    mock_get_projects = mocker.patch("arcade_todoist.tools.projects.get_projects")
    mock_get_projects.return_value = PROJECTS_PARSED_RESPONSE

    mock_create_task_in_project = mocker.patch("arcade_todoist.tools.tasks._create_task_in_project")
    mock_create_task_in_project.return_value = CREATE_TASK_PARSED_RESPONSE

    result = await create_task(context=tool_context, description="New Task", project="Work Project")

    assert result == CREATE_TASK_PARSED_RESPONSE
    mock_get_projects.assert_called_once_with(context=tool_context)
    mock_create_task_in_project.assert_called_once_with(
        context=tool_context, description="New Task", project_id="project_123"
    )


@pytest.mark.asyncio
async def test_create_task_success_no_project(tool_context, mocker) -> None:
    mock_create_task_in_project = mocker.patch("arcade_todoist.tools.tasks._create_task_in_project")
    mock_create_task_in_project.return_value = CREATE_TASK_PARSED_RESPONSE

    result = await create_task(context=tool_context, description="New Task", project=None)

    assert result == CREATE_TASK_PARSED_RESPONSE
    mock_create_task_in_project.assert_called_once_with(
        context=tool_context, description="New Task", project_id=None
    )


@pytest.mark.asyncio
async def test_create_task_project_not_found(tool_context, mocker) -> None:
    mock_get_projects = mocker.patch("arcade_todoist.tools.projects.get_projects")
    mock_get_projects.return_value = PROJECTS_PARSED_RESPONSE

    with pytest.raises(ProjectNotFoundError) as exc_info:
        await create_task(
            context=tool_context, description="New Task", project="Nonexistent Project"
        )

    assert "Project not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_close_task_success_with_id(tool_context, mocker) -> None:
    mock_close_task_by_task_id = mocker.patch("arcade_todoist.tools.tasks._close_task_by_task_id")
    mock_close_task_by_task_id.return_value = CLOSE_TASK_SUCCESS_RESPONSE

    result = await close_task(context=tool_context, task_id="1")

    assert result == CLOSE_TASK_SUCCESS_RESPONSE
    mock_close_task_by_task_id.assert_called_once_with(context=tool_context, task_id="1")


@pytest.mark.asyncio
async def test_delete_task_success_with_id(tool_context, mocker) -> None:
    mock_delete_task_by_task_id = mocker.patch("arcade_todoist.tools.tasks._delete_task_by_task_id")
    mock_delete_task_by_task_id.return_value = DELETE_TASK_SUCCESS_RESPONSE

    result = await delete_task(context=tool_context, task_id="3")

    assert result == DELETE_TASK_SUCCESS_RESPONSE
    mock_delete_task_by_task_id.assert_called_once_with(context=tool_context, task_id="3")


@pytest.mark.asyncio
async def test_get_tasks_by_project_id_success(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = PROJECT_SPECIFIC_TASKS_API_RESPONSE
    httpx_mock.get.return_value = mock_response

    result = await _get_tasks_by_project_id(context=tool_context, project_id="project_123")

    assert result == PROJECT_SPECIFIC_TASKS_PARSED_RESPONSE
    httpx_mock.get.assert_called_once()

    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {"limit": 50, "project_id": "project_123"}


@pytest.mark.asyncio
async def test_get_tasks_by_project_id_empty_result(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = EMPTY_TASKS_API_RESPONSE
    httpx_mock.get.return_value = mock_response

    result = await _get_tasks_by_project_id(context=tool_context, project_id="empty_project")

    assert result == EMPTY_TASKS_PARSED_RESPONSE
    httpx_mock.get.assert_called_once()

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

    with pytest.raises(httpx.HTTPStatusError):
        await _get_tasks_by_project_id(context=tool_context, project_id="project_123")

    httpx_mock.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_tasks_by_project_name_success(tool_context, mocker) -> None:
    mock_get_projects = mocker.patch("arcade_todoist.tools.projects.get_projects")
    mock_get_projects.return_value = PROJECTS_PARSED_RESPONSE

    mock_get_tasks_by_project_id = mocker.patch(
        "arcade_todoist.tools.tasks._get_tasks_by_project_id"
    )
    mock_get_tasks_by_project_id.return_value = PROJECT_SPECIFIC_TASKS_PARSED_RESPONSE

    result = await get_tasks_by_project(context=tool_context, project="Work Project")

    assert result == PROJECT_SPECIFIC_TASKS_PARSED_RESPONSE
    mock_get_projects.assert_called_once_with(context=tool_context)
    mock_get_tasks_by_project_id.assert_called_once_with(
        context=tool_context, project_id="project_123", limit=50, next_page_token=None
    )


@pytest.mark.asyncio
async def test_get_tasks_by_project_name_not_found(tool_context, mocker) -> None:
    mock_get_projects = mocker.patch("arcade_todoist.tools.projects.get_projects")
    mock_get_projects.return_value = PROJECTS_PARSED_RESPONSE

    with pytest.raises(ProjectNotFoundError) as exc_info:
        await get_tasks_by_project(context=tool_context, project="Nonexistent Project")

    assert "Project not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_tasks_by_project_name_partial_match(tool_context, mocker) -> None:
    mock_get_projects = mocker.patch("arcade_todoist.tools.projects.get_projects")
    mock_get_projects.return_value = PROJECTS_PARSED_RESPONSE

    with pytest.raises(ProjectNotFoundError) as exc_info:
        await get_tasks_by_project(context=tool_context, project="Work")

    assert "Project not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_all_tasks_with_custom_limit(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SINGLE_TASK_API_RESPONSE
    httpx_mock.get.return_value = mock_response

    result = await get_all_tasks(context=tool_context, limit=25)

    assert result == SINGLE_TASK_PARSED_RESPONSE
    httpx_mock.get.assert_called_once()

    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {"limit": 25}


@pytest.mark.asyncio
async def test_get_all_tasks_with_pagination(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = TASKS_WITH_PAGINATION_API_RESPONSE
    httpx_mock.get.return_value = mock_response

    result = await get_all_tasks(context=tool_context, next_page_token="page_token_123")  # noqa: S106

    assert result == TASKS_WITH_PAGINATION_PARSED_RESPONSE
    httpx_mock.get.assert_called_once()

    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {"limit": 50, "cursor": "page_token_123"}


@pytest.mark.asyncio
async def test_get_tasks_by_project_id_with_custom_limit(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = CUSTOM_LIMIT_TASK_API_RESPONSE
    httpx_mock.get.return_value = mock_response

    result = await _get_tasks_by_project_id(
        context=tool_context, project_id="project_123", limit=100
    )

    assert result == CUSTOM_LIMIT_TASK_PARSED_RESPONSE
    httpx_mock.get.assert_called_once()

    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {"limit": 100, "project_id": "project_123"}


@pytest.mark.asyncio
async def test_get_tasks_by_project_id_with_pagination(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = PAGINATED_TASKS_API_RESPONSE
    httpx_mock.get.return_value = mock_response

    result = await _get_tasks_by_project_id(
        context=tool_context,
        project_id="project_123",
        limit=25,
        next_page_token="previous_page_token",  # noqa: S106
    )

    assert result == PAGINATED_TASKS_PARSED_RESPONSE
    httpx_mock.get.assert_called_once()

    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {
        "limit": 25,
        "cursor": "previous_page_token",
        "project_id": "project_123",
    }


@pytest.mark.asyncio
async def test_get_tasks_by_project_name_with_pagination(tool_context, mocker) -> None:
    mock_get_projects = mocker.patch("arcade_todoist.tools.projects.get_projects")
    mock_get_projects.return_value = PROJECTS_PARSED_RESPONSE

    mock_get_tasks_by_project_id = mocker.patch(
        "arcade_todoist.tools.tasks._get_tasks_by_project_id"
    )
    mock_get_tasks_by_project_id.return_value = PAGINATED_TASKS_PARSED_RESPONSE

    result = await get_tasks_by_project(
        context=tool_context,
        project="Work Project",
        limit=10,
        next_page_token="some_token",  # noqa: S106
    )

    assert result == PAGINATED_TASKS_PARSED_RESPONSE
    mock_get_projects.assert_called_once_with(context=tool_context)
    mock_get_tasks_by_project_id.assert_called_once_with(
        context=tool_context,
        project_id="project_123",
        limit=10,
        next_page_token="some_token",  # noqa: S106
    )


@pytest.mark.asyncio
async def test_get_tasks_by_project_with_id(tool_context, mocker) -> None:
    mock_get_projects = mocker.patch("arcade_todoist.tools.projects.get_projects")
    mock_get_projects.return_value = PROJECTS_PARSED_RESPONSE

    mock_get_tasks_by_project_id = mocker.patch(
        "arcade_todoist.tools.tasks._get_tasks_by_project_id"
    )
    mock_get_tasks_by_project_id.return_value = CUSTOM_LIMIT_TASK_PARSED_RESPONSE

    result = await get_tasks_by_project(context=tool_context, project="project_123")

    assert result == CUSTOM_LIMIT_TASK_PARSED_RESPONSE
    mock_get_projects.assert_called_once_with(context=tool_context)
    mock_get_tasks_by_project_id.assert_called_once_with(
        context=tool_context, project_id="project_123", limit=50, next_page_token=None
    )


@pytest.mark.asyncio
async def test_get_tasks_by_project_with_name(tool_context, mocker) -> None:
    mock_get_projects = mocker.patch("arcade_todoist.tools.projects.get_projects")
    mock_get_projects.return_value = PROJECTS_PARSED_RESPONSE

    mock_get_tasks_by_project_id = mocker.patch(
        "arcade_todoist.tools.tasks._get_tasks_by_project_id"
    )
    mock_get_tasks_by_project_id.return_value = CUSTOM_LIMIT_TASK_PARSED_RESPONSE

    result = await get_tasks_by_project(context=tool_context, project="Work Project")

    assert result == CUSTOM_LIMIT_TASK_PARSED_RESPONSE
    mock_get_projects.assert_called_once_with(context=tool_context)
    mock_get_tasks_by_project_id.assert_called_once_with(
        context=tool_context, project_id="project_123", limit=50, next_page_token=None
    )


@pytest.mark.asyncio
async def test_create_task_with_project_id(tool_context, mocker) -> None:
    mock_get_projects = mocker.patch("arcade_todoist.tools.projects.get_projects")
    mock_get_projects.return_value = PROJECTS_PARSED_RESPONSE

    mock_create_task_in_project = mocker.patch("arcade_todoist.tools.tasks._create_task_in_project")
    mock_create_task_in_project.return_value = CREATE_TASK_PARSED_RESPONSE

    result = await create_task(context=tool_context, description="New Task", project="project_123")

    assert result == CREATE_TASK_PARSED_RESPONSE
    mock_get_projects.assert_called_once_with(context=tool_context)
    mock_create_task_in_project.assert_called_once_with(
        context=tool_context, description="New Task", project_id="project_123"
    )


@pytest.mark.asyncio
async def test_close_task_with_task_id(tool_context, mocker) -> None:
    mock_close_task_by_task_id = mocker.patch("arcade_todoist.tools.tasks._close_task_by_task_id")
    mock_close_task_by_task_id.return_value = CLOSE_TASK_SUCCESS_RESPONSE

    result = await close_task(context=tool_context, task_id="1")

    assert result == CLOSE_TASK_SUCCESS_RESPONSE
    mock_close_task_by_task_id.assert_called_once_with(context=tool_context, task_id="1")


@pytest.mark.asyncio
async def test_delete_task_with_task_id(tool_context, mocker) -> None:
    mock_delete_task_by_task_id = mocker.patch("arcade_todoist.tools.tasks._delete_task_by_task_id")
    mock_delete_task_by_task_id.return_value = DELETE_TASK_SUCCESS_RESPONSE

    result = await delete_task(context=tool_context, task_id="3")

    assert result == DELETE_TASK_SUCCESS_RESPONSE
    mock_delete_task_by_task_id.assert_called_once_with(context=tool_context, task_id="3")


@pytest.mark.asyncio
async def test_get_tasks_by_filter_success(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SINGLE_TASK_API_RESPONSE
    httpx_mock.get.return_value = mock_response

    result = await get_tasks_by_filter(context=tool_context, filter_query="today")

    assert result == SINGLE_TASK_PARSED_RESPONSE
    httpx_mock.get.assert_called_once()

    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {"query": "today", "limit": 50}


@pytest.mark.asyncio
async def test_get_tasks_by_filter_with_pagination(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = TASKS_WITH_PAGINATION_API_RESPONSE
    httpx_mock.get.return_value = mock_response

    result = await get_tasks_by_filter(
        context=tool_context,
        filter_query="p1",
        limit=25,
        next_page_token="page_token_123",  # noqa: S106
    )

    assert result == TASKS_WITH_PAGINATION_PARSED_RESPONSE
    httpx_mock.get.assert_called_once()

    call_args = httpx_mock.get.call_args
    assert call_args[1]["params"] == {"query": "p1", "limit": 25, "cursor": "page_token_123"}


@pytest.mark.asyncio
async def test_get_tasks_by_filter_failure(tool_context, httpx_mock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {}
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Bad Request",
        request=httpx.Request("GET", "http://test.com"),
        response=mock_response,
    )
    httpx_mock.get.return_value = mock_response

    with pytest.raises(ToolExecutionError):
        await get_tasks_by_filter(context=tool_context, filter_query="invalid filter")

    httpx_mock.get.assert_called_once()
