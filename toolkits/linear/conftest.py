import json
import random
import string
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from arcade_tdk import ToolAuthorizationContext, ToolContext

# Seed random generator for deterministic tests
random.seed(42)

# Hardcoded email list for deterministic testing with varied domains
TEST_EMAILS = [
    "alice.smith@testcorp.com",
    "bob.jones@acme.org",
    "charlie.brown@techstart.io",
    "diana.wilson@example.net",
    "eve.davis@startup.co",
    "frank.miller@bigtech.com",
    "grace.taylor@innovation.ai",
    "henry.anderson@devteam.dev",
    "iris.johnson@design.studio",
    "jack.white@cloudops.tech",
    "karen.thomas@product.team",
    "liam.jackson@engineering.co",
    "mia.harris@marketing.agency",
    "noah.martin@sales.pro",
    "olivia.garcia@support.help",
    "peter.rodriguez@finance.biz",
    "quinn.lewis@legal.firm",
    "rachel.lee@hr.people",
    "sam.walker@operations.work",
    "tina.hall@consulting.group",
]

_email_counter = 0


@pytest.fixture
def fake_auth_token() -> str:
    return generate_random_str()


def generate_random_str(length: int = 8) -> str:
    """Generate a deterministic random string for testing"""
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length))  # noqa: S311


def generate_random_int(min_val: int = 1, max_val: int = 9999) -> int:
    """Generate a deterministic random integer for testing"""
    return random.randint(min_val, max_val)  # noqa: S311


def get_test_email() -> str:
    """Get the next email from the hardcoded list, cycling through them"""
    global _email_counter
    email = TEST_EMAILS[_email_counter % len(TEST_EMAILS)]
    _email_counter += 1
    return email


@pytest.fixture
def generate_random_email() -> Callable[[str | None, str | None], str]:
    def random_email_generator(name: str | None = None, domain: str | None = None) -> str:
        # If specific name/domain provided, use them, otherwise use hardcoded emails
        if name is None and domain is None:
            return get_test_email()

        name = name or generate_random_str()
        domain = domain or "example.com"
        return f"{name}@{domain}"

    return random_email_generator


