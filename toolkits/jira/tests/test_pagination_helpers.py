from collections.abc import Callable

import pytest
from arcade_tdk import ToolContext

from arcade_jira.exceptions import JiraToolExecutionError
from arcade_jira.tools.priorities import list_projects_associated_with_a_priority_scheme
from arcade_jira.utils import add_pagination_to_response, clean_project_dict, paginate_all_items


@pytest.mark.asyncio
async def test_paginate_all_items_with_zero_matches(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_search_response_dict: Callable,
):
    response = mock_httpx_response(200, build_project_search_response_dict([], is_last=True))
    mock_httpx_client.get.return_value = response

    response = await paginate_all_items(
        context=mock_context,
        tool=list_projects_associated_with_a_priority_scheme,
        response_items_key="projects",
        scheme_id="123",
    )
    assert response == []


@pytest.mark.asyncio
async def test_paginate_all_items_with_one_page(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_project_search_response_dict: Callable,
    fake_cloud_name: str,
):
    projects = [build_project_dict(), build_project_dict()]
    response = mock_httpx_response(200, build_project_search_response_dict(projects, is_last=True))
    mock_httpx_client.get.return_value = response

    response = await paginate_all_items(
        context=mock_context,
        tool=list_projects_associated_with_a_priority_scheme,
        response_items_key="projects",
        scheme_id="123",
    )
    assert response == [clean_project_dict(project, fake_cloud_name) for project in projects]


@pytest.mark.asyncio
async def test_paginate_all_items_with_multiple_pages(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_project_search_response_dict: Callable,
    fake_cloud_name: str,
):
    page1 = [build_project_dict(), build_project_dict()]
    page2 = [build_project_dict(), build_project_dict()]
    page3 = [build_project_dict()]

    response1 = mock_httpx_response(200, build_project_search_response_dict(page1, is_last=False))
    response2 = mock_httpx_response(200, build_project_search_response_dict(page2, is_last=False))
    response3 = mock_httpx_response(200, build_project_search_response_dict(page3, is_last=True))

    mock_httpx_client.get.side_effect = [response1, response2, response3]

    response = await paginate_all_items(
        context=mock_context,
        tool=list_projects_associated_with_a_priority_scheme,
        response_items_key="projects",
        scheme_id="123",
        limit=2,
    )
    assert response == [
        clean_project_dict(project, fake_cloud_name) for project in page1 + page2 + page3
    ]


@pytest.mark.asyncio
async def test_paginate_all_items_when_tool_returns_error(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_search_response_dict: Callable,
):
    project_id = "456"
    get_project_by_id_response = mock_httpx_response(404, {})
    search_projects_response = mock_httpx_response(200, build_project_search_response_dict([]))
    mock_httpx_client.get.side_effect = [get_project_by_id_response, search_projects_response]

    with pytest.raises(JiraToolExecutionError) as exc:
        await paginate_all_items(
            context=mock_context,
            tool=list_projects_associated_with_a_priority_scheme,
            response_items_key="projects",
            scheme_id="123",
            project=project_id,
            limit=2,
        )

    assert exc.value.message == f"Project not found with name/key/ID '{project_id}'"


def test_add_pagination_to_response_with_zero_items():
    response = {"items": []}
    items = []
    limit = 10
    offset = 0
    add_pagination_to_response(response, items, limit, offset)
    assert response["pagination"] == {"is_last_page": True, "limit": limit, "total_results": 0}


def test_add_pagination_to_response_with_last_page_false():
    items = [{"id": "123"}, {"id": "456"}]
    response = {"items": items, "isLast": False}
    limit = 2
    offset = 0
    add_pagination_to_response(response, items, limit, offset)
    assert response["pagination"] == {
        "limit": limit,
        "total_results": 2,
        "next_offset": 2,
    }


def test_add_pagination_to_response_with_last_page_true():
    items = [{"id": "123"}, {"id": "456"}]
    response = {"items": items, "isLast": True}
    limit = 2
    offset = 0
    add_pagination_to_response(response, items, limit, offset)
    assert response["pagination"] == {
        "limit": limit,
        "total_results": 2,
        "is_last_page": True,
    }


def test_add_pagination_to_response_without_last_page_and_limit_equal_items():
    items = [{"id": "123"}, {"id": "456"}]
    response = {"items": items}
    limit = 2
    offset = 0
    add_pagination_to_response(response, items, limit, offset)
    assert response["pagination"] == {
        "limit": limit,
        "total_results": 2,
        "next_offset": 2,
    }


def test_add_pagination_to_response_without_last_page_and_less_items_than_limit():
    items = [{"id": "123"}]
    response = {"items": items}
    limit = 2
    offset = 0
    add_pagination_to_response(response, items, limit, offset)
    assert response["pagination"] == {
        "limit": limit,
        "total_results": 1,
        "is_last_page": True,
    }
