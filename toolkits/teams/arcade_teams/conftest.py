import random
import string
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from arcade_tdk import ToolAuthorizationContext, ToolContext
from msgraph.generated.models.person import Person


@pytest.fixture
def mock_context():
    mock_auth = ToolAuthorizationContext(token="fake-token")  # noqa: S106
    return ToolContext(authorization=mock_auth)


@pytest.fixture
def mock_client(mocker):
    mock_client = mocker.patch("arcade_teams.client.GraphServiceClient", autospec=True)
    return mock_client.return_value


@pytest.fixture
def response_factory():
    def response_factory(value: Any, next_link: str | None = None):
        container = MagicMock()
        container.value = value
        container.odata_next_link = next_link

        async def async_response():
            return container

        return async_response()

    return response_factory


@pytest.fixture
def random_str_factory():
    def random_str_factory(
        length: int = 10,
    ) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))  # noqa: S311

    return random_str_factory


@pytest.fixture
def person_dict_factory(random_str_factory):
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
def person_factory():
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
