"""Integration tests verifying that get_ssl_verify() is threaded through httpx calls."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest


SENTINEL_CA_PATH = "/custom/ca-bundle.pem"


class TestAuthnSslVerify:
    """Verify authn.py httpx calls pass verify=get_ssl_verify()."""

    @patch("arcade_cli.authn.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.authn.httpx.get")
    def test_fetch_whoami_passes_verify(
        self, mock_get: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from arcade_cli.authn import fetch_whoami

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": {"account_id": "a", "email": "e", "orgs": []}},
        )
        fetch_whoami("https://example.com", "token")
        mock_get.assert_called_once()
        assert mock_get.call_args.kwargs["verify"] == SENTINEL_CA_PATH

    @patch("arcade_cli.authn.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.authn.get_valid_access_token", return_value="token")
    @patch("arcade_cli.authn.httpx.get")
    def test_fetch_organizations_passes_verify(
        self, mock_get: MagicMock, mock_token: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from arcade_cli.authn import fetch_organizations

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": {"items": []}},
        )
        fetch_organizations("https://example.com")
        mock_get.assert_called_once()
        assert mock_get.call_args.kwargs["verify"] == SENTINEL_CA_PATH

    @patch("arcade_cli.authn.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.authn.get_valid_access_token", return_value="token")
    @patch("arcade_cli.authn.httpx.get")
    def test_fetch_projects_passes_verify(
        self, mock_get: MagicMock, mock_token: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from arcade_cli.authn import fetch_projects

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": {"items": []}},
        )
        fetch_projects("https://example.com", "org-123")
        mock_get.assert_called_once()
        assert mock_get.call_args.kwargs["verify"] == SENTINEL_CA_PATH


class TestSecretSslVerify:
    """Verify secret.py httpx calls pass verify=get_ssl_verify()."""

    @patch("arcade_cli.secret.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.secret.get_auth_headers", return_value={"Authorization": "Bearer t"})
    @patch("arcade_cli.secret.get_org_scoped_url", return_value="https://example.com/secrets/KEY")
    @patch("arcade_cli.secret.state", {"engine_url": "https://example.com"})
    @patch("arcade_cli.secret.httpx.put")
    def test_upsert_secret_passes_verify(
        self, mock_put: MagicMock, mock_url: MagicMock, mock_auth: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from arcade_cli.secret import _upsert_secret

        mock_put.return_value = MagicMock(status_code=200)
        _upsert_secret("KEY", "value")
        mock_put.assert_called_once()
        assert mock_put.call_args.kwargs["verify"] == SENTINEL_CA_PATH

    @patch("arcade_cli.secret.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.secret.get_auth_headers", return_value={"Authorization": "Bearer t"})
    @patch("arcade_cli.secret.get_org_scoped_url", return_value="https://example.com/secrets")
    @patch("arcade_cli.secret.state", {"engine_url": "https://example.com"})
    @patch("arcade_cli.secret.httpx.get")
    def test_get_secrets_passes_verify(
        self, mock_get: MagicMock, mock_url: MagicMock, mock_auth: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from arcade_cli.secret import _get_secrets

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"items": []},
        )
        _get_secrets()
        mock_get.assert_called_once()
        assert mock_get.call_args.kwargs["verify"] == SENTINEL_CA_PATH

    @patch("arcade_cli.secret.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.secret.get_auth_headers", return_value={"Authorization": "Bearer t"})
    @patch("arcade_cli.secret.get_org_scoped_url", return_value="https://example.com/secrets/id")
    @patch("arcade_cli.secret.state", {"engine_url": "https://example.com"})
    @patch("arcade_cli.secret.httpx.delete")
    def test_delete_secret_passes_verify(
        self, mock_delete: MagicMock, mock_url: MagicMock, mock_auth: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from arcade_cli.secret import _delete_secret

        mock_delete.return_value = MagicMock(status_code=200)
        _delete_secret("secret-id")
        mock_delete.assert_called_once()
        assert mock_delete.call_args.kwargs["verify"] == SENTINEL_CA_PATH


class TestDeploySslVerify:
    """Verify deploy.py httpx Client calls pass verify=get_ssl_verify()."""

    @patch("arcade_cli.deploy.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.deploy.get_auth_headers", return_value={"Authorization": "Bearer t"})
    @patch("arcade_cli.deploy.get_org_scoped_url", return_value="https://example.com/status")
    @patch("arcade_cli.deploy.httpx.Client")
    def test_get_deployment_status_passes_verify(
        self, mock_client_cls: MagicMock, mock_url: MagicMock, mock_auth: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from arcade_cli.deploy import _get_deployment_status

        mock_client = MagicMock()
        mock_client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "running"},
        )
        mock_client_cls.return_value = mock_client

        _get_deployment_status("https://example.com", "my-server")
        mock_client_cls.assert_called_once()
        assert mock_client_cls.call_args.kwargs["verify"] == SENTINEL_CA_PATH

    @patch("arcade_cli.deploy.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.deploy.get_auth_headers", return_value={"Authorization": "Bearer t"})
    @patch("arcade_cli.deploy.get_org_scoped_url", return_value="https://example.com/workers/s")
    @patch("arcade_cli.deploy.httpx.Client")
    def test_server_already_exists_passes_verify(
        self, mock_client_cls: MagicMock, mock_url: MagicMock, mock_auth: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from arcade_cli.deploy import server_already_exists

        mock_client = MagicMock()
        mock_client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"managed": True},
        )
        mock_client_cls.return_value = mock_client

        server_already_exists("https://example.com", "my-server")
        mock_client_cls.assert_called_once()
        assert mock_client_cls.call_args.kwargs["verify"] == SENTINEL_CA_PATH

    @patch("arcade_cli.deploy.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.deploy.httpx.get")
    def test_wait_for_health_passes_verify(
        self, mock_get: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from arcade_cli.deploy import wait_for_health

        mock_get.return_value = MagicMock(status_code=200)
        mock_process = MagicMock()
        mock_process.poll.return_value = None

        wait_for_health("http://localhost:8000", mock_process, timeout=1)
        mock_get.assert_called()
        assert mock_get.call_args.kwargs["verify"] == SENTINEL_CA_PATH

    @patch("arcade_cli.deploy.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.deploy.httpx.post")
    def test_get_server_info_passes_verify(
        self, mock_post: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from arcade_cli.deploy import get_server_info

        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "result": {
                    "serverInfo": {"name": "test-server", "version": "1.0.0"}
                }
            },
        )

        get_server_info("http://localhost:8000")
        mock_post.assert_called_once()
        assert mock_post.call_args.kwargs["verify"] == SENTINEL_CA_PATH

    @patch("arcade_cli.deploy.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.deploy.httpx.get")
    def test_get_required_secrets_passes_verify(
        self, mock_get: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from arcade_cli.deploy import get_required_secrets

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [],
        )

        get_required_secrets("http://localhost:8000", "server", "1.0.0")
        mock_get.assert_called_once()
        assert mock_get.call_args.kwargs["verify"] == SENTINEL_CA_PATH


class TestServerSslVerify:
    """Verify server.py httpx Client calls pass verify=get_ssl_verify()."""

    @patch("arcade_cli.server.get_ssl_verify", return_value=SENTINEL_CA_PATH)
    @patch("arcade_cli.server.httpx.Client")
    def test_display_deployment_logs_passes_verify(
        self, mock_client_cls: MagicMock, mock_ssl: MagicMock
    ) -> None:
        from datetime import datetime, timezone

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: [],
        )
        mock_client_cls.return_value = mock_client

        from arcade_cli.server import _display_deployment_logs

        now = datetime.now(tz=timezone.utc)
        _display_deployment_logs(
            "https://example.com/logs", {}, now, now, debug=False
        )
        mock_client_cls.assert_called_once()
        assert mock_client_cls.call_args.kwargs["verify"] == SENTINEL_CA_PATH
