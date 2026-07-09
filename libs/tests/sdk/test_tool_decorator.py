import asyncio
import inspect

import pytest
from arcade_core.auth import AuthProviderType, Google, Microsoft, MicrosoftPowerBI
from arcade_tdk import tool
from arcade_tdk.auth import OAuth2, PagerDuty


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
        (PagerDuty, {"scopes": ["test_scope", "another.scope"]}, "pagerduty", None),
        (
            PagerDuty,
            {"id": "my_pagerduty_provider123", "scopes": ["test_scope", "another.scope"]},
            "pagerduty",
            "my_pagerduty_provider123",
        ),
        (
            MicrosoftPowerBI,
            {"scopes": ["test_scope", "another.scope"]},
            "microsoft-powerbi",
            None,
        ),
        (
            MicrosoftPowerBI,
            {"id": "my_powerbi_provider123", "scopes": ["test_scope", "another.scope"]},
            "microsoft-powerbi",
            "my_powerbi_provider123",
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


def test_microsoft_powerbi_provider_defaults():
    auth = MicrosoftPowerBI()

    assert auth.provider_id == "microsoft-powerbi"
    assert auth.id is None
    assert auth.scopes is None
    assert auth.provider_type == AuthProviderType.oauth2
    # Subclasses Microsoft so it inherits the Microsoft Graph error adapter mapping.
    assert isinstance(auth, Microsoft)


def test_microsoft_powerbi_importable_from_mcp_server_auth():
    from arcade_mcp_server.auth import MicrosoftPowerBI as MicrosoftPowerBIFromServer

    assert MicrosoftPowerBIFromServer is MicrosoftPowerBI
    assert MicrosoftPowerBIFromServer().provider_id == "microsoft-powerbi"


def test_microsoft_powerbi_importable_from_tdk_auth():
    from arcade_tdk.auth import MicrosoftPowerBI as MicrosoftPowerBIFromTdk

    assert MicrosoftPowerBIFromTdk is MicrosoftPowerBI
    assert MicrosoftPowerBIFromTdk().provider_id == "microsoft-powerbi"


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
        (
            PagerDuty,
            {
                "provider_id": "my_example_provider_id_123",
                "scopes": ["test_scope", "another.scope"],
            },
        ),
        (
            PagerDuty,
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


def test_tool_deprecated_ordering_no_auth():
    """
    Checks the behavior of @tool.deprecated when used before and after the @tool decorator.
    The order of the decorators should not matter.
    """
    message = "Deprecated: please use new_tool instead."

    @tool.deprecated(message)
    @tool
    def func_deprecated_after(x):
        """Test description for func_deprecated_after"""
        return x

    assert hasattr(func_deprecated_after, "__tool_deprecation_message__")
    assert func_deprecated_after.__tool_deprecation_message__ == message
    assert func_deprecated_after.__tool_name__ == "FuncDeprecatedAfter"
    assert (
        func_deprecated_after.__tool_description__ == "Test description for func_deprecated_after"
    )
    assert func_deprecated_after.__tool_requires_auth__ is None

    @tool
    @tool.deprecated(message)
    def func_deprecated_before(x):
        """Test description for func_deprecated_before"""
        return x

    assert hasattr(func_deprecated_before, "__tool_deprecation_message__")
    assert func_deprecated_before.__tool_deprecation_message__ == message
    assert func_deprecated_before.__tool_name__ == "FuncDeprecatedBefore"
    assert (
        func_deprecated_before.__tool_description__ == "Test description for func_deprecated_before"
    )
    assert func_deprecated_before.__tool_requires_auth__ is None


def test_tool_deprecated_ordering_with_auth():
    """
    Checks the behavior of @tool.deprecated when used with authentication.
    The order of the decorators should not matter.
    """
    message = "Deprecated: please use new_tool instead."

    @tool.deprecated(message)
    @tool(requires_auth=OAuth2(id="my_auth_id", scopes=["test_scope"]))
    def func_deprecated_after_auth(x):
        """Test description for func_deprecated_after_auth"""
        return x

    assert hasattr(func_deprecated_after_auth, "__tool_deprecation_message__")
    assert func_deprecated_after_auth.__tool_deprecation_message__ == message
    assert func_deprecated_after_auth.__tool_name__ == "FuncDeprecatedAfterAuth"
    assert (
        func_deprecated_after_auth.__tool_description__
        == "Test description for func_deprecated_after_auth"
    )
    assert func_deprecated_after_auth.__tool_requires_auth__ is not None

    @tool(requires_auth=OAuth2(id="my_auth_id", scopes=["test_scope"]))
    @tool.deprecated(message)
    def func_deprecated_before_auth(x):
        """Test description for func_deprecated_before_auth"""
        return x

    assert hasattr(func_deprecated_before_auth, "__tool_deprecation_message__")
    assert func_deprecated_before_auth.__tool_deprecation_message__ == message
    assert func_deprecated_before_auth.__tool_name__ == "FuncDeprecatedBeforeAuth"
    assert (
        func_deprecated_before_auth.__tool_description__
        == "Test description for func_deprecated_before_auth"
    )
    assert func_deprecated_before_auth.__tool_requires_auth__ is not None


# MCP-specific ``execution`` / ``taskSupport`` semantics live in
# arcade-mcp-server. The corresponding tests live in
# ``libs/tests/arcade_mcp_server/test_tool_wrapper.py`` (see the
# ``TestRelocatedFromArcadeTdk`` class). arcade-tdk itself stays
# protocol-agnostic and no longer exposes an ``execution`` kwarg.


class TestArcadeTdkToolHasNoMCPSpecificKwargs:
    """Pin the layering boundary: arcade-tdk's ``@tool`` does not accept
    or document MCP-specific concepts. These tests fail loudly if MCP
    surface re-leaks into arcade-tdk in a future change.
    """

    def test_arcade_tdk_tool_does_not_accept_execution_kwarg(self):
        with pytest.raises(TypeError, match="unexpected keyword argument 'execution'"):

            @tool(execution="anything")
            def f() -> str:
                return "x"

    def test_arcade_tdk_tool_signature_has_no_execution_parameter(self):
        assert "execution" not in inspect.signature(tool).parameters

    def test_arcade_tdk_tool_docstring_does_not_mention_mcp_or_taskSupport(self):
        doc = (tool.__doc__ or "").lower()
        assert "mcp" not in doc
        assert "tasksupport" not in doc
        assert "arcade_mcp_server" not in doc
