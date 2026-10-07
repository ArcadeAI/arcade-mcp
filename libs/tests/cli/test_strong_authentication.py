import asyncio
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import httpx2
import pytest
from arcade_cli.authn import (
    OAuthLoginError,
    WhoAmIResponse,
    exchange_code_for_tokens,
    forget_sign_in,
    perform_oauth_login,
)
from arcade_cli.connect import list_gateways
from arcade_cli.deploy import upsert_secrets_to_engine
from arcade_cli.secret import list_secrets, set_secret, unset_secret
from arcade_cli.server import _display_deployment_logs, _stream_deployment_logs
from arcade_cli.strong_authentication import (
    STRONG_AUTHENTICATION_REQUIRED,
    InsufficientUserAuthentication,
    from_error,
    from_response,
)
from arcade_cli.utils import (
    CLIError,
    exit_if_strong_authentication_required,
    handle_cli_error,
)
from arcade_core.auth_tokens import CLIConfig, TokenResponse
from arcade_core.config_model import AuthConfig, Config, UserConfig
from arcadepy import AuthenticationError
from authlib.integrations.httpx_client import OAuth2Client
from rich.console import Console

DESCRIPTION = (
    "Your organization requires a passkey or an authenticator app to sign in. "
    "Set one up in your Arcade account settings, then sign in again."
)
CHALLENGE = (
    f'Bearer error="insufficient_user_authentication", error_description="{DESCRIPTION}"'
)
REQUEST = httpx.Request("GET", "https://api.arcade.dev/v1/orgs/o/projects/p/workers")


def _refusal(challenge: str = CHALLENGE, status: int = 401) -> httpx.Response:
    return httpx.Response(
        status,
        headers={"WWW-Authenticate": challenge},
        json={"name": "insufficient_user_authentication", "message": DESCRIPTION},
        request=REQUEST,
    )


@pytest.fixture
def signed_in(tmp_path: Path) -> Iterator[Path]:
    os.environ["ARCADE_WORK_DIR"] = str(tmp_path)
    Config(
        coordinator_url="https://cloud.arcade.dev",
        auth=AuthConfig(
            access_token="access",
            refresh_token="refresh",
            expires_at=datetime.now() + timedelta(hours=1),
        ),
        user=UserConfig(email="operator@example.com"),
    ).save_to_file()
    yield tmp_path


@pytest.fixture
def output() -> Iterator[StringIO]:
    buffer = StringIO()
    with patch("arcade_cli.utils.console", Console(file=buffer, width=400)):
        yield buffer


class TestDetectingTheRefusal:
    def test_reads_the_description_from_the_challenge(self) -> None:
        assert from_response(_refusal()) == InsufficientUserAuthentication(
            description=DESCRIPTION, uri=None
        )

    def test_reads_an_error_uri_and_unescapes_quoted_pairs(self) -> None:
        challenge = (
            'Bearer realm="arcade", error="insufficient_user_authentication", '
            'error_description="Use a \\"passkey\\"", error_uri="https://docs.arcade.dev/mfa"'
        )
        assert from_response(_refusal(challenge)) == InsufficientUserAuthentication(
            description='Use a "passkey"', uri="https://docs.arcade.dev/mfa"
        )

    @pytest.mark.parametrize(
        ("challenge", "status"),
        [
            ('Bearer error="invalid_token", error_description="Expired"', 401),
            (CHALLENGE, 403),
            (CHALLENGE.replace("Bearer", "Basic", 1), 401),
        ],
    )
    def test_ignores_other_refusals(self, challenge: str, status: int) -> None:
        assert from_response(_refusal(challenge, status)) is None

    def test_finds_the_refusal_behind_a_wrapping_error(self) -> None:
        response = _refusal()
        try:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise ValueError("Deployment failed") from e
        except ValueError as wrapped:
            assert from_error(wrapped) is not None

    def test_finds_the_refusal_in_an_sdk_error(self) -> None:
        error = AuthenticationError("Error code: 401", response=_refusal(), body=None)
        assert from_error(error) is not None


