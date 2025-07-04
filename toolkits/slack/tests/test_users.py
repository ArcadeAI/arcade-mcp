import json
from unittest.mock import patch

import pytest
from arcade_tdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError

from arcade_slack.tools.users import (
    get_user_info_by_id,
    get_users_info,
    list_users,
)
from arcade_slack.utils import extract_basic_user_info, short_user_info


@pytest.mark.asyncio
async def test_get_user_info_by_id_success(mock_context, mock_users_slack_client):
    # Mock the response from slackClient.users_info
    mock_user = {
        "id": "U12345",
        "name": "testuser",
        "real_name": "Test User",
        "profile": {"email": "testuser@example.com"},
    }
    mock_users_slack_client.users_info.return_value = {"ok": True, "user": mock_user}

    # Call the function
    response = await get_user_info_by_id(mock_context, user_id="U12345")

    # Verify that the correct Slack API method was called
    mock_users_slack_client.users_info.assert_called_once_with(user="U12345")

    # Verify the response
    expected_response = extract_basic_user_info(mock_user)
    assert response == expected_response


@pytest.mark.asyncio
@patch("arcade_slack.tools.users.list_users")
async def test_get_user_info_by_id_user_not_found(
    mock_list_users, mock_context, mock_users_slack_client
):
    error_response = {"ok": False, "error": "user_not_found"}
    mock_users_slack_client.users_info.side_effect = SlackApiError(
        message="User not found",
        response=error_response,
    )

    existing_user = {"id": "U12345", "name": "testuser"}
    mock_list_users.return_value = {"users": [existing_user]}
    mock_list_users.__tool_name__ = list_users.__tool_name__

    with pytest.raises(RetryableToolError) as e:
        await get_user_info_by_id(mock_context, user_id="U99999")

        assert json.dumps(short_user_info(existing_user)) in e.value.additional_prompt_content

    mock_users_slack_client.users_info.assert_called_once_with(user="U99999")
    mock_list_users.assert_called_once_with(mock_context, limit=100)


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
async def test_list_users_with_pagination_success(mock_context, mock_users_slack_client):
    mock_users_slack_client.users_list.side_effect = [
        {
            "ok": True,
            "members": [{"id": "U12345"}],
            "response_metadata": {"next_cursor": "cursor_xyz"},
        },
        {
            "ok": True,
            "members": [{"id": "U123456"}],
            "response_metadata": {"next_cursor": None},
        },
    ]
    response = await list_users(mock_context, limit=3)
    assert response == {
        "users": [
            extract_basic_user_info({"id": "U12345"}),
            extract_basic_user_info({"id": "U123456"}),
        ],
        "next_cursor": None,
    }


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
    assert str(short_user_info(user1)) in e.value.additional_prompt_content
    assert str(short_user_info(user2)) in e.value.additional_prompt_content
    assert str(short_user_info(user3)) not in e.value.additional_prompt_content


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

    response = await get_users_info(mock_context, usernames=[user1["name"], user2["name"]])

    assert response == {"users": [extract_basic_user_info(user1), extract_basic_user_info(user2)]}


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

    with pytest.raises(RetryableToolError) as e:
        await get_users_info(mock_context, usernames=[user1["name"], user2["name"] + "not_found"])

    assert user2["name"] + "not_found" in e.value.message
    assert str(short_user_info(user1)) not in e.value.additional_prompt_content
    assert str(short_user_info(user2)) in e.value.additional_prompt_content
    assert str(short_user_info(user3)) not in e.value.additional_prompt_content


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
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    additional_user = dummy_user_factory()
    mock_user_retrieval_slack_client.users_lookupByEmail.side_effect = SlackApiError(
        message="User not found",
        response={"ok": False, "error": "user_not_found"},
    )
    mock_user_retrieval_slack_client.users_list.return_value = {
        "ok": True,
        "members": [additional_user],
    }

    with pytest.raises(RetryableToolError) as e:
        await get_users_info(mock_context, emails=["not_found@example.com"])

    assert "not_found@example.com" in e.value.message


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
    mock_context, mock_user_retrieval_slack_client, dummy_user_factory
):
    user1 = dummy_user_factory()
    user2 = dummy_user_factory()

    mock_user_retrieval_slack_client.users_lookupByEmail.side_effect = [
        {"ok": True, "user": user1},
        {"ok": True, "user": user2},
        SlackApiError(
            message="User not found",
            response={"ok": False, "error": "user_not_found"},
        ),
    ]

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
