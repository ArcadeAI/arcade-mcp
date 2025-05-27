import pytest
from arcade_core.schema import (
    ToolAuthorizationContext,
    ToolContext,
    ToolMetadataItem,
    ToolSecretItem,
)


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


def test_get_secret_valid():
    key = "my_key"
    val = "secret_value"
    secrets = [ToolSecretItem(key=key, value=val)]
    tool_context = ToolContext(secrets=secrets)

    # When the secret exists, get_secret should return its value.
    actual_secret = tool_context.get_secret(key)
    assert actual_secret == val


def test_get_secret_with_case_insensitive_key():
    key = "My_key"
    val = "secret_value"
    secrets = [ToolSecretItem(key=key, value=val)]
    tool_context = ToolContext(secrets=secrets)

    assert tool_context.get_secret(key.upper()) == val
    assert tool_context.get_secret(key.lower()) == val


def test_get_secret_key_not_found():
    key = "nonexistent_key"
    secrets = [ToolSecretItem(key="other_key", value="another_secret")]
    tool_context = ToolContext(secrets=secrets)

    # When the key is not found, get_secret should raise a ValueError.
    with pytest.raises(ValueError, match=f"Secret {key} not found in context."):
        tool_context.get_secret(key)


def test_get_secret_when_secrets_is_none():
    tool_context = ToolContext(secrets=None)

    # When no secrets dictionary is provided, get_secret should raise a ValueError.
    with pytest.raises(ValueError, match="Secrets not found in context."):
        tool_context.get_secret("missing_key")


def test_get_secret_with_empty_key():
    tool_context = ToolContext(secrets=[])

    with pytest.raises(ValueError, match="Secret key passed to get_secret cannot be empty."):
        tool_context.get_secret("")


def test_get_metadata_valid():
    key = "my_key"
    val = "metadata_value"
    metadata = [ToolMetadataItem(key=key, value=val)]
    tool_context = ToolContext(metadata=metadata)

    assert tool_context.get_metadata(key) == val


def test_get_metadata_with_case_insensitive_key():
    key = "My_key"
    val = "metadata_value"
    metadata = [ToolMetadataItem(key=key, value=val)]
    tool_context = ToolContext(metadata=metadata)

    assert tool_context.get_metadata(key.upper()) == val
    assert tool_context.get_metadata(key.lower()) == val


def test_get_metadata_key_not_found():
    key = "nonexistent_key"
    metadata = [ToolMetadataItem(key="other_key", value="another_metadata")]
    tool_context = ToolContext(metadata=metadata)

    with pytest.raises(ValueError, match=f"Metadata {key} not found in context."):
        tool_context.get_metadata(key)


def test_get_metadata_when_metadata_is_none():
    tool_context = ToolContext(metadata=None)

    with pytest.raises(ValueError, match="Metadatas not found in context."):
        tool_context.get_metadata("missing_key")


def test_get_metadata_with_empty_key():
    tool_context = ToolContext(metadata=[])

    with pytest.raises(ValueError, match="Metadata key passed to get_metadata cannot be empty."):
        tool_context.get_metadata("")
