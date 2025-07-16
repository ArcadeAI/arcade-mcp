import random
import string
import uuid
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from arcade_tdk import ToolAuthorizationContext, ToolContext
from msgraph.generated.models.chat import Chat
from msgraph.generated.models.conversation_member import ConversationMember
from msgraph.generated.models.person import Person
from pytest_mock import MockerFixture


@pytest.fixture
def mock_context() -> ToolContext:
    mock_auth = ToolAuthorizationContext(token="fake-token")  # noqa: S106
    return ToolContext(authorization=mock_auth)


@pytest.fixture
def mock_client(mocker: MockerFixture) -> Any:
    mock_client = mocker.patch("arcade_teams.client.GraphServiceClient", autospec=True)
    return mock_client.return_value


@pytest.fixture
def response_factory() -> Callable[[Any, str | None], Any]:
    def response_factory(value: Any, next_link: str | None = None) -> Any:
        container = MagicMock()
        container.value = value
        container.odata_next_link = next_link

        async def async_response() -> Any:
            return container

        return async_response()

    return response_factory


@pytest.fixture
def random_str_factory() -> Callable[[int], str]:
    def random_str_factory(
        length: int = 10,
    ) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))  # noqa: S311

    return random_str_factory


@pytest.fixture
def person_dict_factory(
    random_str_factory: Callable[[int], str],
) -> Callable[[Any, str | None, str | None, str | None], dict]:
    def person_dict_factory(
        id_: str | None = None,
        display_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> dict:
        first_name = first_name or f"first_{random_str_factory(4)}"
        last_name = last_name or f"last_{random_str_factory(4)}"
        display_name = display_name or f"{first_name} {last_name}"
        return {
            "id": id_ or random_str_factory(10),
            "name": {
                "display": display_name,
                "first": first_name,
                "last": last_name,
            },
        }

    return person_dict_factory


@pytest.fixture
def person_factory(
    random_str_factory: Callable[[int], str],
) -> Callable[[Any, str | None, str | None, str | None], Person]:
    def person_factory(
        id_: str | None = None,
        display_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Person:
        first_name = first_name or f"first_{random_str_factory(4)}"
        last_name = last_name or f"last_{random_str_factory(4)}"
        display_name = display_name or f"{first_name} {last_name}"
        return Person(
            id=id_ or str(uuid.uuid4()),
            display_name=display_name,
            given_name=first_name,
            surname=last_name,
        )

    return person_factory


@pytest.fixture
def chat_factory() -> Callable[[Any, list[ConversationMember] | None], Chat]:
    def chat_factory(
        id_: str | None = None,
        members: list[ConversationMember] | None = None,
    ) -> Chat:
        return Chat(
            id=id_ or str(uuid.uuid4()),
            members=members,
        )

    return chat_factory


@pytest.fixture
def member_factory(
    random_str_factory: Callable[[int], str],
) -> Callable[
    [Any, str | None, str | None, str | None, str | None, str | None, list[str] | None],
    ConversationMember,
]:
    def member_factory(
        id_: str | None = None,
        display_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        tenant_name: str | None = None,
        roles: list[str] | None = None,
    ) -> ConversationMember:
        id_ = id_ or str(uuid.uuid4())
        first_name = first_name or f"first_{random_str_factory(4)}"
        last_name = last_name or f"last_{random_str_factory(4)}"
        display_name = display_name or f"{first_name} {last_name}"
        tenant_name = tenant_name or f"tenant_{random_str_factory(4)}"
        email = email or f"{first_name}.{last_name}@{tenant_name}.onmicrosoft.com"
        roles = roles or ["owner"]
        member = ConversationMember(
            id=id_,
            display_name=display_name,
            roles=roles,
        )
        member.email = email
        member.user_id = id_
        return member

    return member_factory
