import tempfile
from unittest.mock import MagicMock, patch

import httpx
import pytest
from arcade_cli.secret import (
    _delete_secret,
    _get_secrets,
    _remove_inline_comment,
    _upsert_secret,
    load_env_file,
    print_secret_table,
)


class TestPrintSecretTable:
    """Tests for print_secret_table function."""

    def test_print_secret_table_empty(self, capsys):
        """Test printing a table with no secrets."""
        secrets = []
        print_secret_table(secrets)

        captured = capsys.readouterr()
        assert "Tool Secrets" in captured.out


class TestLoadEnvFile:
    """Tests for load_env_file function."""

    def test_load_env_file_basic(self):
        """Test loading a basic .env file."""
        env_content = """
KEY1=value1
KEY2=value2
# This is a comment
KEY3=value3
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            secrets = load_env_file(f.name)

        assert secrets == {
            "KEY1": "value1",
            "KEY2": "value2",
            "KEY3": "value3",
        }

    def test_load_env_file_with_quotes(self):
        """Test loading .env file with quoted values."""
        env_content = """
KEY1="quoted value"
KEY2='single quoted'
KEY3="value with = sign"
KEY4="value with # comment inside"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            secrets = load_env_file(f.name)

        assert secrets == {
            "KEY1": "quoted value",
            "KEY2": "single quoted",
            "KEY3": "value with = sign",
            "KEY4": "value with # comment inside",
        }

    def test_load_env_file_with_inline_comments(self):
        """Test loading .env file with inline comments."""
        env_content = """
KEY1=value1 # inline comment
KEY2="quoted value" # comment after quote
KEY3=value3# no space before comment
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            secrets = load_env_file(f.name)

        assert secrets == {
            "KEY1": "value1",
            "KEY2": "quoted value",
            "KEY3": "value3# no space before comment",  # No space, so not treated as comment
        }

    def test_load_env_file_skip_empty_and_invalid(self):
        """Test that empty lines, comments, and invalid entries are skipped."""
        env_content = """
# Comment line
KEY1=value1

KEY2=
=value_without_key
KEY3=value3
invalid_line_without_equals
KEY4=value4
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            secrets = load_env_file(f.name)

        assert secrets == {
            "KEY1": "value1",
            "KEY3": "value3",
            "KEY4": "value4",
        }


class TestRemoveInlineComment:
    """Tests for _remove_inline_comment function."""

    def test_remove_inline_comment_unquoted(self):
        """Test removing inline comments from unquoted values."""
        assert _remove_inline_comment("value # comment") == "value"
        assert _remove_inline_comment("value# no space") == "value# no space"
        assert _remove_inline_comment("value") == "value"
        assert _remove_inline_comment("value with spaces # comment") == "value with spaces"

    def test_remove_inline_comment_double_quoted(self):
        """Test removing inline comments from double-quoted values."""
        assert _remove_inline_comment('"quoted value" # comment') == "quoted value"
        assert _remove_inline_comment('"value with # inside"') == "value with # inside"
        assert _remove_inline_comment('"quoted value"') == "quoted value"
        assert _remove_inline_comment('"unclosed quote') == '"unclosed quote'

    def test_remove_inline_comment_single_quoted(self):
        """Test removing inline comments from single-quoted values."""
        assert _remove_inline_comment("'quoted value' # comment") == "quoted value"
        assert _remove_inline_comment("'value with # inside'") == "value with # inside"
        assert _remove_inline_comment("'quoted value'") == "quoted value"
        assert _remove_inline_comment("'unclosed quote") == "'unclosed quote"

    def test_remove_inline_comment_edge_cases(self):
        """Test edge cases for inline comment removal."""
        assert _remove_inline_comment("") == ""


