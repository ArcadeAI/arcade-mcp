"""Tests for the arcade connect command."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from arcade_cli.connect import (
    ensure_login,
    fetch_account_gateways,
    fetch_available_toolkits,
    get_toolkit_examples,
    run_connect,
)

# ---------------------------------------------------------------------------
# get_toolkit_examples
# ---------------------------------------------------------------------------


class TestGetToolkitExamples:
    def test_known_toolkit_returns_examples(self) -> None:
        examples = get_toolkit_examples(["github"])
        assert len(examples) == 2
        assert any("pull request" in e.lower() for e in examples)

    def test_multiple_toolkits(self) -> None:
        examples = get_toolkit_examples(["github", "slack"])
        assert len(examples) == 4

    def test_unknown_toolkit_returns_fallback(self) -> None:
        examples = get_toolkit_examples(["nonexistent_toolkit_xyz"])
        assert len(examples) == 1
        assert "assistant" in examples[0].lower()

    def test_strips_arcade_prefix(self) -> None:
        examples = get_toolkit_examples(["arcade-github"])
        assert len(examples) == 2

    def test_empty_list_returns_fallback(self) -> None:
        examples = get_toolkit_examples([])
        assert len(examples) == 1


# ---------------------------------------------------------------------------
# ensure_login
# ---------------------------------------------------------------------------


class TestEnsureLogin:
    @patch("arcade_cli.connect.console")
    @patch("arcade_cli.authn.get_valid_access_token", return_value="tok_abc")
    @patch("arcade_cli.authn.check_existing_login", return_value=True)
    def test_already_logged_in_returns_token(
        self, _check: MagicMock, _get_token: MagicMock, _console: MagicMock
    ) -> None:
        token = ensure_login()
        assert token == "tok_abc"

    @patch("arcade_cli.connect.console")
    @patch("arcade_cli.authn.get_valid_access_token", return_value="tok_new")
    @patch("arcade_cli.authn.save_credentials_from_whoami")
    @patch("arcade_cli.authn.check_existing_login", return_value=False)
    def test_not_logged_in_triggers_oauth(
        self,
        _check: MagicMock,
        _save: MagicMock,
        _get_token: MagicMock,
        _console: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.email = "user@example.com"
        mock_result.tokens = MagicMock()
        mock_result.whoami = MagicMock()

        with patch(
            "arcade_cli.authn.perform_oauth_login",
            return_value=mock_result,
        ):
            token = ensure_login()
        assert token == "tok_new"


# ---------------------------------------------------------------------------
# fetch_available_toolkits
# ---------------------------------------------------------------------------


class TestFetchAvailableToolkits:
    def test_groups_by_toolkit_name(self) -> None:
        tool1 = SimpleNamespace(toolkit=SimpleNamespace(name="github"), name="GithubListPRs")
        tool2 = SimpleNamespace(toolkit=SimpleNamespace(name="github"), name="GithubCreateIssue")
        tool3 = SimpleNamespace(toolkit=SimpleNamespace(name="slack"), name="SlackSendMessage")

        mock_client = MagicMock()
        mock_client.tools.list.return_value = [tool1, tool2, tool3]

        with patch("arcade_cli.utils.get_arcade_client", return_value=mock_client):
            result = fetch_available_toolkits("https://api.example.com", skip_cache=True)

        assert "github" in result
        assert len(result["github"]) == 2
        assert "slack" in result
        assert len(result["slack"]) == 1

    @patch("arcade_cli.connect.console")
    def test_connection_error_returns_empty(self, _console: MagicMock) -> None:
        from arcadepy import APIConnectionError

        mock_client = MagicMock()
        mock_client.tools.list.side_effect = APIConnectionError(request=MagicMock())

        with patch("arcade_cli.utils.get_arcade_client", return_value=mock_client):
            result = fetch_available_toolkits("https://api.example.com", skip_cache=True)

        assert result == {}


# ---------------------------------------------------------------------------
# fetch_account_gateways
# ---------------------------------------------------------------------------


class TestFetchAccountGateways:
    def test_returns_gateway_list(self) -> None:
        worker = SimpleNamespace(
            id="my-gw",
            enabled=True,
            type="mcp",
            mcp=SimpleNamespace(uri="https://api.arcade.dev/mcp/my-gw"),
        )
        mock_client = MagicMock()
        mock_client.workers.list.return_value = SimpleNamespace(items=[worker])

        with patch("arcade_cli.utils.get_arcade_client", return_value=mock_client):
            result = fetch_account_gateways("https://api.example.com")

        assert len(result) == 1
        assert result[0]["id"] == "my-gw"
        assert result[0]["enabled"] is True
        assert result[0]["uri"] == "https://api.arcade.dev/mcp/my-gw"

    @patch("arcade_cli.connect.console")
    def test_connection_error_returns_empty(self, _console: MagicMock) -> None:
        from arcadepy import APIConnectionError

        mock_client = MagicMock()
        mock_client.workers.list.side_effect = APIConnectionError(request=MagicMock())

        with patch("arcade_cli.utils.get_arcade_client", return_value=mock_client):
            result = fetch_account_gateways("https://api.example.com")

        assert result == []


# ---------------------------------------------------------------------------
# run_quickstart — gateway mode (direct slug)
# ---------------------------------------------------------------------------


class TestRunQuickstartGateway:
    def test_gateway_mode_configures_claude(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="claude",
                gateway="my-production-gw",
                config_path=config_path,
            )

        config = json.loads(config_path.read_text(encoding="utf-8"))
        entry = config["mcpServers"]["my-production-gw"]
        assert entry["url"] == "https://api.arcade.dev/mcp/my-production-gw"
        # OAuth mode: no headers (MCP client handles auth natively)
        assert "headers" not in entry

    def test_gateway_mode_configures_cursor(self, tmp_path: Path) -> None:
        config_path = tmp_path / "cursor.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="cursor",
                gateway="test-gw",
                config_path=config_path,
            )

        config = json.loads(config_path.read_text(encoding="utf-8"))
        entry = config["mcpServers"]["test-gw"]
        assert entry["type"] == "sse"
        assert "api.arcade.dev/mcp/test-gw" in entry["url"]

    def test_gateway_mode_configures_vscode(self, tmp_path: Path) -> None:
        config_path = tmp_path / "vscode.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="vscode",
                gateway="test-gw",
                config_path=config_path,
            )

        config = json.loads(config_path.read_text(encoding="utf-8"))
        entry = config["servers"]["test-gw"]
        assert entry["type"] == "http"
        assert "api.arcade.dev/mcp/test-gw" in entry["url"]


# ---------------------------------------------------------------------------
# run_quickstart — toolkit mode (creates gateway)
# ---------------------------------------------------------------------------


class TestRunQuickstartToolkit:
    def test_toolkit_creates_gateway_and_configures_client(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch(
                "arcade_cli.connect.fetch_available_toolkits",
                return_value={"github": ["Github.ListPRs", "Github.CreateIssue"]},
            ),
            patch(
                "arcade_cli.connect.create_gateway",
                return_value={"slug": "github", "id": "gw-123"},
            ) as mock_create,
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="claude",
                toolkits=["github"],
                config_path=config_path,
            )

        # Verify gateway was created with the right tools
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["name"] == "github"
        assert "Github.ListPRs" in call_kwargs["tool_allow_list"]
        assert "Github.CreateIssue" in call_kwargs["tool_allow_list"]

        # Verify client config points to the gateway (OAuth — no headers)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        entry = config["mcpServers"]["github"]
        assert entry["url"] == "https://api.arcade.dev/mcp/github"
        assert "headers" not in entry

    def test_multiple_toolkits_creates_combined_gateway(self, tmp_path: Path) -> None:
        config_path = tmp_path / "cursor.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch(
                "arcade_cli.connect.fetch_available_toolkits",
                return_value={
                    "github": ["Github.ListPRs"],
                    "slack": ["Slack.SendMessage"],
                },
            ),
            patch(
                "arcade_cli.connect.create_gateway",
                return_value={"slug": "github-slack", "id": "gw-456"},
            ) as mock_create,
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="cursor",
                toolkits=["github", "slack"],
                config_path=config_path,
            )

        call_kwargs = mock_create.call_args[1]
        assert "Github.ListPRs" in call_kwargs["tool_allow_list"]
        assert "Slack.SendMessage" in call_kwargs["tool_allow_list"]

        config = json.loads(config_path.read_text(encoding="utf-8"))
        entry = config["mcpServers"]["github-slack"]
        assert entry["type"] == "sse"
        assert "api.arcade.dev/mcp/github-slack" in entry["url"]


# ---------------------------------------------------------------------------
# run_quickstart — --all and interactive modes
# ---------------------------------------------------------------------------


class TestRunQuickstartInteractive:
    def test_all_mode_creates_gateway_for_all_toolkits(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch(
                "arcade_cli.connect.fetch_available_toolkits",
                return_value={
                    "github": ["Github.ListPRs"],
                    "slack": ["Slack.SendMessage"],
                },
            ),
            patch(
                "arcade_cli.connect.create_gateway",
                return_value={"slug": "github-slack", "id": "gw-789"},
            ) as mock_create,
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="claude",
                all_tools=True,
                config_path=config_path,
            )

        call_kwargs = mock_create.call_args[1]
        assert len(call_kwargs["tool_allow_list"]) == 2

        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert "mcpServers" in config

    def test_all_mode_no_toolkits_exits(self) -> None:
        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch(
                "arcade_cli.connect.fetch_available_toolkits",
                return_value={},
            ),
            patch("arcade_cli.connect.console"),
            pytest.raises(SystemExit),
        ):
            run_connect(client="claude", all_tools=True)

    def test_toolkit_not_found_exits(self) -> None:
        """When specified toolkit has no tools in the account, exit with error."""
        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch(
                "arcade_cli.connect.fetch_available_toolkits",
                return_value={},
            ),
            patch("arcade_cli.connect.console"),
            pytest.raises(SystemExit),
        ):
            run_connect(client="claude", toolkits=["nonexistent"])
