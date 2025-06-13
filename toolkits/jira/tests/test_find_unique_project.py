from collections.abc import Callable

import pytest
from arcade_tdk import ToolContext

from arcade_jira.exceptions import MultipleItemsFoundError, NotFoundError
from arcade_jira.utils import clean_project_dict, find_unique_project


@pytest.mark.asyncio
async def test_find_unique_project_by_id_success(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    fake_cloud_name: str,
):
    sample_project = build_project_dict()
    project_response = mock_httpx_response(200, sample_project)
    mock_httpx_client.get.return_value = project_response

    response = await find_unique_project(mock_context, sample_project["id"])
    assert response == clean_project_dict(sample_project, fake_cloud_name)


@pytest.mark.asyncio
async def test_find_unique_project_by_name_with_a_single_match(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_project_search_response_dict: Callable,
    fake_cloud_name: str,
):
    sample_project = build_project_dict()
    get_project_by_id_response = mock_httpx_response(404, {})
    get_projects_without_id_response = mock_httpx_response(
        200, build_project_search_response_dict([sample_project])
    )
    mock_httpx_client.get.side_effect = [
        get_project_by_id_response,
        get_projects_without_id_response,
    ]

    response = await find_unique_project(mock_context, sample_project["name"].lower())
    assert response == clean_project_dict(sample_project, fake_cloud_name)


@pytest.mark.asyncio
async def test_find_unique_project_by_name_with_multiple_matches(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_project_search_response_dict: Callable,
    generate_random_str: Callable,
):
    project_name = generate_random_str()
    sample_projects = [
        build_project_dict(name=project_name),
        build_project_dict(name=project_name),
    ]
    get_project_by_id_response = mock_httpx_response(404, {})
    search_projects_response = mock_httpx_response(
        200, build_project_search_response_dict(sample_projects)
    )
    mock_httpx_client.get.side_effect = [
        get_project_by_id_response,
        search_projects_response,
    ]

    with pytest.raises(MultipleItemsFoundError) as exc:
        await find_unique_project(mock_context, sample_projects[0]["name"].lower())

    assert sample_projects[0]["id"] in exc.value.message
    assert sample_projects[1]["id"] in exc.value.message


@pytest.mark.asyncio
async def test_find_unique_project_by_name_without_matches(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    generate_random_str: Callable,
    build_project_search_response_dict: Callable,
):
    get_project_by_id_response = mock_httpx_response(404, {})
    search_projects_response = mock_httpx_response(200, build_project_search_response_dict([]))
    mock_httpx_client.get.side_effect = [
        get_project_by_id_response,
        search_projects_response,
    ]

    with pytest.raises(NotFoundError):
        await find_unique_project(mock_context, generate_random_str())
