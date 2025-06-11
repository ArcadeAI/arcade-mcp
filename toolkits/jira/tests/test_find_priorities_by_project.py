from collections.abc import Callable

import httpx
import pytest
from arcade_tdk import ToolContext

from arcade_jira.exceptions import NotFoundError
from arcade_jira.utils import clean_priority_dict, find_priorities_by_project


@pytest.mark.asyncio
async def test_find_priorities_by_project_with_no_priority_schemes(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
):
    list_priority_schemes_response = mock_httpx_response(
        200,
        {
            "values": [],
            "isLast": True,
        },
    )
    mock_httpx_client.get.return_value = list_priority_schemes_response

    with pytest.raises(NotFoundError) as exc:
        await find_priorities_by_project(mock_context, {})

    assert "No priority schemes found" in exc.value.message


@pytest.mark.asyncio
async def test_find_priorities_by_project_when_project_does_not_exist(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_priority_scheme_dict: Callable,
):
    sample_project = build_project_dict()
    priority_scheme = build_priority_scheme_dict()
    list_priority_schemes_response = mock_httpx_response(
        200,
        {"values": [priority_scheme], "isLast": True},
    )

    find_project_by_id_response = mock_httpx_response(404, {})
    search_projects_response = mock_httpx_response(200, {"values": [], "isLast": True})

    mock_httpx_client.get.side_effect = [
        list_priority_schemes_response,
        find_project_by_id_response,
        search_projects_response,
    ]

    response = await find_priorities_by_project(mock_context, sample_project)

    assert response == {"error": f"Project not found with name/key/ID '{sample_project['id']}'"}


@pytest.mark.asyncio
async def test_find_priorities_by_project_when_project_is_found_but_does_not_match_id(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_priority_scheme_dict: Callable,
):
    sample_project = build_project_dict()
    other_project = build_project_dict(name=sample_project["name"])

    priority_scheme = build_priority_scheme_dict()
    list_priority_schemes_response = mock_httpx_response(
        200,
        {"values": [priority_scheme], "isLast": True},
    )

    find_project_by_id_response = mock_httpx_response(404, {})

    search_projects_response = mock_httpx_response(
        200,
        {"values": [other_project], "isLast": True},
    )

    list_projects_response = mock_httpx_response(
        200,
        {"values": [other_project], "isLast": True},
    )

    mock_httpx_client.get.side_effect = [
        list_priority_schemes_response,
        find_project_by_id_response,
        search_projects_response,
        list_projects_response,
    ]

    response = await find_priorities_by_project(mock_context, sample_project)

    assert response == {
        "error": f"No priority schemes found for the project {sample_project['id']}"
    }


@pytest.mark.asyncio
async def test_find_priorities_by_project_happy_path(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_priority_dict: Callable,
    build_priority_scheme_dict: Callable,
):
    sample_project = build_project_dict()
    other_project = build_project_dict(name=sample_project["name"])

    priority_scheme = build_priority_scheme_dict()
    priority1 = build_priority_dict()
    priority2 = build_priority_dict()

    list_priority_schemes_response = mock_httpx_response(
        200,
        {"values": [priority_scheme], "isLast": True},
    )

    find_project_by_id_response = mock_httpx_response(404, {})

    search_projects_response = mock_httpx_response(
        200,
        {"values": [sample_project], "isLast": True},
    )

    list_projects_response = mock_httpx_response(
        200,
        {"values": [sample_project, other_project], "isLast": True},
    )

    list_priorities_response = mock_httpx_response(
        200,
        {"values": [priority1, priority2], "isLast": True},
    )

    mock_httpx_client.get.side_effect = [
        list_priority_schemes_response,
        find_project_by_id_response,
        search_projects_response,
        list_projects_response,
        list_priorities_response,
    ]

    response = await find_priorities_by_project(mock_context, sample_project)

    assert response["priorities_available"] == [
        clean_priority_dict(priority1),
        clean_priority_dict(priority2),
    ]


@pytest.mark.asyncio
async def test_find_priorities_by_project_happy_path_with_repeated_priorities_across_schemes(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_priority_dict: Callable,
    build_priority_scheme_dict: Callable,
):
    sample_project = build_project_dict()
    other_project = build_project_dict(name=sample_project["name"])

    priority_scheme1 = build_priority_scheme_dict()
    priority_scheme2 = build_priority_scheme_dict()

    priority1 = build_priority_dict()
    priority2 = build_priority_dict()
    priority3 = build_priority_dict()

    list_priority_schemes_response = mock_httpx_response(
        200,
        {"values": [priority_scheme1, priority_scheme2], "isLast": True},
    )

    find_project_by_id_response = mock_httpx_response(200, sample_project)

    list_projects_by_priority_scheme_response1 = mock_httpx_response(
        200,
        {"values": [sample_project, other_project], "isLast": True},
    )
    list_projects_by_priority_scheme_response2 = mock_httpx_response(
        200,
        {"values": [sample_project], "isLast": True},
    )

    list_priorities_by_scheme_response1 = mock_httpx_response(
        200,
        {"values": [priority1, priority2], "isLast": True},
    )
    list_priorities_by_scheme_response2 = mock_httpx_response(
        200,
        {"values": [priority2, priority3], "isLast": True},
    )

    def get_httpx_response(url: str, *args, **kwargs) -> httpx.Response:
        if url.endswith("/priorityscheme"):
            return list_priority_schemes_response
        elif url.endswith(f"/project/{sample_project['id']}"):
            return find_project_by_id_response
        elif url.endswith(f"/priorityscheme/{priority_scheme1['id']}/projects"):
            return list_projects_by_priority_scheme_response1
        elif url.endswith(f"/priorityscheme/{priority_scheme2['id']}/projects"):
            return list_projects_by_priority_scheme_response2
        elif url.endswith(f"/priorityscheme/{priority_scheme1['id']}/priorities"):
            return list_priorities_by_scheme_response1
        elif url.endswith(f"/priorityscheme/{priority_scheme2['id']}/priorities"):
            return list_priorities_by_scheme_response2
        else:
            raise ValueError(f"Unexpected URL: {url}")  # noqa: TRY003

    mock_httpx_client.get.side_effect = get_httpx_response

    response = await find_priorities_by_project(mock_context, sample_project)

    assert len(response["priorities_available"]) == 3
    assert clean_priority_dict(priority1) in response["priorities_available"]
    assert clean_priority_dict(priority2) in response["priorities_available"]
    assert clean_priority_dict(priority3) in response["priorities_available"]
