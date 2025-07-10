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
def mock_user_retrieval_slack_client(mocker):
    mock_client = mocker.patch("arcade_slack.user_retrieval.AsyncWebClient", autospec=True)
    return mock_client.return_value


@pytest.fixture
def mock_conversation_retrieval_slack_client(mocker):
    mock_client = mocker.patch("arcade_slack.conversation_retrieval.AsyncWebClient", autospec=True)
    return mock_client.return_value


@pytest.fixture
def mock_message_retrieval_slack_client(mocker):
    mock_client = mocker.patch("arcade_slack.message_retrieval.AsyncWebClient", autospec=True)
    return mock_client.return_value


@pytest.fixture
def random_str_factory():
    def random_str_factory(length: int = 10):
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))  # noqa: S311

    return random_str_factory


@pytest.fixture
def random_ts_factory():
    def random_ts_factory():
        return f"{random.uniform(1735689600.000000, 1751327999.999999)}"  # noqa: S311

    return random_ts_factory


@pytest.fixture
def dummy_channel_factory(random_str_factory: Callable[[int], str]):
    def dummy_channel_factory(
        id_: str | None = None,
        name: str | None = None,
        is_member: bool = True,
        is_private: bool = False,
        is_archived: bool = False,
        is_channel: bool = False,
        is_im: bool = False,
        is_mpim: bool = False,
        num_members: int | None = None,
        user: str | None = None,
        is_user_deleted: bool = False,
    ):
        channel = {
            "id": id_ or f"channel_id_{random_str_factory()}",
            "is_member": is_member,
            "is_private": is_private,
            "is_archived": is_archived,
        }

        if name or is_channel or is_mpim:
            channel["name"] = name or f"channel_name_{random_str_factory()}"

        if is_channel:
            channel["is_channel"] = True
        if is_im:
            channel["is_im"] = True
        if is_mpim:
            channel["is_group"] = True
        if num_members:
            channel["num_members"] = num_members
        if user or is_im:
            channel["user"] = user or f"user_id_{random_str_factory()}"
        if is_user_deleted:
            channel["is_user_deleted"] = is_user_deleted

        return channel

    return dummy_channel_factory


@pytest.fixture
def dummy_user_factory(random_str_factory: Callable[[int], str]):
    def dummy_user_factory(
        id_: str | None = None,
        name: str | None = None,
        email: str | None = None,
        is_bot: bool = False,
    ):
        return {
            "id": id_ or random_str_factory(),
            "name": name or random_str_factory(),
            "profile": {
                "email": email or f"{random_str_factory()}@{random_str_factory()}.com",
            },
            "is_bot": is_bot,
        }

    return dummy_user_factory


@pytest.fixture
def dummy_reaction_factory(random_str_factory):
    def reaction_factory(
        name: str | None = None,
        user_ids: list[str] | None = None,
        count: int | None = None,
    ):
        count = count or random.randint(1, 10)  # noqa: S311
        if user_ids:
            count = len(user_ids)
        return {
            "count": count,
            "name": name or random_str_factory(),
            "users": user_ids or [random_str_factory() for _ in range(count)],
        }

    return reaction_factory


@pytest.fixture
def dummy_message_factory(random_str_factory, random_ts_factory):
    def message_factory(
        user_id: str | None = None,
        text: str | None = None,
        reactions: list[dict] | None = None,
        type_: str = "message",
        ts: float | None = None,
    ):
        message = {
            "user": user_id or random_str_factory(),
            "text": text or random_str_factory(),
            "type": type_,
            "ts": ts or random_ts_factory(),
        }

        if reactions:
            message["reactions"] = reactions
        return message

    return message_factory
