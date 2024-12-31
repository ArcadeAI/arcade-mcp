from unittest.mock import MagicMock, patch

import pytest
from arcade.sdk import ToolAuthorizationContext, ToolContext

from arcade_slack.tools.chat import send_dm_to_user, send_message_to_channel


@pytest.fixture
def mock_context():
    mock_auth = ToolAuthorizationContext(token="fake-token")  # noqa: S106
    return ToolContext(authorization=mock_auth)


def test_send_dm_to_user(mock_context):
    with patch("arcade_slack.tools.chat.WebClient") as MockWebClient:
        mock_client = MockWebClient.return_value
        mock_client.users_list.return_value = {"members": [{"name": "testuser", "id": "U12345"}]}
        mock_client.conversations_open.return_value = {"channel": {"id": "D12345"}}
        mock_client.chat_postMessage.return_value = MagicMock(data={"ok": True})

        response = send_dm_to_user(mock_context, "testuser", "Hello!")

        assert response["ok"] is True
        mock_client.users_list.assert_called_once()
        mock_client.conversations_open.assert_called_once_with(users=["U12345"])
        mock_client.chat_postMessage.assert_called_once_with(channel="D12345", text="Hello!")


def test_send_message_to_channel(mock_context):
    with patch("arcade_slack.tools.chat.WebClient") as MockWebClient:
        mock_client = MockWebClient.return_value
        mock_client.conversations_list.return_value = {
            "channels": [{"name": "general", "id": "C12345"}]
        }
        mock_client.chat_postMessage.return_value = MagicMock(data={"ok": True})

        response = send_message_to_channel(mock_context, "general", "Hello, channel!")

        assert response["ok"] is True
        mock_client.conversations_list.assert_called_once()
        mock_client.chat_postMessage.assert_called_once_with(
            channel="C12345", text="Hello, channel!"
        )