class TestUpsertSecretToEngine:
    """Tests for _upsert_secret function."""

    @patch("arcade_cli.secret.get_auth_headers")
    @patch("arcade_cli.secret.get_org_scoped_url")
    @patch("arcade_cli.secret.httpx.put")
    def test_upsert_secret_success(self, mock_put, mock_get_url, mock_get_headers):
        """Test successful secret upsert."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_put.return_value = mock_response
        mock_get_url.return_value = "https://api.example.com/v1/org/test-org/secrets/SECRET_KEY"
        mock_get_headers.return_value = {"Authorization": "Bearer test-api-key"}

        _upsert_secret("SECRET_KEY", "secret-value")

        mock_put.assert_called_once_with(
            "https://api.example.com/v1/org/test-org/secrets/SECRET_KEY",
            headers={"Authorization": "Bearer test-api-key"},
            json={"description": "Secret set via CLI", "value": "secret-value"},
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("arcade_cli.secret.get_auth_headers")
    @patch("arcade_cli.secret.get_org_scoped_url")
    @patch("arcade_cli.secret.httpx.put")
    def test_upsert_secret_http_error(self, mock_put, mock_get_url, mock_get_headers):
        """Test secret upsert with HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=MagicMock()
        )
        mock_put.return_value = mock_response
        mock_get_url.return_value = "https://api.example.com/v1/org/test-org/secrets/SECRET_KEY"
        mock_get_headers.return_value = {"Authorization": "Bearer test-api-key"}

        with pytest.raises(httpx.HTTPStatusError):
            _upsert_secret("SECRET_KEY", "secret-value")


class TestGetSecretsFromEngine:
    """Tests for _get_secrets function."""

    @patch("arcade_cli.secret.get_auth_headers")
    @patch("arcade_cli.secret.get_org_scoped_url")
    @patch("arcade_cli.secret.httpx.get")
    def test_get_secrets_success(self, mock_get, mock_get_url, mock_get_headers):
        """Test successful secrets retrieval."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "items": [
                {"key": "SECRET1", "id": "id1"},
                {"key": "SECRET2", "id": "id2"},
            ]
        }
        mock_get.return_value = mock_response
        mock_get_url.return_value = "https://api.example.com/v1/org/test-org/secrets"
        mock_get_headers.return_value = {"Authorization": "Bearer test-api-key"}

        secrets = _get_secrets()

        assert secrets == [
            {"key": "SECRET1", "id": "id1"},
            {"key": "SECRET2", "id": "id2"},
        ]
        mock_get.assert_called_once_with(
            "https://api.example.com/v1/org/test-org/secrets",
            headers={"Authorization": "Bearer test-api-key"},
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("arcade_cli.secret.get_auth_headers")
    @patch("arcade_cli.secret.get_org_scoped_url")
    @patch("arcade_cli.secret.httpx.get")
    def test_get_secrets_http_error(self, mock_get, mock_get_url, mock_get_headers):
        """Test secrets retrieval with HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=MagicMock()
        )
        mock_get.return_value = mock_response
        mock_get_url.return_value = "https://api.example.com/v1/org/test-org/secrets"
        mock_get_headers.return_value = {"Authorization": "Bearer test-api-key"}

        with pytest.raises(httpx.HTTPStatusError):
            _get_secrets()


class TestDeleteSecretFromEngine:
    """Tests for _delete_secret function."""

    @patch("arcade_cli.secret.get_auth_headers")
    @patch("arcade_cli.secret.get_org_scoped_url")
    @patch("arcade_cli.secret.httpx.delete")
    def test_delete_secret_success(self, mock_delete, mock_get_url, mock_get_headers):
        """Test successful secret deletion."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_delete.return_value = mock_response
        mock_get_url.return_value = "https://api.example.com/v1/org/test-org/secrets/secret-id-123"
        mock_get_headers.return_value = {"Authorization": "Bearer test-api-key"}

        _delete_secret("secret-id-123")

        mock_delete.assert_called_once_with(
            "https://api.example.com/v1/org/test-org/secrets/secret-id-123",
            headers={"Authorization": "Bearer test-api-key"},
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("arcade_cli.secret.get_auth_headers")
    @patch("arcade_cli.secret.get_org_scoped_url")
    @patch("arcade_cli.secret.httpx.delete")
    def test_delete_secret_http_error(self, mock_delete, mock_get_url, mock_get_headers):
        """Test secret deletion with HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock()
        )
        mock_delete.return_value = mock_response
        mock_get_url.return_value = "https://api.example.com/v1/org/test-org/secrets/secret-id-123"
        mock_get_headers.return_value = {"Authorization": "Bearer test-api-key"}

        with pytest.raises(httpx.HTTPStatusError):
            _delete_secret("secret-id-123")
