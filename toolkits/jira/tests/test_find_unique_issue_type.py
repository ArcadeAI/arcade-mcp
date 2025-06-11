import json
from collections.abc import Callable

import pytest
from arcade_tdk import ToolContext

from arcade_jira.exceptions import JiraToolExecutionError, MultipleItemsFoundError, NotFoundError
from arcade_jira.utils import clean_issue_type_dict, find_unique_issue_type


@pytest.mark.asyncio
async def test_find_unique_issue_type_by_id_success(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_issue_type_dict: Callable,
):
    sample_issue_type = build_issue_type_dict()
    issue_type_response = mock_httpx_response(200, sample_issue_type)
    mock_httpx_client.get.return_value = issue_type_response

    response = await find_unique_issue_type(mock_context, sample_issue_type["id"], "123")
    assert response == clean_issue_type_dict(sample_issue_type)


@pytest.mark.asyncio
async def test_find_unique_issue_type_by_name_with_a_single_match(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_issue_type_dict: Callable,
    build_project_dict: Callable,
    build_issue_types_response_dict: Callable,
):
    sample_project = build_project_dict()
    sample_issue_type = build_issue_type_dict()

    # It will first try to get the issue type by ID, we simulate a not found response
    get_issue_type_by_id_response = mock_httpx_response(404, {})

    # When it tries to get the issue type by name, it will first query the project data
    get_project_by_id_response = mock_httpx_response(200, sample_project)

    # Then it will query the issue types available to the project
    list_issue_types_response = mock_httpx_response(
        200, build_issue_types_response_dict([sample_issue_type], is_last=True)
    )

    mock_httpx_client.get.side_effect = [
        get_issue_type_by_id_response,
        get_project_by_id_response,
        list_issue_types_response,
    ]

    response = await find_unique_issue_type(
        mock_context, sample_issue_type["name"].lower(), sample_project["id"]
    )
    assert response == clean_issue_type_dict(sample_issue_type)


@pytest.mark.asyncio
async def test_find_unique_issue_type_by_name_when_project_does_not_exist(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_issue_type_dict: Callable,
    build_issue_types_response_dict: Callable,
    build_project_search_response_dict: Callable,
):
    sample_project = build_project_dict()
    sample_issue_type = build_issue_type_dict()

    # It will first try to get the issue type by ID
    get_issue_type_by_id_response = mock_httpx_response(404, {})

    # When it tries to get the project by id, we'll simulate a 404 error
    get_project_by_id_response = mock_httpx_response(404, {})

    # And also simulate no results found from search_projects
    search_projects_response = mock_httpx_response(200, build_project_search_response_dict([]))

    mock_httpx_client.get.side_effect = [
        get_issue_type_by_id_response,
        get_project_by_id_response,
        search_projects_response,
    ]

    with pytest.raises(JiraToolExecutionError) as exc:
        await find_unique_issue_type(
            mock_context, sample_issue_type["name"].lower(), sample_project["id"]
        )

    assert f"Project not found with name/key/ID '{sample_project['id']}'" in exc.value.message


@pytest.mark.asyncio
async def test_find_unique_issue_type_by_name_with_multiple_priorities_but_zero_matches(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_issue_type_dict: Callable,
    build_issue_types_response_dict: Callable,
):
    sample_project = build_project_dict()

    sample_issue_type = build_issue_type_dict()
    other_issue_type1 = build_issue_type_dict(name=sample_issue_type["name"] + "1")
    other_issue_type2 = build_issue_type_dict(name=sample_issue_type["name"] + "2")

    # It will first try to get the issue type by ID
    get_issue_type_by_id_response = mock_httpx_response(404, {})

    # When it tries to get the issue type by name, it will first query the project data
    get_project_by_id_response = mock_httpx_response(200, sample_project)

    # Then it will query the issue types available to the project
    search_issue_types_response = mock_httpx_response(
        200, build_issue_types_response_dict([other_issue_type1, other_issue_type2], is_last=True)
    )

    mock_httpx_client.get.side_effect = [
        get_issue_type_by_id_response,
        get_project_by_id_response,
        search_issue_types_response,
    ]

    with pytest.raises(NotFoundError) as exc:
        await find_unique_issue_type(
            mock_context, sample_issue_type["name"].lower(), sample_project["id"]
        )

    available_issue_types = json.dumps([
        {
            "id": other_issue_type1["id"],
            "name": other_issue_type1["name"],
        },
        {
            "id": other_issue_type2["id"],
            "name": other_issue_type2["name"],
        },
    ])

    assert (
        f"Issue type not found with ID or name '{sample_issue_type['name'].lower()}'. "
        f"These are the issue types available for the project: {available_issue_types}"
        == exc.value.message
    )


@pytest.mark.asyncio
async def test_find_unique_issue_type_by_name_with_multiple_issue_types_but_one_match(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_issue_type_dict: Callable,
    build_issue_types_response_dict: Callable,
):
    sample_project = build_project_dict()
    sample_issue_type = build_issue_type_dict()
    other_issue_type1 = build_issue_type_dict(name=sample_issue_type["name"] + "1")
    other_issue_type2 = build_issue_type_dict(name=sample_issue_type["name"] + "2")

    # It will first try to get the issue type by ID
    get_issue_type_by_id_response = mock_httpx_response(404, {})

    # When it tries to get the priority by name, it will first query the project data
    get_project_by_id_response = mock_httpx_response(200, sample_project)

    # Then it will query the issue types available to the project
    search_issue_types_response = mock_httpx_response(
        200,
        build_issue_types_response_dict(
            [sample_issue_type, other_issue_type1, other_issue_type2],
            is_last=True,
        ),
    )

    mock_httpx_client.get.side_effect = [
        get_issue_type_by_id_response,
        get_project_by_id_response,
        search_issue_types_response,
    ]

    response = await find_unique_issue_type(
        mock_context, sample_issue_type["name"].lower(), sample_project["id"]
    )
    assert response == clean_issue_type_dict(sample_issue_type)


@pytest.mark.asyncio
async def test_find_unique_issue_type_by_name_with_multiple_issue_types_and_multiple_matches(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_project_dict: Callable,
    build_issue_type_dict: Callable,
    build_issue_types_response_dict: Callable,
):
    sample_project = build_project_dict()
    sample_issue_type = build_issue_type_dict()
    other_issue_type1 = build_issue_type_dict(name=sample_issue_type["name"])
    other_issue_type2 = build_issue_type_dict()

    # It will first try to get the issue type by ID
    get_issue_type_by_id_response = mock_httpx_response(404, {})

    # When it tries to get the priority by name, it will first query the project data
    get_project_by_id_response = mock_httpx_response(200, sample_project)

    # Then it will query the issue types available to the project
    search_issue_types_response = mock_httpx_response(
        200,
        build_issue_types_response_dict(
            [sample_issue_type, other_issue_type1, other_issue_type2],
            is_last=True,
        ),
    )

    mock_httpx_client.get.side_effect = [
        get_issue_type_by_id_response,
        get_project_by_id_response,
        search_issue_types_response,
    ]

    with pytest.raises(MultipleItemsFoundError) as exc:
        await find_unique_issue_type(
            mock_context, sample_issue_type["name"].lower(), sample_project["id"]
        )

    assert sample_issue_type["id"] in exc.value.message
    assert other_issue_type1["id"] in exc.value.message
    assert other_issue_type2["id"] not in exc.value.message
