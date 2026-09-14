import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from arcade_cli.deploy import (
    deploy_server_logic,
    deploy_server_to_engine,
    preflight_secret_ownership,
    update_deployment,
    upsert_secrets_to_engine,
)

ARCADE_SERVER = """
from arcade_mcp_server import MCPApp

app = MCPApp(name="expense", version="1.0.0")
"""


def _http_error_client(status_code: int):
    request = httpx.Request("PUT", "https://engine.acme.internal/x")
    response = httpx.Response(status_code, request=request)

    def _raise(*args, **kwargs):
        raise httpx.HTTPStatusError("err", request=request, response=response)

    client = MagicMock()
    client.put.return_value = response
    client.post.return_value = response
    client.get.return_value = response
    response.raise_for_status = _raise  # type: ignore[method-assign]
    client.close.return_value = None
    return client


class TestPreflightSecretOwnership:
    def test_foreign_key_raises_naming_it(self):
        with patch(
            "arcade_cli.deploy._fetch_secret_owners",
            return_value={"EXPENSE_API_TOKEN": "other-acct"},
        ):
            with pytest.raises(ValueError, match="EXPENSE_API_TOKEN"):
                preflight_secret_ownership("url", {"EXPENSE_API_TOKEN"}, "me")

    def test_own_key_passes(self):
        with patch(
            "arcade_cli.deploy._fetch_secret_owners",
            return_value={"EXPENSE_API_TOKEN": "me"},
        ):
            preflight_secret_ownership("url", {"EXPENSE_API_TOKEN"}, "me")

    def test_new_key_passes(self):
        with patch("arcade_cli.deploy._fetch_secret_owners", return_value={}):
            preflight_secret_ownership("url", {"EXPENSE_REGION"}, "me")

    def test_unowned_existing_key_passes(self):
        with patch(
            "arcade_cli.deploy._fetch_secret_owners",
            return_value={"EXPENSE_API_TOKEN": None},
        ):
            preflight_secret_ownership("url", {"EXPENSE_API_TOKEN"}, "me")

    def test_no_account_id_skips_preflight(self):
        with patch("arcade_cli.deploy._fetch_secret_owners") as mock_fetch:
            preflight_secret_ownership("url", {"EXPENSE_API_TOKEN"}, None)

        mock_fetch.assert_not_called()

    def test_empty_declared_skips_preflight(self):
        with patch("arcade_cli.deploy._fetch_secret_owners") as mock_fetch:
            preflight_secret_ownership("url", set(), "me")

        mock_fetch.assert_not_called()


class TestFetchSecretOwners:
    def test_maps_keys_to_owner_account_ids(self):
        from arcade_cli.deploy import _fetch_secret_owners

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "items": [
                {"key": "OWNED", "owner_account_id": "me"},
                {"key": "FOREIGN", "owner_account_id": "other"},
                {"key": "UNOWNED", "owner_account_id": None},
                {"owner_account_id": "skip-me-no-key"},
            ]
        }
        client = MagicMock()
        client.get.return_value = response
        client.close.return_value = None

        with (
            patch("arcade_cli.deploy.httpx.Client", return_value=client),
            patch("arcade_cli.deploy.get_auth_headers", return_value={}),
            patch("arcade_cli.deploy.get_org_scoped_url", return_value="https://engine/secrets"),
        ):
            owners = _fetch_secret_owners("https://engine.acme.internal")

        assert owners == {"OWNED": "me", "FOREIGN": "other", "UNOWNED": None}


class TestForbiddenMapping:
    def test_update_deployment_403_is_forbidden(self):
        with (
            patch("arcade_cli.deploy.httpx.Client", return_value=_http_error_client(403)),
            patch("arcade_cli.deploy.get_auth_headers", return_value={}),
            patch("arcade_cli.deploy.get_org_scoped_url", return_value="https://engine/x"),
        ):
            with pytest.raises(ValueError, match="forbidden"):
                update_deployment("https://engine.acme.internal", "Email Tools", {})

    def test_deploy_server_to_engine_403_is_forbidden(self):
        with (
            patch("arcade_cli.deploy.httpx.Client", return_value=_http_error_client(403)),
            patch("arcade_cli.deploy.get_auth_headers", return_value={}),
            patch("arcade_cli.deploy.get_org_scoped_url", return_value="https://engine/x"),
        ):
            with pytest.raises(ValueError, match="forbidden"):
                deploy_server_to_engine("https://engine.acme.internal", {})

    def test_upsert_secret_403_is_forbidden(self):
        os.environ["EXPENSE_API_TOKEN"] = "value"
        with (
            patch("arcade_cli.deploy.httpx.Client", return_value=_http_error_client(403)),
            patch("arcade_cli.deploy.get_auth_headers", return_value={}),
            patch("arcade_cli.deploy.get_org_scoped_url", return_value="https://engine/x"),
        ):
            with pytest.raises(ValueError, match="forbidden"):
                upsert_secrets_to_engine("https://engine.acme.internal", {"EXPENSE_API_TOKEN"})


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    os.environ["ARCADE_WORK_DIR"] = str(tmp_path / "home")
    (tmp_path / "home").mkdir()
    return tmp_path


