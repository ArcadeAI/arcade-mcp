import random
import string
from typing import Any, Callable
from unittest.mock import MagicMock, patch

import httpx
import pytest
from arcade.sdk import ToolAuthorizationContext, ToolContext


@pytest.fixture
def generate_random_str() -> Callable[[int], str]:
    def random_str_builder(length: int = 10) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))  # noqa: S311

    return random_str_builder


@pytest.fixture
def generate_random_email(generate_random_str: Callable) -> Callable[[str | None, str | None], str]:
    def random_email_generator(name: str | None = None, domain: str | None = None) -> str:
        name = name or generate_random_str()
        domain = domain or f"{generate_random_str()}.com"
        return f"{name}@{domain}"

    return random_email_generator


@pytest.fixture
def mock_context():
    mock_auth = ToolAuthorizationContext(token="fake-token")  # noqa: S106
    return ToolContext(authorization=mock_auth)


@pytest.fixture
def mock_httpx_client():
    with patch("arcade_jira.client.httpx") as mock_httpx:
        yield mock_httpx.AsyncClient().__aenter__.return_value


@pytest.fixture
def mock_httpx_response() -> Callable[[int, dict], httpx.Response]:
    def generate_mock_httpx_response(status_code: int, json_data: dict) -> httpx.Response:
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.json.return_value = json_data
        return response

    return generate_mock_httpx_response


@pytest.fixture
def build_sample_user_dict(
    generate_random_str: Callable[[int], str],
    generate_random_email: Callable[[str | None, str | None], str],
) -> Callable[[str | None, str | None, str | None], dict]:
    def user_dict_builder(
        id_: str | None = None,
        email: str | None = None,
        display_name: str | None = None,
        active: bool = True,
        account_type: str = "atlassian",
    ) -> dict[str, Any]:
        display_name = display_name or generate_random_str()
        user = {
            "id": id_ or generate_random_str(),
            "displayName": display_name,
            "emailAddress": email or generate_random_email(name=display_name),
            "active": active,
            "accountType": account_type,
        }

        return user

    return user_dict_builder
