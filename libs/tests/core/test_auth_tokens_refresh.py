import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from arcade_core.auth_tokens import CLIConfig, get_valid_access_token
from arcade_core.config_model import AuthConfig, Config

TOKEN_ENDPOINT = "https://auth.arcade.dev/oauth2/token"
CLI_CONFIG = CLIConfig(
    client_id="arcade-cli",
    authorization_endpoint="https://auth.arcade.dev/oauth2/auth",
    token_endpoint=TOKEN_ENDPOINT,
)


@pytest.fixture
def expired_sign_in(tmp_path: Path) -> Path:
    os.environ["ARCADE_WORK_DIR"] = str(tmp_path)
    Config(
        coordinator_url="https://cloud.arcade.dev",
        auth=AuthConfig(
            access_token="access",
            refresh_token="refresh",
            expires_at=datetime.now() - timedelta(minutes=1),
        ),
    ).save_to_file()
    return tmp_path


def _refused(status: int, body: dict | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", TOKEN_ENDPOINT)
    response = httpx.Response(status, json=body, request=request)
    return httpx.HTTPStatusError(str(status), request=request, response=response)


def _refused_with_text(status: int, text: str) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", TOKEN_ENDPOINT)
    response = httpx.Response(status, text=text, request=request)
    return httpx.HTTPStatusError(str(status), request=request, response=response)


def _refresh_failing_with(error: httpx.HTTPError):
    return (
        patch("arcade_core.auth_tokens.fetch_cli_config", return_value=CLI_CONFIG),
        patch("arcade_core.auth_tokens.refresh_access_token", side_effect=error),
    )


def test_a_refused_refresh_token_shows_why_and_is_forgotten(expired_sign_in: Path) -> None:
    config_patch, refresh_patch = _refresh_failing_with(
        _refused(400, {"error": "invalid_grant", "error_description": "The refresh token was revoked."})
    )
    with config_patch, refresh_patch, pytest.raises(ValueError) as failed:
        get_valid_access_token()

    assert "Failed to refresh token: The refresh token was revoked. Please run" in str(failed.value)
    assert Config.load_from_file().auth is None


@pytest.mark.parametrize(
    "error",
    [
        _refused(503, {"error": "server_error"}),
        _refused(400, {"error": "invalid_request"}),
        _refused_with_text(502, "<html>Bad gateway</html>"),
        _refused_with_text(400, '["not", "an", "object"]'),
        httpx.ConnectError("unreachable"),
    ],
)
def test_other_refresh_failures_keep_the_sign_in(
    expired_sign_in: Path, error: httpx.HTTPError
) -> None:
    config_patch, refresh_patch = _refresh_failing_with(error)
    with config_patch, refresh_patch, pytest.raises(ValueError):
        get_valid_access_token()

    assert Config.load_from_file().auth is not None