@pytest.fixture
def project_dir(work_dir: Path) -> Path:
    proj = work_dir / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("[project]\nname = 'expense'\nversion = '1.0.0'\n")
    (proj / "server.py").write_text(ARCADE_SERVER)
    return proj


class TestDeployRejectsBeforeUpload:
    def test_unsupported_input_rejected_before_upload(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        os.environ["ARCADE_URL"] = "https://engine.acme.internal"
        os.environ["ARCADE_API_KEY"] = "ci-key"
        (project_dir / "server.py").write_text(
            "from mcp.server.fastmcp import FastMCP\napp = FastMCP('x')\n"
        )
        monkeypatch.chdir(project_dir)

        with (
            patch("arcade_cli.deploy.httpx.Client") as mock_client,
            patch("arcade_cli.deploy.deploy_server_to_engine") as mock_deploy,
        ):
            with pytest.raises(ValueError, match="FastMCP"):
                deploy_server_logic(
                    entrypoint="server.py",
                    skip_validate=True,
                    server_name="expense",
                    server_version="1.0.0",
                    secrets="skip",
                    host=None,
                    port=None,
                    force_tls=False,
                    force_no_tls=False,
                    debug=False,
                )

        mock_client.assert_not_called()
        mock_deploy.assert_not_called()

    def test_foreign_secret_rejected_before_upload(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        os.environ.pop("ARCADE_URL", None)
        os.environ.pop("ARCADE_API_KEY", None)

        from arcade_core.config_model import Config, NamedContext

        seed = Config()
        seed.contexts = {
            "onprem": NamedContext(kind="self_hosted", engine_url="https://engine.acme.internal")
        }
        seed._apply_named_context("onprem", seed.contexts["onprem"])
        seed.save_to_file()

        (project_dir / ".env").write_text("EXPENSE_API_TOKEN=local-value\n")
        monkeypatch.chdir(project_dir)

        config = MagicMock()
        config.user.email = "user@acme.internal"
        config.user.account_id = "me"

        with (
            patch("arcade_cli.deploy.validate_and_get_config", return_value=config),
            patch(
                "arcade_cli.deploy._fetch_secret_owners",
                return_value={"EXPENSE_API_TOKEN": "other-acct"},
            ),
            patch("arcade_cli.deploy.upsert_secrets_to_engine") as mock_upsert,
            patch("arcade_cli.deploy.deploy_server_to_engine") as mock_deploy,
        ):
            with pytest.raises(ValueError, match="EXPENSE_API_TOKEN"):
                deploy_server_logic(
                    entrypoint="server.py",
                    skip_validate=True,
                    server_name="expense",
                    server_version="1.0.0",
                    secrets="all",
                    host=None,
                    port=None,
                    force_tls=False,
                    force_no_tls=False,
                    debug=False,
                )

        mock_upsert.assert_not_called()
        mock_deploy.assert_not_called()

    def test_own_and_new_secret_keys_are_set(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        os.environ.pop("ARCADE_URL", None)
        os.environ.pop("ARCADE_API_KEY", None)

        from arcade_core.config_model import Config, NamedContext

        seed = Config()
        seed.contexts = {
            "onprem": NamedContext(kind="self_hosted", engine_url="https://engine.acme.internal")
        }
        seed._apply_named_context("onprem", seed.contexts["onprem"])
        seed.save_to_file()

        (project_dir / ".env").write_text(
            "EXPENSE_API_TOKEN=token-value\nEXPENSE_REGION=us-east-1\n"
        )
        monkeypatch.chdir(project_dir)

        config = MagicMock()
        config.user.email = "user@acme.internal"
        config.user.account_id = "me"

        with (
            patch("arcade_cli.deploy.validate_and_get_config", return_value=config),
            patch(
                "arcade_cli.deploy._fetch_secret_owners",
                return_value={"EXPENSE_API_TOKEN": "me"},
            ),
            patch("arcade_cli.deploy.upsert_secrets_to_engine") as mock_upsert,
            patch("arcade_cli.deploy.server_already_exists", return_value=False),
            patch("arcade_cli.deploy.deploy_server_to_engine") as mock_deploy,
            patch(
                "arcade_cli.deploy._monitor_deployment_with_logs",
                new=AsyncMock(return_value=("running", [])),
            ),
        ):
            deploy_server_logic(
                entrypoint="server.py",
                skip_validate=True,
                server_name="expense",
                server_version="1.0.0",
                secrets="all",
                host=None,
                port=None,
                force_tls=False,
                force_no_tls=False,
                debug=False,
            )

        mock_upsert.assert_called_once()
        assert mock_upsert.call_args.args[1] == {"EXPENSE_API_TOKEN", "EXPENSE_REGION"}
        mock_deploy.assert_called_once()
