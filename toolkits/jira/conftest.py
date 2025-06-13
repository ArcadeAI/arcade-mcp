import random
import string
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from arcade_tdk import ToolAuthorizationContext, ToolContext

from arcade_jira.cache import set_cloud_id, set_cloud_name


@pytest.fixture
def fake_auth_token(generate_random_str: Callable) -> str:
    return generate_random_str()


@pytest.fixture
def fake_cloud_id(generate_random_str: Callable) -> str:
    return generate_random_str()


@pytest.fixture
def fake_cloud_name(generate_random_str: Callable) -> str:
    return generate_random_str()


@pytest.fixture(autouse=True)
def set_cloud_id_cache(fake_auth_token: str, fake_cloud_id: str, fake_cloud_name: str) -> None:
    """This fixture auto-sets cloud ID in the cache to skip the HTTP call to get it"""
    set_cloud_id(fake_auth_token, fake_cloud_id)
    set_cloud_name(fake_auth_token, fake_cloud_name)


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
def generate_random_url(generate_random_str: Callable) -> Callable[[str], str]:
    def random_url_generator(base_url: str | None = None) -> str:
        base_url = base_url or f"https://{generate_random_str()}.com"
        return f"{base_url}/{generate_random_str()}"

    return random_url_generator


@pytest.fixture
def mock_context(fake_auth_token: str) -> ToolContext:
    mock_auth = ToolAuthorizationContext(token=fake_auth_token)
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
def build_user_dict(
    generate_random_str: Callable[[int], str],
    generate_random_email: Callable[[str | None, str | None], str],
) -> Callable[[str | None, str | None, str | None, bool, str], dict]:
    def user_dict_builder(
        id_: str | None = None,
        email: str | None = None,
        display_name: str | None = None,
        active: bool = True,
        account_type: str = "atlassian",
    ) -> dict[str, Any]:
        display_name = display_name or generate_random_str()
        user = {
            "accountId": id_ or generate_random_str(),
            "displayName": display_name,
            "emailAddress": email or generate_random_email(name=display_name),
            "active": active,
            "accountType": account_type,
        }

        return user

    return user_dict_builder


@pytest.fixture
def build_project_dict(
    generate_random_str: Callable,
    generate_random_url: Callable,
) -> Callable[[str | None, str | None, str | None, str | None, str | None], dict]:
    def project_dict_builder(
        id_: str | None = None,
        key: str | None = None,
        name: str | None = None,
        description: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        return {
            "id": id_ or generate_random_str(),
            "key": key or generate_random_str(),
            "name": name or generate_random_str(),
            "description": description or generate_random_str(),
            "url": url or generate_random_url(),
        }

    return project_dict_builder


@pytest.fixture
def build_project_search_response_dict() -> Callable[[list[dict], bool], dict]:
    def project_search_response_builder(projects: list[dict], is_last: bool = True) -> dict:
        return {
            "values": projects,
            "isLast": is_last,
        }

    return project_search_response_builder


@pytest.fixture
def build_priority_dict(
    generate_random_str: Callable,
) -> Callable[[str | None, str | None, str | None], dict]:
    def priority_dict_builder(
        id_: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> dict:
        return {
            "id": id_ or generate_random_str(),
            "name": name or generate_random_str(),
            "description": description or generate_random_str(),
        }

    return priority_dict_builder


@pytest.fixture
def build_issue_type_dict(
    generate_random_str: Callable,
) -> Callable[[str | None, str | None, str | None], dict]:
    def issue_type_dict_builder(
        id_: str | None = None, name: str | None = None, description: str | None = None
    ) -> dict:
        return {
            "id": id_ or generate_random_str(),
            "name": name or generate_random_str(),
            "description": description or generate_random_str(),
        }

    return issue_type_dict_builder


@pytest.fixture
def build_issue_types_response_dict() -> Callable[[list[dict]], dict]:
    def issue_types_response_builder(
        issue_types: list[dict],
        is_last: bool = True,
    ) -> dict:
        return {
            "issueTypes": issue_types,
            "isLast": is_last,
        }

    return issue_types_response_builder


@pytest.fixture
def build_priority_scheme_dict(
    generate_random_str: Callable,
) -> Callable[[str | None, str | None, str | None, bool], dict]:
    def priority_scheme_dict_builder(
        id_: str | None = None,
        name: str | None = None,
        description: str | None = None,
        is_default: bool = False,
    ) -> dict:
        return {
            "id": id_ or generate_random_str(),
            "name": name or generate_random_str(),
            "description": description or generate_random_str(),
            "isDefault": is_default,
        }

    return priority_scheme_dict_builder
