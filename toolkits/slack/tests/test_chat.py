import pytest
from arcade.sdk.errors import RetryableToolError, ToolExecutionError
from slack_sdk.errors import SlackApiError

from arcade_slack.tools.chat import send_dm_to_user, send_message_to_channel


@pytest.fixture
def mock_slack_client(mocker):
    mock_client = mocker.patch("arcade_slack.tools.chat.AsyncWebClient", autospec=True)
    return mock_client.return_value


@pytest.mark.asyncio
async def test_send_dm_to_user(mock_context, mock_slack_client):
    mock_slack_client.users_list.return_value = {"members": [{"name": "testuser", "id": "U12345"}]}
    mock_slack_client.conversations_open.return_value = {"channel": {"id": "D12345"}}
    mock_slack_client.chat_postMessage.return_value = {"ok": True}

    response = await send_dm_to_user(mock_context, "testuser", "Hello!")

    assert response["ok"] is True
    mock_slack_client.users_list.assert_called_once()
    mock_slack_client.conversations_open.assert_called_once_with(users=["U12345"])
    mock_slack_client.chat_postMessage.assert_called_once_with(channel="D12345", text="Hello!")


@pytest.mark.asyncio
async def test_send_dm_to_inexistent_user(mock_context, mock_slack_client):
    mock_slack_client.users_list.return_value = {"members": [{"name": "testuser", "id": "U12345"}]}

    with pytest.raises(RetryableToolError):
        await send_dm_to_user(mock_context, "inexistent_user", "Hello!")

    mock_slack_client.users_list.assert_called_once()
    mock_slack_client.conversations_open.assert_not_called()
    mock_slack_client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_send_message_to_channel(mock_context, mock_slack_client):
    mock_slack_client.conversations_list.return_value = {
        "channels": [{"name": "general", "id": "C12345"}]
    }
    mock_slack_client.chat_postMessage.return_value = {"ok": True}

    response = await send_message_to_channel(mock_context, "general", "Hello, channel!")

    assert response["ok"] is True
    mock_slack_client.conversations_list.assert_called_once()
    mock_slack_client.chat_postMessage.assert_called_once_with(
        channel="C12345", text="Hello, channel!"
    )


@pytest.mark.asyncio
async def test_send_message_to_inexistent_channel(mock_context, mock_slack_client):
    mock_slack_client.conversations_list.return_value = {"channels": []}

    with pytest.raises(RetryableToolError):
        await send_message_to_channel(mock_context, "inexistent_channel", "Hello!")

    mock_slack_client.conversations_list.assert_called_once()
    mock_slack_client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "faulty_slack_function_name, tool_function, tool_args",
    [
        ("users_list", send_dm_to_user, ("testuser", "Hello!")),
        ("conversations_list", send_message_to_channel, ("general", "Hello!")),
    ],
)
async def test_tools_with_slack_error(
    mock_context, mock_slack_client, faulty_slack_function_name, tool_function, tool_args
):
    getattr(mock_slack_client, faulty_slack_function_name).side_effect = SlackApiError(
        message="test_slack_error",
        response={"ok": False, "error": "test_slack_error"},
    )

    with pytest.raises(ToolExecutionError) as e:
        await tool_function(mock_context, *tool_args)
        assert "test_slack_error" in str(e.value)