class TestReportingTheRefusal:
    def test_explains_it_and_logs_out(self, signed_in: Path, output: StringIO) -> None:
        with pytest.raises(CLIError):
            handle_cli_error(
                "Failed to list servers",
                AuthenticationError("Error code: 401", response=_refusal(), body=None),
                debug=False,
            )

        printed = output.getvalue()
        assert DESCRIPTION in printed
        assert "Failed to list servers" not in printed
        assert "arcade login" in printed
        config = Config.load_from_file()
        assert config.auth is None
        assert config.user is not None
        assert config.user.email == "operator@example.com"

    def test_shows_the_error_uri_when_arcade_sends_one(
        self, signed_in: Path, output: StringIO
    ) -> None:
        challenge = f'{CHALLENGE}, error_uri="https://docs.arcade.dev/mfa"'
        with pytest.raises(CLIError):
            handle_cli_error("Failed", httpx.HTTPStatusError("401", request=REQUEST, response=_refusal(challenge)))

        assert "https://docs.arcade.dev/mfa" in output.getvalue()

    def test_falls_back_to_its_own_explanation(self, signed_in: Path, output: StringIO) -> None:
        bare = 'Bearer error="insufficient_user_authentication"'
        with pytest.raises(CLIError):
            handle_cli_error("Failed", httpx.HTTPStatusError("401", request=REQUEST, response=_refusal(bare)))

        assert STRONG_AUTHENTICATION_REQUIRED in output.getvalue()

    def test_a_reported_refusal_is_not_reported_again(
        self, signed_in: Path, output: StringIO
    ) -> None:
        # Commands that catch every error hand the refusal back to
        # handle_cli_error, chained to the response it was found in.
        with pytest.raises(CLIError) as reported:
            try:
                _refusal().raise_for_status()
            except httpx.HTTPStatusError as e:
                exit_if_strong_authentication_required(e)
        output.truncate(0)
        output.seek(0)

        with pytest.raises(CLIError) as again:
            handle_cli_error("Failed to deploy server", reported.value, debug=False)

        assert again.value is reported.value
        assert output.getvalue() == ""

    def test_leaves_other_errors_alone(self, signed_in: Path, output: StringIO) -> None:
        other = httpx.Response(401, request=REQUEST)
        with pytest.raises(CLIError):
            handle_cli_error(
                "Failed", httpx.HTTPStatusError("401", request=REQUEST, response=other), debug=False
            )

        assert Config.load_from_file().auth is not None


class TestListingGateways:
    def test_a_refusal_is_reported_rather_than_read_as_no_gateways(
        self, signed_in: Path, output: StringIO
    ) -> None:
        with (
            patch("arcade_cli.utils.get_org_project_context", return_value=("o", "p")),
            patch("arcade_cli.connect.httpx.get", return_value=_refusal()),
            pytest.raises(CLIError),
        ):
            list_gateways("access", base_url="https://api.arcade.dev")

        assert DESCRIPTION in output.getvalue()
        assert Config.load_from_file().auth is None

    def test_any_other_401_is_reported_too(self, signed_in: Path, output: StringIO) -> None:
        with (
            patch("arcade_cli.utils.get_org_project_context", return_value=("o", "p")),
            patch(
                "arcade_cli.connect.httpx.get",
                return_value=httpx.Response(401, request=REQUEST),
            ),
            pytest.raises(CLIError),
        ):
            list_gateways("access", base_url="https://api.arcade.dev")


TOKEN_ENDPOINT = "https://cloud.arcade.dev/api/v1/auth/cli_token"


def _oauth_client(body: dict, status: int = 400) -> OAuth2Client:
    return OAuth2Client(
        client_id="arcade-cli",
        token_endpoint=TOKEN_ENDPOINT,
        code_challenge_method="S256",
        transport=httpx2.MockTransport(lambda request: httpx2.Response(status, json=body)),
    )


class TestLoggingIn:
    def test_a_refused_code_exchange_shows_the_reason(self) -> None:
        client = _oauth_client({"error": "invalid_grant", "error_description": DESCRIPTION})

        with pytest.raises(OAuthLoginError) as refused:
            exchange_code_for_tokens(client, "code", "http://127.0.0.1:9905/callback", "verifier")

        assert str(refused.value) == DESCRIPTION

    def test_a_refused_code_exchange_shows_its_error_uri(self) -> None:
        client = _oauth_client({
            "error": "invalid_grant",
            "error_description": DESCRIPTION,
            "error_uri": "https://docs.arcade.dev/mfa",
        })

        with pytest.raises(OAuthLoginError) as refused:
            exchange_code_for_tokens(client, "code", "http://127.0.0.1:9905/callback", "verifier")

        assert "Learn more: https://docs.arcade.dev/mfa" in str(refused.value)

    def test_whoami_keeps_where_the_sign_in_stands(self) -> None:
        whoami = WhoAmIResponse.model_validate({
            "account_id": "a",
            "email": "operator@example.com",
            "mfa": {"status": "unmet"},
        })
        assert whoami.requires_strong_authentication
        assert not WhoAmIResponse(account_id="a", email="e").requires_strong_authentication

    def test_a_sign_in_whoami_reports_as_unmet_is_not_saved(self) -> None:
        server = MagicMock()
        server.result = {"code": "code"}
        server.get_redirect_uri.return_value = "http://127.0.0.1:9905/callback"

        @contextmanager
        def callback_server(state: str) -> Iterator[MagicMock]:
            yield server

        whoami = WhoAmIResponse.model_validate({
            "account_id": "a",
            "email": "operator@example.com",
            "organizations": [{"org_id": "o", "name": "Org"}],
            "projects": [{"project_id": "p", "name": "Proj"}],
            "mfa": {"status": "unmet"},
        })
        with (
            patch(
                "arcade_cli.authn.fetch_cli_config",
                return_value=CLIConfig(
                    client_id="arcade-cli",
                    authorization_endpoint="https://auth.arcade.dev/oauth2/auth",
                    token_endpoint=TOKEN_ENDPOINT,
                ),
            ),
            patch("arcade_cli.authn.oauth_callback_server", callback_server),
            patch("arcade_cli.authn._open_browser", return_value=True),
            patch(
                "arcade_cli.authn.exchange_code_for_tokens",
                return_value=TokenResponse(
                    access_token="a", refresh_token="r", expires_in=3600, token_type="bearer"
                ),
            ),
            patch("arcade_cli.authn.fetch_whoami", return_value=whoami),
            pytest.raises(OAuthLoginError) as refused,
        ):
            perform_oauth_login("https://cloud.arcade.dev")

        assert STRONG_AUTHENTICATION_REQUIRED in str(refused.value)


