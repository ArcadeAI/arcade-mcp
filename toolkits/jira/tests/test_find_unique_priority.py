from collections.abc import Callable
from unittest.mock import patch

import pytest
from arcade_tdk import ToolContext

from arcade_jira.exceptions import JiraToolExecutionError, MultipleItemsFoundError, NotFoundError
from arcade_jira.utils import clean_priority_dict, find_unique_priority


@pytest.mark.asyncio
async def test_find_unique_priority_by_id_success(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_priority_dict: Callable,
):
    sample_priority = build_priority_dict()
    priority_response = mock_httpx_response(200, sample_priority)
    mock_httpx_client.get.return_value = priority_response

    response = await find_unique_priority(mock_context, sample_priority["id"], "123")
    assert response == clean_priority_dict(sample_priority)


@pytest.mark.asyncio
@patch("arcade_jira.tools.priorities.find_priorities_by_project")
async def test_find_unique_priority_by_name_with_a_single_match(
    mock_find_priorities_by_project,
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_priority_dict: Callable,
):
    sample_project = build_project_dict()
    sample_priority = build_priority_dict()

    # It will first try to get the priority by ID
    get_priority_by_id_response = mock_httpx_response(404, {})

    # When it tries to get the priority by name, it will first query the project data
    get_project_by_id_response = mock_httpx_response(200, sample_project)

    # Then it will query the priorities available to the project
    mock_find_priorities_by_project.return_value = {
        "project": sample_project,
        "priorities_available": [sample_priority],
    }

    mock_httpx_client.get.side_effect = [
        get_priority_by_id_response,
        get_project_by_id_response,
    ]

    response = await find_unique_priority(
        mock_context, sample_priority["name"].lower(), sample_project["id"]
    )
    assert response == clean_priority_dict(sample_priority)


@pytest.mark.asyncio
@patch("arcade_jira.tools.priorities.find_priorities_by_project")
async def test_find_unique_priority_by_name_when_project_does_not_exist(
    mock_find_priorities_by_project,
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_priority_dict: Callable,
    build_project_search_response_dict: Callable,
):
    sample_project = build_project_dict()
    sample_priority = build_priority_dict()

    # It will first try to get the priority by ID
    get_priority_by_id_response = mock_httpx_response(404, {})

    # When it tries to get the project by id, we'll simulate a 404 error
    get_project_by_id_response = mock_httpx_response(404, {})

    # And also simulate no results found from search_projects
    search_projects_response = mock_httpx_response(200, build_project_search_response_dict([]))

    # We'll still simulate a find_priorities_by_project response, but this should not be called
    mock_find_priorities_by_project.return_value = {
        "project": sample_project,
        "priorities_available": [sample_priority],
    }

    mock_httpx_client.get.side_effect = [
        get_priority_by_id_response,
        get_project_by_id_response,
        search_projects_response,
    ]

    with pytest.raises(JiraToolExecutionError) as exc:
        await find_unique_priority(
            mock_context, sample_priority["name"].lower(), sample_project["id"]
        )

    mock_find_priorities_by_project.assert_not_called()
    assert f"Project not found with name/key/ID '{sample_project['id']}'" in exc.value.message


@pytest.mark.asyncio
@patch("arcade_jira.tools.priorities.find_priorities_by_project")
async def test_find_unique_priority_by_name_with_multiple_priorities_but_zero_matches(
    mock_find_priorities_by_project,
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_priority_dict: Callable,
):
    sample_project = build_project_dict()

    sample_priority = build_priority_dict()
    other_priority1 = build_priority_dict(name=sample_priority["name"] + "1")
    other_priority2 = build_priority_dict(name=sample_priority["name"] + "2")

    # It will first try to get the priority by ID
    get_priority_by_id_response = mock_httpx_response(404, {})

    # When it tries to get the priority by name, it will first query the project data
    get_project_by_id_response = mock_httpx_response(200, sample_project)

    # Then it will query the priorities available to the project
    mock_find_priorities_by_project.return_value = {
        "project": sample_project,
        "priorities_available": [other_priority1, other_priority2],
    }

    mock_httpx_client.get.side_effect = [
        get_priority_by_id_response,
        get_project_by_id_response,
    ]

    with pytest.raises(NotFoundError) as exc:
        await find_unique_priority(
            mock_context, sample_priority["name"].lower(), sample_project["id"]
        )

    assert (
        f"Priority not found with ID or name '{sample_priority['name'].lower()}'"
        == exc.value.message
    )


@pytest.mark.asyncio
@patch("arcade_jira.tools.priorities.find_priorities_by_project")
async def test_find_unique_priority_by_name_with_multiple_priorities_but_one_match(
    mock_find_priorities_by_project,
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_priority_dict: Callable,
):
    sample_project = build_project_dict()
    sample_priority = build_priority_dict()
    other_priority1 = build_priority_dict()
    other_priority2 = build_priority_dict()

    # It will first try to get the priority by ID
    get_priority_by_id_response = mock_httpx_response(404, {})

    # When it tries to get the priority by name, it will first query the project data
    get_project_by_id_response = mock_httpx_response(200, sample_project)

    # Then it will query the priorities available to the project
    mock_find_priorities_by_project.return_value = {
        "project": sample_project,
        "priorities_available": [sample_priority, other_priority1, other_priority2],
    }

    mock_httpx_client.get.side_effect = [
        get_priority_by_id_response,
        get_project_by_id_response,
    ]

    response = await find_unique_priority(
        mock_context, sample_priority["name"].lower(), sample_project["id"]
    )
    assert response == clean_priority_dict(sample_priority)


@pytest.mark.asyncio
@patch("arcade_jira.tools.priorities.find_priorities_by_project")
async def test_find_unique_priority_by_name_with_multiple_priorities_and_multiple_matches(
    mock_find_priorities_by_project,
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_priority_dict: Callable,
):
    sample_project = build_project_dict()
    sample_priority = build_priority_dict()
    other_priority1 = build_priority_dict(name=sample_priority["name"])
    other_priority2 = build_priority_dict()

    # It will first try to get the priority by ID
    get_priority_by_id_response = mock_httpx_response(404, {})

    # When it tries to get the priority by name, it will first query the project data
    get_project_by_id_response = mock_httpx_response(200, sample_project)

    # Then it will query the priorities available to the project
    mock_find_priorities_by_project.return_value = {
        "project": sample_project,
        "priorities_available": [sample_priority, other_priority1, other_priority2],
    }

    mock_httpx_client.get.side_effect = [
        get_priority_by_id_response,
        get_project_by_id_response,
    ]

    with pytest.raises(MultipleItemsFoundError) as exc:
        await find_unique_priority(
            mock_context, sample_priority["name"].lower(), sample_project["id"]
        )

    assert sample_priority["id"] in exc.value.message
    assert other_priority1["id"] in exc.value.message
    assert other_priority2["id"] not in exc.value.message
