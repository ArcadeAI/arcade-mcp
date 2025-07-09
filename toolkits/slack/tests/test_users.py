import json
from unittest.mock import patch

import pytest
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError

from arcade_slack.tools.users import (
    get_users_info,
    list_users,
)
from arcade_slack.utils import extract_basic_user_info, short_user_info


@pytest.mark.asyncio
async def test_get_user_info_by_id_success(mock_context, mock_user_retrieval_slack_client):
    # Mock the response from slackClient.users_info
    mock_user = {
        "id": "U12345",
        "name": "testuser",
        "real_name": "Test User",
        "profile": {"email": "testuser@example.com"},
    }
    mock_user_retrieval_slack_client.users_info.return_value = {"ok": True, "user": mock_user}

    response = await get_users_info(mock_context, user_ids=["U12345"])

    mock_user_retrieval_slack_client.users_info.assert_called_once_with(user="U12345")

    expected_response = extract_basic_user_info(mock_user)
    assert response == {"users": [expected_response]}


@pytest.mark.asyncio
@patch("arcade_slack.tools.users.list_users")
async def test_get_user_info_by_id_user_not_found(
    mock_list_users, mock_context, mock_user_retrieval_slack_client
):
    error_response = {"ok": False, "error": "user_not_found"}
    mock_user_retrieval_slack_client.users_info.side_effect = SlackApiError(
        message="User not found",
        response=error_response,
    )

    existing_user = {"id": "U12345", "name": "testuser"}
    mock_list_users.return_value = {"users": [existing_user]}
    mock_list_users.__tool_name__ = list_users.__tool_name__

    with pytest.raises(RetryableToolError) as e:
        await get_users_info(mock_context, user_ids=["U99999"])

        assert existing_user["id"] in e.value.additional_prompt_content

    mock_user_retrieval_slack_client.users_info.assert_called_once_with(user="U99999")
    mock_list_users.assert_called_once_with(mock_context, limit=100, exclude_bots=True)


@pytest.mark.asyncio
async def test_list_users_success(mock_context, mock_users_slack_client):
    mock_users_slack_client.users_list.return_value = {
        "ok": True,
        "members": [{"id": "U12345"}],
    }
    response = await list_users(mock_context)
    assert response == {
        "users": [extract_basic_user_info({"id": "U12345"})],
        "next_cursor": None,
    }


@pytest.mark.asyncio
async def test_list_users_with_pagination_success(
    dummy_user_factory, mock_context, mock_users_slack_client
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()
    user3 = dummy_user_factory()
    user4 = dummy_user_factory()

    mock_users_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [user1, user2],
            "response_metadata": {"next_cursor": "cursor_xyz"},
        },
        {
            "ok": True,
            "members": [user3, user4],
            "response_metadata": {"next_cursor": None},
        },
    ]
    response = await list_users(mock_context, limit=3)
    assert response == {
        "users": [
            extract_basic_user_info(user1),
            extract_basic_user_info(user2),
            extract_basic_user_info(user3),
            extract_basic_user_info(user4),
        ],
        "next_cursor": None,
    }

    assert mock_users_slack_client.users_list.call_count == 2


@pytest.mark.asyncio
async def test_get_user_by_username_success(
    mock_context,
    mock_user_retrieval_slack_client,
    dummy_user_factory,
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()

    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [user1, user2],
    }

    response = await get_users_info(mock_context, usernames=[user1["name"]])

    assert response == {"users": [extract_basic_user_info(user1)]}


@pytest.mark.asyncio
async def test_get_user_by_username_with_pagination_success(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()
    user3 = dummy_user_factory()
    user4 = dummy_user_factory()
    user5 = dummy_user_factory()

    mock_user_retrieval_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [user1, user2],
            "response_metadata": {"next_cursor": "cursor1"},
        },
        {
            "ok": True,
            "members": [user3, user4],
            "response_metadata": {"next_cursor": "cursor2"},
        },
        {
            "ok": True,
            "members": [user5],
            "response_metadata": {"next_cursor": None},
        },
    ]

    response = await get_users_info(mock_context, usernames=[user3["name"]])

    assert response == {"users": [extract_basic_user_info(user3)]}

    assert mock_user_retrieval_slack_client.users_list.call_count == 2


@pytest.mark.asyncio
async def test_get_user_by_username_not_found(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()
    user3 = dummy_user_factory(is_bot=True)

    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [user1, user2, user3],
    }

    with pytest.raises(RetryableToolError) as e:
        await get_users_info(mock_context, usernames=[user1["name"] + "not_found"])

    # Check that the error message contains the available users
    assert user1["id"] in e.value.additional_prompt_content
    assert user2["id"] in e.value.additional_prompt_content
    assert user3["id"] not in e.value.additional_prompt_content


@pytest.mark.asyncio
async def test_get_multiple_users_by_username_success(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()
    user3 = dummy_user_factory()

    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [user1, user2, user3],
    }

    response = await get_users_info(
        mock_context,
        usernames=[user1["name"], user2["name"]],
    )

    assert response == {
        "users": [
            extract_basic_user_info(user1),
            extract_basic_user_info(user2),
        ]
    }


