"""Tests for the arcade connect command."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from arcade_cli.connect import (
    _get_context_key,
    _read_cache,
    _write_cache,
    create_gateway,
    ensure_login,
    fetch_available_toolkits,
    find_matching_gateway,
    get_toolkit_examples,
    list_gateways,
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
# Cache functions
# ---------------------------------------------------------------------------


class TestCache:
    def test_write_and_read_cache(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import arcade_cli.connect as mod

        cache_file = tmp_path / "tools.json"
        monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(mod, "_CACHE_FILE", cache_file)
        monkeypatch.setattr(mod, "_get_context_key", lambda: "org:proj")

        toolkits = {"github": ["Github.CreateIssue"]}
        _write_cache(toolkits)
        assert cache_file.exists()

        result = _read_cache()
        assert result == toolkits

    def test_read_cache_returns_none_when_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import arcade_cli.connect as mod

        monkeypatch.setattr(mod, "_CACHE_FILE", tmp_path / "nonexistent.json")
        assert _read_cache() is None

    def test_read_cache_invalidates_on_context_change(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import arcade_cli.connect as mod

        cache_file = tmp_path / "tools.json"
        monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(mod, "_CACHE_FILE", cache_file)

        # Write with one context
        monkeypatch.setattr(mod, "_get_context_key", lambda: "org1:proj1")
        _write_cache({"github": ["Github.CreateIssue"]})

        # Read with different context
        monkeypatch.setattr(mod, "_get_context_key", lambda: "org2:proj2")
        assert _read_cache() is None

    def test_get_context_key_returns_unknown_without_credentials(self) -> None:
        # On CI or without credentials, should return "unknown" not raise
        with patch(
            "arcade_cli.utils.get_org_project_context",
            side_effect=Exception("no creds"),
        ):
            assert _get_context_key() == "unknown"


# ---------------------------------------------------------------------------
# find_matching_gateway
# ---------------------------------------------------------------------------


class TestFindMatchingGateway:
    def test_finds_superset_gateway(self) -> None:
        gateways = [
            {
                "slug": "my-gw",
                "tool_filter": {"allowed_tools": ["Github.CreateIssue", "Github.ListPRs"]},
            }
        ]
        result = find_matching_gateway(gateways, ["Github.CreateIssue"])
        assert result is not None
        assert result["slug"] == "my-gw"

    def test_returns_none_when_no_match(self) -> None:
        gateways = [{"slug": "my-gw", "tool_filter": {"allowed_tools": ["Slack.SendMessage"]}}]
        result = find_matching_gateway(gateways, ["Github.CreateIssue"])
        assert result is None

    def test_returns_none_for_empty_gateways(self) -> None:
        assert find_matching_gateway([], ["Github.CreateIssue"]) is None

    def test_skips_gateway_with_wrong_auth_type(self) -> None:
        gateways = [
            {
                "slug": "oauth-gw",
                "auth_type": "arcade",
                "tool_filter": {"allowed_tools": ["Github.CreateIssue"]},
            }
        ]
        # Looking for arcade_header auth — should not match the OAuth gateway
        result = find_matching_gateway(gateways, ["Github.CreateIssue"], auth_type="arcade_header")
        assert result is None

    def test_matches_gateway_with_correct_auth_type(self) -> None:
        gateways = [
            {
                "slug": "apikey-gw",
                "auth_type": "arcade_header",
                "tool_filter": {"allowed_tools": ["Github.CreateIssue"]},
            }
        ]
        result = find_matching_gateway(gateways, ["Github.CreateIssue"], auth_type="arcade_header")
        assert result is not None
        assert result["slug"] == "apikey-gw"


# ---------------------------------------------------------------------------
# list_gateways
# ---------------------------------------------------------------------------


class TestListGateways:
    @patch("arcade_cli.connect.httpx.get")
    @patch("arcade_cli.utils.get_org_project_context", return_value=("org1", "proj1"))
    def test_returns_items(self, _ctx: MagicMock, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": [{"slug": "gw1"}]}
        mock_get.return_value = mock_resp

        result = list_gateways("tok")
        assert len(result) == 1
        assert result[0]["slug"] == "gw1"

    @patch("arcade_cli.connect.httpx.get")
    @patch("arcade_cli.utils.get_org_project_context", return_value=("org1", "proj1"))
    def test_returns_empty_on_error(self, _ctx: MagicMock, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        result = list_gateways("tok")
        assert result == []


# ---------------------------------------------------------------------------
# create_gateway
# ---------------------------------------------------------------------------


class TestCreateGateway:
    @patch("arcade_cli.connect.httpx.post")
    @patch("arcade_cli.utils.get_org_project_context", return_value=("org1", "proj1"))
    def test_returns_gateway_dict(self, _ctx: MagicMock, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"slug": "my-gw", "id": "gw-123"}
        mock_post.return_value = mock_resp

        result = create_gateway("tok", "my-gw", ["Github.CreateIssue"])
        assert result["slug"] == "my-gw"

    @patch("arcade_cli.connect.httpx.post")
    @patch("arcade_cli.utils.get_org_project_context", return_value=("org1", "proj1"))
    def test_unwraps_items_envelope(self, _ctx: MagicMock, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": [{"slug": "gw-abc", "id": "123"}]}
        mock_post.return_value = mock_resp

        result = create_gateway("tok", "test", ["Github.CreateIssue"])
        assert result["slug"] == "gw-abc"

    @patch("arcade_cli.connect.httpx.post")
    @patch("arcade_cli.utils.get_org_project_context", return_value=("org1", "proj1"))
    def test_raises_on_error(self, _ctx: MagicMock, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "bad request"
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="400"):
            create_gateway("tok", "test", ["Github.CreateIssue"])

    @patch("arcade_cli.connect.httpx.post")
    @patch("arcade_cli.utils.get_org_project_context", return_value=("org1", "proj1"))
    def test_passes_slug_and_auth_type(self, _ctx: MagicMock, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"slug": "custom"}
        mock_post.return_value = mock_resp

        create_gateway("tok", "test", ["T.A"], auth_type="arcade_header", slug="custom")
        call_body = mock_post.call_args[1]["json"]
        assert call_body["auth_type"] == "arcade_header"
        assert call_body["slug"] == "custom"


# ---------------------------------------------------------------------------
# _resolve_gateway_slug
# ---------------------------------------------------------------------------


class TestResolveGatewaySlug:
    @patch("arcade_cli.connect.list_gateways")
    def test_matches_by_slug(self, mock_list: MagicMock) -> None:
        from arcade_cli.connect import _resolve_gateway_slug

        mock_list.return_value = [{"slug": "pascal_opencode", "name": "opencode"}]
        assert _resolve_gateway_slug("pascal_opencode", "tok") == "pascal_opencode"

    @patch("arcade_cli.connect.list_gateways")
    def test_matches_by_name(self, mock_list: MagicMock) -> None:
        from arcade_cli.connect import _resolve_gateway_slug

        mock_list.return_value = [{"slug": "pascal_opencode", "name": "opencode"}]
        assert _resolve_gateway_slug("opencode", "tok") == "pascal_opencode"

    @patch("arcade_cli.connect.list_gateways")
    def test_falls_back_to_input(self, mock_list: MagicMock) -> None:
        from arcade_cli.connect import _resolve_gateway_slug

        mock_list.return_value = [{"slug": "other", "name": "other"}]
        assert _resolve_gateway_slug("unknown-gw", "tok") == "unknown-gw"


# ---------------------------------------------------------------------------
# run_connect — tool-only mode
# ---------------------------------------------------------------------------


class TestRunConnectToolOnly:
    def test_tool_only_creates_gateway(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            _mock_list_gw(),
            patch(
                "arcade_cli.connect.create_gateway",
                return_value={"slug": "custom-tools", "id": "gw-999"},
            ),
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="claude",
                tools=["Github.CreateIssue", "Slack.SendMessage"],
                config_path=config_path,
            )

        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert "mcpServers" in config


# ---------------------------------------------------------------------------
# Helpers: fresh mocks per test (patch objects are single-use as context managers)
# ---------------------------------------------------------------------------


def _mock_list_gw():  # type: ignore[no-untyped-def]
    return patch("arcade_cli.connect.list_gateways", return_value=[])


def _mock_resolve_slug():  # type: ignore[no-untyped-def]
    return patch("arcade_cli.connect._resolve_gateway_slug", side_effect=lambda gw, *a, **kw: gw)


# ---------------------------------------------------------------------------
# run_connect — gateway mode (direct slug)
# ---------------------------------------------------------------------------


class TestRunConnectGateway:
    def test_gateway_mode_configures_claude(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            _mock_resolve_slug(),
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
        assert "headers" not in entry

    def test_gateway_mode_configures_cursor(self, tmp_path: Path) -> None:
        config_path = tmp_path / "cursor.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            _mock_resolve_slug(),
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
            _mock_resolve_slug(),
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
# run_connect — toolkit mode (creates gateway)
# ---------------------------------------------------------------------------


class TestRunConnectToolkit:
    def test_toolkit_creates_gateway_and_configures_client(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch(
                "arcade_cli.connect.fetch_available_toolkits",
                return_value={"github": ["Github.ListPRs", "Github.CreateIssue"]},
            ),
            _mock_list_gw(),
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

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["name"] == "github"
        assert "Github.ListPRs" in call_kwargs["tool_allow_list"]
        assert "Github.CreateIssue" in call_kwargs["tool_allow_list"]

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
            _mock_list_gw(),
            patch(
                "arcade_cli.connect.create_gateway",
                return_value={"slug": "github-slack", "id": "gw-456"},
            ),
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="cursor",
                toolkits=["github", "slack"],
                config_path=config_path,
            )

        config = json.loads(config_path.read_text(encoding="utf-8"))
        entry = config["mcpServers"]["github-slack"]
        assert entry["type"] == "sse"
        assert "api.arcade.dev/mcp/github-slack" in entry["url"]


# ---------------------------------------------------------------------------
# run_connect — --all and interactive modes
# ---------------------------------------------------------------------------


class TestRunConnectInteractive:
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
            _mock_list_gw(),
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
            patch("arcade_cli.connect.fetch_available_toolkits", return_value={}),
            patch("arcade_cli.connect.console"),
            pytest.raises(SystemExit),
        ):
            run_connect(client="claude", all_tools=True)

    def test_toolkit_not_found_exits(self) -> None:
        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch("arcade_cli.connect.fetch_available_toolkits", return_value={}),
            _mock_list_gw(),
            patch("arcade_cli.connect.console"),
            pytest.raises(SystemExit),
        ):
            run_connect(client="claude", toolkits=["nonexistent"])


# ---------------------------------------------------------------------------
# create_project_api_key
# ---------------------------------------------------------------------------


class TestCreateProjectApiKey:
    @patch("arcade_cli.connect.httpx.post")
    @patch("arcade_cli.utils.get_org_project_context", return_value=("org1", "proj1"))
    def test_returns_api_key(self, _ctx: MagicMock, mock_post: MagicMock) -> None:
        from arcade_cli.connect import create_project_api_key

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"api_key": "arc_test123"}
        mock_post.return_value = mock_resp

        result = create_project_api_key("tok", label="test")
        assert result == "arc_test123"

    @patch("arcade_cli.connect.httpx.post")
    @patch("arcade_cli.utils.get_org_project_context", return_value=("org1", "proj1"))
    def test_raises_on_error(self, _ctx: MagicMock, mock_post: MagicMock) -> None:
        from arcade_cli.connect import create_project_api_key

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "forbidden"
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="403"):
            create_project_api_key("tok")


# ---------------------------------------------------------------------------
# prompt_toolkit_selection
# ---------------------------------------------------------------------------


class TestPromptToolkitSelection:
    from arcade_cli.connect import prompt_toolkit_selection

    def test_selects_single_toolkit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from arcade_cli.connect import prompt_toolkit_selection

        monkeypatch.setattr("builtins.input", lambda _: "1")
        with patch("arcade_cli.connect.console"):
            result = prompt_toolkit_selection({"github": ["Github.CreateIssue"]})
        assert result == ["github"]

    def test_selects_multiple(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from arcade_cli.connect import prompt_toolkit_selection

        # Bundles come first, then individual toolkits, then "all"
        # With no matching bundles, "github" is option 1, "slack" is 2, "all" is 3
        monkeypatch.setattr("builtins.input", lambda _: "1,2")
        with patch("arcade_cli.connect.console"):
            result = prompt_toolkit_selection({
                "github": ["Github.CreateIssue"],
                "slack": ["Slack.Send"],
            })
        assert "github" in result
        assert "slack" in result

    def test_empty_input_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from arcade_cli.connect import prompt_toolkit_selection

        monkeypatch.setattr("builtins.input", lambda _: "")
        with patch("arcade_cli.connect.console"), pytest.raises(SystemExit):
            prompt_toolkit_selection({"github": ["Github.CreateIssue"]})

    def test_empty_available_exits(self) -> None:
        from arcade_cli.connect import prompt_toolkit_selection

        with patch("arcade_cli.connect.console"), pytest.raises(SystemExit):
            prompt_toolkit_selection({})


# ---------------------------------------------------------------------------
# run_connect — gateway reuse and api-key paths
# ---------------------------------------------------------------------------


class TestRunConnectAdvanced:
    def test_reuses_existing_gateway(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"

        existing_gw = {
            "slug": "existing-gw",
            "name": "existing",
            "tool_filter": {"allowed_tools": ["Github.CreateIssue"]},
        }

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch(
                "arcade_cli.connect.fetch_available_toolkits",
                return_value={"github": ["Github.CreateIssue"]},
            ),
            patch("arcade_cli.connect.list_gateways", return_value=[existing_gw]),
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="claude",
                toolkits=["github"],
                config_path=config_path,
            )

        config = json.loads(config_path.read_text(encoding="utf-8"))
        entry = config["mcpServers"]["github"]
        assert "existing-gw" in entry["url"]

    def test_gateway_with_api_key(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            _mock_resolve_slug(),
            patch("arcade_cli.connect.create_project_api_key", return_value="arc_key123"),
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="claude",
                gateway="my-gw",
                use_api_key=True,
                config_path=config_path,
            )

        config = json.loads(config_path.read_text(encoding="utf-8"))
        entry = config["mcpServers"]["my-gw"]
        assert entry["headers"]["Authorization"] == "Bearer arc_key123"

    def test_toolkit_with_custom_slug(self, tmp_path: Path) -> None:
        config_path = tmp_path / "claude.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch(
                "arcade_cli.connect.fetch_available_toolkits",
                return_value={"github": ["Github.CreateIssue"]},
            ),
            _mock_list_gw(),
            patch(
                "arcade_cli.connect.create_gateway",
                return_value={"slug": "my-custom", "id": "gw-1"},
            ),
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="claude",
                toolkits=["github"],
                gateway_slug="my-custom",
                config_path=config_path,
            )

        config = json.loads(config_path.read_text(encoding="utf-8"))
        # Display name should be the slug when --slug is given
        assert "my-custom" in config["mcpServers"]

    def test_tool_with_toolkit_combo(self, tmp_path: Path) -> None:
        """--toolkit github --tool Slack.SendMessage merges both."""
        config_path = tmp_path / "claude.json"

        with (
            patch("arcade_cli.connect.ensure_login", return_value="tok_abc"),
            patch(
                "arcade_cli.connect.fetch_available_toolkits",
                return_value={"github": ["Github.CreateIssue"]},
            ),
            _mock_list_gw(),
            patch(
                "arcade_cli.connect.create_gateway",
                return_value={"slug": "combo", "id": "gw-2"},
            ) as mock_create,
            patch("arcade_cli.connect.console"),
            patch("arcade_cli.configure.console"),
        ):
            run_connect(
                client="claude",
                toolkits=["github"],
                tools=["Slack.SendMessage"],
                config_path=config_path,
            )

        call_kwargs = mock_create.call_args[1]
        assert "Github.CreateIssue" in call_kwargs["tool_allow_list"]
        assert "Slack.SendMessage" in call_kwargs["tool_allow_list"]
