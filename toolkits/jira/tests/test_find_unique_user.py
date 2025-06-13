from collections.abc import Callable

import pytest
from arcade_tdk import ToolContext

from arcade_jira.exceptions import MultipleItemsFoundError, NotFoundError
from arcade_jira.utils import (
    clean_user_dict,
    find_multiple_unique_users,
    find_unique_user,
)


@pytest.mark.asyncio
async def test_find_unique_user_by_id_success(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_user_dict: Callable,
    fake_cloud_name: str,
):
    sample_user = build_user_dict()
    user_response = mock_httpx_response(200, sample_user)
    mock_httpx_client.get.return_value = user_response

    response = await find_unique_user(mock_context, sample_user["accountId"])
    assert response == clean_user_dict(sample_user, fake_cloud_name)


@pytest.mark.asyncio
async def test_find_unique_user_by_name_with_a_single_match(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_user_dict: Callable,
    fake_cloud_name: str,
):
    sample_user = build_user_dict()
    get_user_by_id_response = mock_httpx_response(404, {})
    get_users_without_id_response = mock_httpx_response(200, [sample_user])
    mock_httpx_client.get.side_effect = [get_user_by_id_response, get_users_without_id_response]

    response = await find_unique_user(mock_context, sample_user["displayName"].lower())
    assert response == clean_user_dict(sample_user, fake_cloud_name)


@pytest.mark.asyncio
async def test_find_unique_user_by_name_with_multiple_matches(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_user_dict: Callable,
    generate_random_str: Callable,
):
    user_name = generate_random_str()
    sample_users = [
        build_user_dict(display_name=user_name),
        build_user_dict(display_name=user_name),
    ]
    get_user_by_id_response = mock_httpx_response(404, {})
    get_users_without_id_response = mock_httpx_response(200, sample_users)
    mock_httpx_client.get.side_effect = [get_user_by_id_response, get_users_without_id_response]

    with pytest.raises(MultipleItemsFoundError) as exc:
        await find_unique_user(mock_context, sample_users[0]["displayName"].lower())

    assert sample_users[0]["accountId"] in exc.value.message
    assert sample_users[1]["accountId"] in exc.value.message


@pytest.mark.asyncio
async def test_find_unique_user_by_name_without_matches(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    generate_random_str: Callable,
):
    get_user_by_id_response = mock_httpx_response(404, {})
    get_users_without_id_response = mock_httpx_response(200, [])
    mock_httpx_client.get.side_effect = [get_user_by_id_response, get_users_without_id_response]

    with pytest.raises(NotFoundError):
        await find_unique_user(mock_context, generate_random_str())


@pytest.mark.asyncio
async def test_find_multiple_users_when_all_names_match_one_result(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_user_dict: Callable,
    fake_cloud_name: str,
):
    user1 = build_user_dict()
    user2 = build_user_dict()

    mock_httpx_client.get.side_effect = [
        mock_httpx_response(200, [user1]),
        mock_httpx_response(200, [user2]),
    ]

    response = await find_multiple_unique_users(
        mock_context, [user1["displayName"], user2["displayName"]]
    )

    assert response == [
        clean_user_dict(user1, fake_cloud_name),
        clean_user_dict(user2, fake_cloud_name),
    ]


@pytest.mark.asyncio
async def test_find_multiple_users_when_a_name_match_multiple_results(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_user_dict: Callable,
):
    user1 = build_user_dict()
    user2 = build_user_dict()
    user3 = build_user_dict()

    mock_httpx_client.get.side_effect = [
        mock_httpx_response(200, [user1]),
        mock_httpx_response(200, [user2, user3]),
    ]

    with pytest.raises(MultipleItemsFoundError) as exc:
        await find_multiple_unique_users(mock_context, [user1["displayName"], user2["displayName"]])

    assert user2["accountId"] in exc.value.message
    assert user3["accountId"] in exc.value.message


@pytest.mark.asyncio
async def test_find_multiple_users_when_user_is_not_found_by_name_but_found_by_id(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_user_dict: Callable,
    fake_cloud_name: str,
):
    user1 = build_user_dict()
    user2 = build_user_dict()

    mock_httpx_client.get.side_effect = [
        mock_httpx_response(200, [user1]),
        mock_httpx_response(200, []),
        mock_httpx_response(200, user2),
    ]

    response = await find_multiple_unique_users(
        mock_context, [user1["displayName"], user2["accountId"]]
    )

    assert response == [
        clean_user_dict(user1, fake_cloud_name),
        clean_user_dict(user2, fake_cloud_name),
    ]


@pytest.mark.asyncio
async def test_find_multiple_users_when_various_users_are_not_found_by_name_but_found_by_id(
    mock_context: ToolContext,
    mock_httpx_client,
    mock_httpx_response: Callable,
    build_user_dict: Callable,
    fake_cloud_name: str,
):
    user1 = build_user_dict()
    user2 = build_user_dict()
    user3 = build_user_dict()

    mock_httpx_client.get.side_effect = [
        mock_httpx_response(200, [user1]),
        mock_httpx_response(200, []),
        mock_httpx_response(200, []),
        mock_httpx_response(200, user2),
        mock_httpx_response(200, user3),
    ]

    response = await find_multiple_unique_users(
        mock_context, [user1["displayName"], user2["accountId"], user3["accountId"]]
    )

    assert response == [
        clean_user_dict(user1, fake_cloud_name),
        clean_user_dict(user2, fake_cloud_name),
        clean_user_dict(user3, fake_cloud_name),
    ]
