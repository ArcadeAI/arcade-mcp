import random
import string
from collections.abc import Callable

import pytest
from arcade_tdk import ToolAuthorizationContext, ToolContext


@pytest.fixture
def mock_context():
    mock_auth = ToolAuthorizationContext(token="fake-token")  # noqa: S106
    return ToolContext(authorization=mock_auth)


@pytest.fixture
def mock_chat_slack_client(mocker):
    mock_client = mocker.patch("arcade_slack.tools.chat.AsyncWebClient", autospec=True)
    return mock_client.return_value


@pytest.fixture
def mock_users_slack_client(mocker):
    mock_client = mocker.patch("arcade_slack.tools.users.AsyncWebClient", autospec=True)
    return mock_client.return_value


@pytest.fixture
def random_str_factory():
    def random_str_factory(length: int = 10):
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))  # noqa: S311

    return random_str_factory


@pytest.fixture
def dummy_user_factory(random_str_factory: Callable[[int], str]):
    def dummy_user_factory(
        id_: str | None = None,
        name: str | None = None,
        email: str | None = None,
    ):
        return {
            "id": id_ or random_str_factory(),
            "name": name or random_str_factory(),
            "profile": {
                "email": email or f"{random_str_factory()}@{random_str_factory()}.com",
            },
        }

    return dummy_user_factory
