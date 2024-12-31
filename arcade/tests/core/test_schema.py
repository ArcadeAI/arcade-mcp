from arcade.core.schema import ToolAuthorizationContext, ToolContext


def test_get_auth_token_or_empty_with_token():
    expected_token = "test_token"  # noqa: S105
    auth_context = ToolAuthorizationContext(token=expected_token)
    tool_context = ToolContext(authorization=auth_context)

    actual_token = tool_context.get_auth_token_or_empty()

    assert actual_token == expected_token


def test_get_auth_token_or_empty_without_token():
    auth_context = ToolAuthorizationContext(token=None)
    tool_context = ToolContext(authorization=auth_context)

    assert tool_context.get_auth_token_or_empty() == ""


def test_get_auth_token_or_empty_no_authorization():
    tool_context = ToolContext(authorization=None)

    assert tool_context.get_auth_token_or_empty() == ""