def _status_error() -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError("401", request=REQUEST, response=_refusal())


class _RefusingLogStream:
    async def __aenter__(self) -> "_RefusingLogStream":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def raise_for_status(self) -> None:
        _refusal().raise_for_status()

    def stream(self, *args: object, **kwargs: object) -> "_RefusingLogStream":
        return self


class TestEveryCommandReportsTheRefusal:
    def test_secret_set(self, signed_in: Path, output: StringIO) -> None:
        with (
            patch("arcade_cli.secret._upsert_secret", side_effect=_status_error()),
            pytest.raises(CLIError),
        ):
            set_secret(key_value_pairs=["KEY=value"], from_env=False, env_file=".env")

        assert DESCRIPTION in output.getvalue()
        assert Config.load_from_file().auth is None

    def test_secret_list(self, signed_in: Path, output: StringIO) -> None:
        with (
            patch("arcade_cli.secret.get_org_scoped_url", return_value=str(REQUEST.url)),
            patch("arcade_cli.secret.get_auth_headers", return_value={}),
            patch("arcade_cli.secret.httpx.get", return_value=_refusal()),
            pytest.raises(CLIError),
        ):
            list_secrets()

        assert DESCRIPTION in output.getvalue()
        assert Config.load_from_file().auth is None

    def test_secret_unset(self, signed_in: Path, output: StringIO) -> None:
        with (
            patch("arcade_cli.secret._get_secrets", return_value=[{"key": "KEY", "id": "1"}]),
            patch("arcade_cli.secret._delete_secret", side_effect=_status_error()),
            pytest.raises(CLIError),
        ):
            unset_secret(keys=["KEY"])

        assert DESCRIPTION in output.getvalue()
        assert Config.load_from_file().auth is None

    def test_server_logs(self, signed_in: Path, output: StringIO) -> None:
        with patch("arcade_cli.server.httpx.Client") as client, pytest.raises(CLIError):
            client.return_value.__enter__.return_value.get.return_value = _refusal()
            _display_deployment_logs(
                str(REQUEST.url), {}, datetime.now(), datetime.now(), debug=False
            )

        assert DESCRIPTION in output.getvalue()
        assert Config.load_from_file().auth is None

    def test_streamed_server_logs(self, signed_in: Path, output: StringIO) -> None:
        with (
            patch("arcade_cli.server.httpx.AsyncClient", return_value=_RefusingLogStream()),
            pytest.raises(CLIError),
        ):
            asyncio.run(
                _stream_deployment_logs(
                    str(REQUEST.url), {}, datetime.now(), datetime.now(), debug=False
                )
            )

        assert DESCRIPTION in output.getvalue()
        assert Config.load_from_file().auth is None

    def test_deploy_secret_upload(self, signed_in: Path, output: StringIO) -> None:
        os.environ["DEPLOY_SECRET"] = "value"
        with (
            patch("arcade_cli.deploy.get_auth_headers", return_value={}),
            patch("arcade_cli.deploy.get_org_scoped_url", return_value=str(REQUEST.url)),
            patch("arcade_cli.deploy.httpx.Client") as client,
            pytest.raises(CLIError),
        ):
            client.return_value.put.return_value = _refusal()
            upsert_secrets_to_engine("https://api.arcade.dev", {"DEPLOY_SECRET"})

        assert DESCRIPTION in output.getvalue()
        assert Config.load_from_file().auth is None


class TestForgettingTheSignIn:
    def test_without_a_credentials_file_does_nothing(self, tmp_path: Path) -> None:
        os.environ["ARCADE_WORK_DIR"] = str(tmp_path)
        forget_sign_in()
        assert list(tmp_path.iterdir()) == []

    def test_a_logged_out_context_is_left_alone(self, signed_in: Path) -> None:
        forget_sign_in()
        credentials = next(signed_in.glob("*.yaml"))
        written = credentials.stat().st_mtime_ns

        forget_sign_in()

        assert credentials.stat().st_mtime_ns == written


class TestLoggingInWithoutADescription:
    def test_a_refusal_without_a_description_shows_its_code(self) -> None:
        client = _oauth_client({"error": "invalid_grant"})

        with pytest.raises(OAuthLoginError) as refused:
            exchange_code_for_tokens(client, "code", "http://127.0.0.1:9905/callback", "verifier")

        assert str(refused.value) == "invalid_grant"
