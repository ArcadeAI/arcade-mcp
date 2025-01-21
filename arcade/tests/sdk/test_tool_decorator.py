import asyncio

import pytest

from arcade.core.auth import AuthProviderType, Google
from arcade.sdk import tool
from arcade.sdk.auth import OAuth2


def test_sync_function():
    """
    Ensures a function will run when decorated by @tool
    """

    @tool
    def sync_func(x, y):
        return x + y

    result = sync_func(1, 2)
    assert result == 3


@pytest.mark.asyncio
async def test_async_function():
    """
    Ensures an async function will run when decorated by @tool
    """

    @tool
    async def async_func(x, y):
        await asyncio.sleep(0)
        return x + y

    result = await async_func(1, 2)
    assert result == 3


@pytest.mark.parametrize(
    "auth_class, auth_kwargs, expected_provider_id, expected_id",
    [
        (
            OAuth2,
            {"id": "my_example_provider123", "scopes": ["test_scope", "another.scope"]},
            None,
            "my_example_provider123",
        ),
        (Google, {"scopes": ["test_scope", "another.scope"]}, "google", None),
        (
            Google,
            {"id": "my_google_provider123", "scopes": ["test_scope", "another.scope"]},
            "google",
            "my_google_provider123",
        ),
    ],
)
def test_tool_decorator_with_auth_success(
    auth_class, auth_kwargs, expected_provider_id, expected_id
):
    @tool(
        name="TestTool",
        desc="Test description",
        requires_auth=auth_class(**auth_kwargs),
    )
    def test_tool(x, y):
        return x + y

    assert test_tool.__tool_name__ == "TestTool"
    assert test_tool.__tool_description__ == "Test description"
    assert test_tool.__tool_requires_auth__.provider_id == expected_provider_id
    assert test_tool.__tool_requires_auth__.provider_type == AuthProviderType.oauth2
    assert test_tool.__tool_requires_auth__.id == expected_id
    assert test_tool.__tool_requires_auth__.scopes == ["test_scope", "another.scope"]


@pytest.mark.parametrize(
    "auth_class, auth_kwargs",
    [
        (OAuth2, {"scopes": ["test_scope", "another.scope"]}),
        (
            OAuth2,
            {"provider_id": "my_example_provider123", "scopes": ["test_scope", "another.scope"]},
        ),
        (
            OAuth2,
            {
                "provider_id": "my_example_provider_id_123",
                "id": "my_example_id_123",
                "scopes": ["test_scope", "another.scope"],
            },
        ),
        (
            Google,
            {
                "provider_id": "my_example_provider_id_123",
                "scopes": ["test_scope", "another.scope"],
            },
        ),
        (
            Google,
            {
                "provider_id": "my_example_provider_id_123",
                "id": "my_example_id_123",
                "scopes": ["test_scope", "another.scope"],
            },
        ),
    ],
)
def test_tool_decorator_with_auth_failure(auth_class, auth_kwargs):
    with pytest.raises(TypeError):

        @tool(
            name="TestTool",
            desc="Test description",
            requires_auth=auth_class(**auth_kwargs),
        )
        def test_tool(x, y):
            return x + y