@pytest.mark.asyncio
async def test_get_multiple_users_by_username_with_pagination_success(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()
    user3 = dummy_user_factory()
    user4 = dummy_user_factory()
    user5 = dummy_user_factory()

    mock_user_retrieval_slack_client.users_list.side_effect = [
        {"ok": True, "members": [user1, user2], "response_metadata": {"next_cursor": "cursor1"}},
        {"ok": True, "members": [user3, user4], "response_metadata": {"next_cursor": "cursor2"}},
        {"ok": True, "members": [user5], "response_metadata": {"next_cursor": None}},
    ]

    response = await get_users_info(mock_context, usernames=[user1["name"], user3["name"]])

    assert response == {"users": [extract_basic_user_info(user1), extract_basic_user_info(user3)]}
    assert mock_user_retrieval_slack_client.users_list.call_count == 2


@pytest.mark.asyncio
async def test_get_multiple_users_by_username_not_found(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()
    user3 = dummy_user_factory(is_bot=True)

    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [user1, user2, user3],
    }

    not_found_username = f"{user2['name']} not_found"

    with pytest.raises(RetryableToolError) as e:
        await get_users_info(mock_context, usernames=[user1["name"], not_found_username])

    assert user1["id"] in e.value.additional_prompt_content
    assert user2["id"] in e.value.additional_prompt_content
    assert user3["id"] not in e.value.additional_prompt_content


@pytest.mark.asyncio
async def test_get_user_by_email_success(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user = dummy_user_factory()
    mock_user_retrieval_slack_client.users_lookupByEmail.return_value = {
        "ok": True,
        "user": user,
    }
    response = await get_users_info(mock_context, emails=[user["profile"]["email"]])
    assert response == {"users": [extract_basic_user_info(user)]}


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(
    mock_context, mock_users_slack_client, mock_user_retrieval_slack_client, dummy_user_factory
):
    additional_user = dummy_user_factory(email="additional_user@example.com")

    async def lookup_by_email_side_effect(*, email):
        if email == "additional_user@example.com":
            return {"ok": True, "user": additional_user}
        raise SlackApiError(
            message="User not found",
            response={"ok": False, "error": "user_not_found"},
        )

    mock_user_retrieval_slack_client.users_lookupByEmail.side_effect = lookup_by_email_side_effect
    mock_users_slack_client.users_list.return_value = {
        "ok": True,
        "members": [additional_user],
    }

    with pytest.raises(RetryableToolError) as e:
        await get_users_info(mock_context, emails=["not_found@example.com"])

    assert "not_found@example.com" in e.value.message
    assert json.dumps(short_user_info(additional_user)) in e.value.additional_prompt_content


@pytest.mark.asyncio
async def test_get_multiple_users_by_email_success(
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()
    user3 = dummy_user_factory()

    mock_user_retrieval_slack_client.users_lookupByEmail.side_effect = [
        {"ok": True, "user": user1},
        {"ok": True, "user": user2},
        {"ok": True, "user": user3},
    ]

    response = await get_users_info(
        mock_context,
        emails=[
            user1["profile"]["email"],
            user2["profile"]["email"],
            user3["profile"]["email"],
        ],
    )

    assert response == {
        "users": [
            extract_basic_user_info(user1),
            extract_basic_user_info(user2),
            extract_basic_user_info(user3),
        ]
    }


@pytest.mark.asyncio
async def test_get_multiple_users_by_email_with_invalid_address(
    mock_context, mock_user_retrieval_slack_client
):
    with pytest.raises(ToolExecutionError) as e:
        await get_users_info(
            mock_context,
            emails=["amyra@jades.com", "invalid_address"],
        )

    mock_user_retrieval_slack_client.assert_not_called()
    assert e.value.message == "Invalid email address: invalid_address"


@pytest.mark.asyncio
async def test_get_multiple_users_by_email_not_found(
    mock_context, mock_user_retrieval_slack_client, mock_users_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()

    async def lookup_by_email_side_effect(*, email):
        if email == user1["profile"]["email"]:
            return {"ok": True, "user": user1}
        if email == user2["profile"]["email"]:
            return {"ok": True, "user": user2}
        raise SlackApiError(
            message="User not found",
            response={"ok": False, "error": "user_not_found"},
        )

    mock_user_retrieval_slack_client.users_lookupByEmail.side_effect = lookup_by_email_side_effect
    mock_users_slack_client.users_list.return_value = {
        "ok": True,
        "members": [user1, user2],
    }

    with pytest.raises(RetryableToolError) as e:
        await get_users_info(
            mock_context,
            emails=[
                user1["profile"]["email"],
                user2["profile"]["email"],
                "not_found@example.com",
            ],
        )

    assert "not_found@example.com" in e.value.message
    assert json.dumps(short_user_info(user1)) in e.value.additional_prompt_content
    assert json.dumps(short_user_info(user2)) in e.value.additional_prompt_content