@pytest.fixture
def mock_context(fake_auth_token: str) -> ToolContext:
    mock_auth = ToolAuthorizationContext(token=fake_auth_token)
    return ToolContext(authorization=mock_auth)


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for GraphQL requests"""
    with patch("arcade_linear.client.httpx.AsyncClient") as mock_client_class:
        # Create an async mock for the client instance
        mock_client_instance = MagicMock()

        # Mock the async context manager methods
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        # Make the post method async
        mock_client_instance.post = AsyncMock()

        yield mock_client_instance


@pytest.fixture
def mock_httpx_response() -> Callable[[int, dict], httpx.Response]:
    """Create mock httpx.Response objects"""

    def generate_mock_httpx_response(status_code: int, json_data: dict) -> httpx.Response:
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.json.return_value = json_data
        response.reason_phrase = "OK" if status_code == 200 else "Error"
        response.text = json.dumps(json_data)
        return response

    return generate_mock_httpx_response


# Linear-specific test data builders
@pytest.fixture
def build_user_dict(
    generate_random_email: Callable[[str | None, str | None], str],
) -> Callable:
    def user_dict_builder(
        id_: str | None = None,
        email: str | None = None,
        name: str | None = None,
        display_name: str | None = None,
        active: bool = True,
    ) -> dict[str, Any]:
        name = name or generate_random_str()
        return {
            "id": id_ or generate_random_str(),
            "name": name,
            "email": email or generate_random_email(name=name),
            "displayName": display_name or name,
            "avatarUrl": f"https://avatar.example.com/{generate_random_str()}.png",
            "active": active,
        }

    return user_dict_builder


@pytest.fixture
def build_team_dict() -> Callable:
    def team_dict_builder(
        id_: str | None = None,
        key: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        name = name or generate_random_str()
        return {
            "id": id_ or generate_random_str(),
            "key": key or generate_random_str(3).upper(),
            "name": name,
            "description": description or f"Description for {name}",
            "private": False,
            "archivedAt": None,
            "createdAt": "2023-01-01T00:00:00.000Z",
            "updatedAt": "2023-01-01T00:00:00.000Z",
            "icon": "🚀",
            "color": "#FF6B6B",
            "cyclesEnabled": True,
            "issueEstimationType": "exponential",
            "organization": {"id": generate_random_str(), "name": "Test Organization"},
            "members": {"nodes": []},
        }

    return team_dict_builder


@pytest.fixture
def build_issue_dict(build_user_dict: Callable, build_team_dict: Callable) -> Callable:
    def issue_dict_builder(
        id_: str | None = None,
        identifier: str | None = None,
        title: str | None = None,
        description: str | None = None,
        priority: int = 2,
        priority_label: str = "Medium",
    ) -> dict[str, Any]:
        user = build_user_dict()
        team = build_team_dict()
        return {
            "id": id_ or generate_random_str(),
            "identifier": identifier or f"TEST-{generate_random_int(1, 9999)}",
            "title": title or f"Test Issue {generate_random_str()}",
            "description": description or f"Description for test issue {generate_random_str()}",
            "priority": priority,
            "priorityLabel": priority_label,
            "estimate": None,
            "sortOrder": 100.0,
            "createdAt": "2023-01-01T00:00:00.000Z",
            "updatedAt": "2023-01-01T00:00:00.000Z",
            "completedAt": None,
            "canceledAt": None,
            "dueDate": None,
            "url": f"https://linear.app/test/issue/{identifier or 'TEST-1'}",
            "branchName": None,
            "creator": user,
            "assignee": user,
            "state": {
                "id": generate_random_str(),
                "name": "Todo",
                "type": "unstarted",
                "color": "#e2e2e2",
                "position": 1,
            },
            "team": team,
            "project": None,
            "cycle": None,
            "parent": None,
            "labels": {"nodes": []},
            "children": {"nodes": []},
            "relations": {"nodes": []},
        }

    return issue_dict_builder


@pytest.fixture
def build_workflow_state_dict(build_team_dict: Callable) -> Callable:
    def workflow_state_dict_builder(
        id_: str | None = None,
        name: str | None = None,
        type_: str = "unstarted",
        color: str = "#e2e2e2",
        position: float = 1.0,
    ) -> dict[str, Any]:
        team = build_team_dict()
        return {
            "id": id_ or generate_random_str(),
            "name": name or f"State {generate_random_str()}",
            "description": f"Description for {name or 'test state'}",
            "type": type_,
            "color": color,
            "position": position,
            "team": team,
        }

    return workflow_state_dict_builder


@pytest.fixture
def build_cycle_dict(build_team_dict: Callable) -> Callable:
    def cycle_dict_builder(
        id_: str | None = None,
        number: int | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        team = build_team_dict()
        number = number or generate_random_int(1, 100)
        return {
            "id": id_ or generate_random_str(),
            "number": number,
            "name": name or f"Sprint {number}",
            "description": description or f"Description for Sprint {number}",
            "startsAt": "2023-01-01T00:00:00.000Z",
            "endsAt": "2023-01-14T23:59:59.000Z",
            "completedAt": None,
            "autoArchivedAt": None,
            "progress": 0.5,
            "createdAt": "2023-01-01T00:00:00.000Z",
            "updatedAt": "2023-01-01T00:00:00.000Z",
            "team": team,
            "issues": {"nodes": []},
        }

    return cycle_dict_builder


@pytest.fixture
def build_project_dict(build_user_dict: Callable) -> Callable:
    def project_dict_builder(
        id_: str | None = None,
        name: str | None = None,
        description: str | None = None,
        state: str = "planned",
    ) -> dict[str, Any]:
        user = build_user_dict()
        return {
            "id": id_ or generate_random_str(),
            "name": name or f"Project {generate_random_str()}",
            "description": description or "Description for test project",
            "state": state,
            "progress": 0.3,
            "startDate": "2023-01-01",
            "targetDate": "2023-12-31",
            "completedAt": None,
            "canceledAt": None,
            "autoArchivedAt": None,
            "createdAt": "2023-01-01T00:00:00.000Z",
            "updatedAt": "2023-01-01T00:00:00.000Z",
            "icon": "📋",
            "color": "#4F46E5",
            "creator": user,
            "lead": user,
            "teams": {"nodes": []},
            "members": {"nodes": []},
        }

    return project_dict_builder


# GraphQL response builders
@pytest.fixture
def build_graphql_response() -> Callable[[dict], dict]:
    def graphql_response_builder(data: dict, errors: list | None = None) -> dict:
        response = {"data": data}
        if errors:
            response["errors"] = errors
        return response

    return graphql_response_builder


@pytest.fixture
def build_paginated_response() -> Callable[[list, bool, str | None, str | None], dict]:
    def paginated_response_builder(
        nodes: list,
        has_next_page: bool = False,
        start_cursor: str | None = None,
        end_cursor: str | None = None,
    ) -> dict:
        return {
            "nodes": nodes,
            "pageInfo": {
                "hasNextPage": has_next_page,
                "hasPreviousPage": False,
                "startCursor": start_cursor,
                "endCursor": end_cursor,
            },
        }

    return paginated_response_builder
