from unittest.mock import patch

import pytest
from arcade_tdk.errors import RetryableToolError
from slack_sdk.errors import SlackApiError

from arcade_slack.tools.users import get_user_info_by_id, list_users
from arcade_slack.utils import extract_basic_user_info


@pytest.fixture
def mock_slack_client(mocker):
    mock_client = mocker.patch("arcade_slack.tools.users.AsyncWebClient", autospec=True)
    return mock_client.return_value


@pytest.mark.asyncio
async def test_get_user_info_by_id_success(mock_context, mock_slack_client):
    # Mock the response from slackClient.users_info
    mock_user = {
        "id": "U12345",
        "name": "testuser",
        "real_name": "Test User",
        "profile": {"email": "testuser@example.com"},
    }
    mock_slack_client.users_info.return_value = {"ok": True, "user": mock_user}

    # Call the function
    response = await get_user_info_by_id(mock_context, user_id="U12345")

    # Verify that the correct Slack API method was called
    mock_slack_client.users_info.assert_called_once_with(user="U12345")

    # Verify the response
    expected_response = extract_basic_user_info(mock_user)
    assert response == expected_response


@pytest.mark.asyncio
@patch("arcade_slack.tools.users.list_users")
async def test_get_user_info_by_id_user_not_found(mock_list_users, mock_context, mock_slack_client):
    error_response = {"ok": False, "error": "user_not_found"}
    mock_slack_client.users_info.side_effect = SlackApiError(
        message="User not found",
        response=error_response,
    )

    existing_user = {"id": "U12345", "name": "testuser"}
    mock_list_users.return_value = {"users": [existing_user]}

    with pytest.raises(RetryableToolError) as e:
        await get_user_info_by_id(mock_context, user_id="U99999")

        assert existing_user["id"] in e.value.additional_prompt_content
        assert existing_user["name"] in e.value.additional_prompt_content

    mock_slack_client.users_info.assert_called_once_with(user="U99999")
    mock_list_users.assert_called_once_with(mock_context)


@pytest.mark.asyncio
async def test_list_users_success(mock_context, mock_slack_client):
    mock_slack_client.users_list.return_value = {"ok": True, "members": [{"id": "U12345"}]}
    response = await list_users(mock_context)
    assert response == {
        "users": [extract_basic_user_info({"id": "U12345"})],
        "next_cursor": None,
    }


@pytest.mark.asyncio
async def test_list_users_with_pagination_success(mock_context, mock_slack_client):
    mock_slack_client.users_list.side_effect = [
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
