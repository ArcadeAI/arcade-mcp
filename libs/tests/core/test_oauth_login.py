"""Tests for ``arcade_core.oauth_login``."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import socket
import sys
import threading
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

import httpx
import pytest
from arcade_core.auth_tokens import CLIConfig, TokenResponse
from arcade_core.oauth_login import (
    DEFAULT_SCOPES,
    NoOrgsError,
    NoProjectsError,
    OAuthCallbackServer,
    OAuthLoginError,
    OrgInfo,
    ProjectInfo,
    WhoAmIResponse,
    exchange_code_for_tokens,
    fetch_whoami,
    generate_authorization_url,
    save_credentials_from_whoami,
    validate_whoami_org_project,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cli_config() -> CLIConfig:
    return CLIConfig(
        client_id="test-client",
        authorization_endpoint="https://auth.example.com/authorize",
        token_endpoint="https://auth.example.com/token",
    )


def _whoami_full() -> WhoAmIResponse:
    return WhoAmIResponse(
        account_id="acc-1",
        email="user@example.com",
        organizations=[OrgInfo(org_id="org-1", name="Acme", is_default=True)],
        projects=[ProjectInfo(project_id="proj-1", name="Main", is_default=True)],
    )


# ---------------------------------------------------------------------------
# 1. PKCE / authorization URL
# ---------------------------------------------------------------------------


def test_generate_authorization_url_uses_pkce_s256_and_returns_state_and_verifier() -> None:
    cli_config = _cli_config()
    state = "abc123-state"
    redirect_uri = "http://127.0.0.1:9999/callback"

    url, code_verifier = generate_authorization_url(cli_config, redirect_uri, state)

    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == cli_config.authorization_endpoint
    qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}

    assert qs["code_challenge_method"] == "S256"
    assert qs["state"] == state
    assert qs["client_id"] == cli_config.client_id
    assert qs["redirect_uri"] == redirect_uri
    assert qs["scope"] == DEFAULT_SCOPES
    assert qs["response_type"] == "code"

    expected_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    assert qs["code_challenge"] == expected_challenge
    assert "=" not in qs["code_challenge"]
    assert len(code_verifier) >= 43  # PKCE minimum


# ---------------------------------------------------------------------------
# 2-8. Callback listener tests
# ---------------------------------------------------------------------------


def test_callback_server_captures_code_and_state() -> None:
    state = "match-state"
    server = OAuthCallbackServer(expected_state=state, port=0)
    server.start()
    try:
        url = f"{server.get_redirect_uri()}?code=abc123&state={state}"
        with urlopen(url) as response:
            assert response.status == 200
            response.read()
        assert server.wait_for_result(timeout=2.0) is True
    finally:
        asyncio.run(server.shutdown())

    assert server.result.get("code") == "abc123"
    assert server.result.get("state") == state
    assert "error" not in server.result


def test_callback_server_state_mismatch_returns_400_and_records_csrf_error_listener_does_not_advance() -> None:
    state = "expected-state"
    server = OAuthCallbackServer(expected_state=state, port=0)
    server.start()
    try:
        url = f"{server.get_redirect_uri()}?code=abc&state=wrong-state"
        try:
            with urlopen(url) as response:
                response.read()
        except HTTPError as e:
            assert e.code == 400
        # CSRF is fatal — result_event fires.
        assert server.wait_for_result(timeout=2.0) is True
    finally:
        asyncio.run(server.shutdown())

    assert "CSRF" in server.result.get("error", "")


def test_callback_server_unknown_path_returns_404_listener_keeps_running(
    capfd: pytest.CaptureFixture[str]
) -> None:
    state = "keep-running-state"
    server = OAuthCallbackServer(expected_state=state, port=0)
    server.start()
    try:
        favicon_url = f"http://127.0.0.1:{server.port}/favicon.ico"
        try:
            with urlopen(favicon_url) as response:
                response.read()
        except HTTPError as e:
            assert e.code == 404

        # Listener should NOT have advanced.
        assert not server.result_event.is_set()
        assert server.result == {}

        # Now hit the proper callback path.
        url = f"{server.get_redirect_uri()}?code=zzz&state={state}"
        with urlopen(url) as response:
            assert response.status == 200
            response.read()
        assert server.wait_for_result(timeout=2.0) is True
        assert server.result.get("code") == "zzz"
    finally:
        asyncio.run(server.shutdown())

    fd_out, fd_err = capfd.readouterr()
    assert fd_out == ""
    assert fd_err == ""


def test_callback_server_times_out_cleanly_no_output(
    capfd: pytest.CaptureFixture[str]
) -> None:
    server = OAuthCallbackServer(expected_state="timeout-state", port=0)
    server.start()
    try:
        assert server.wait_for_result(timeout=0.05) is False
        assert "Timed out" in server.result.get("error", "")
    finally:
        asyncio.run(server.shutdown())


    fd_out, fd_err = capfd.readouterr()

    assert fd_out == "" and fd_err == ""


def test_callback_server_port_in_use_fails_cleanly_no_output(
    capfd: pytest.CaptureFixture[str]
) -> None:
    # Pre-bind an ephemeral port.
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    try:
        _, port = blocker.getsockname()
        server = OAuthCallbackServer(expected_state="port-in-use", port=port)
        with pytest.raises(OSError):
            server.start()
    finally:
        blocker.close()


    fd_out, fd_err = capfd.readouterr()

    assert fd_out == "" and fd_err == ""


def test_callback_server_handle_error_logs_via_stdlib_no_print_no_stderr(
    capfd: pytest.CaptureFixture[str]
) -> None:
    server = OAuthCallbackServer(expected_state="handle-error", port=0)
    server.start()
    try:
        # Send malformed bytes that should trigger handle_error inside the
        # server thread.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", server.port))
        s.sendall(b"\x00\x01\x02NOT-A-VALID-HTTP-REQUEST\r\n\r\n")
        try:
            s.recv(1024)
        except Exception:
            pass
        s.close()
    finally:
        asyncio.run(server.shutdown())


    fd_out, fd_err = capfd.readouterr()

    assert fd_out == "" and fd_err == ""


def test_callback_server_broken_pipe_suppressed_no_output(
    capfd: pytest.CaptureFixture[str]
) -> None:
    state = "broken-pipe"
    server = OAuthCallbackServer(expected_state=state, port=0)
    server.start()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", server.port))
        # Send a request line then immediately close the socket; the server's
        # response write should hit a broken pipe / connection reset.
        s.sendall(
            f"GET /callback?code=abc&state={state} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{server.port}\r\n"
            f"Connection: close\r\n\r\n".encode("ascii")
        )
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        # Give the server a moment to try writing.
        server._result_event.wait(timeout=2.0)
    finally:
        asyncio.run(server.shutdown())


    fd_out, fd_err = capfd.readouterr()

    assert fd_out == "" and fd_err == ""


# ---------------------------------------------------------------------------
# 9. save_credentials_from_whoami
# ---------------------------------------------------------------------------


def test_save_credentials_writes_file_chmod_600_and_invalidates_cache(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))

    from datetime import datetime, timedelta

    from arcade_core.config_model import AuthConfig, Config

    # Seed credentials BEFORE importing arcade_core.config (which calls
    # get_config() at module-import time and would otherwise blow up if no
    # credentials file exists yet).
    seed = Config(
        coordinator_url="https://seed.example.com",
        auth=AuthConfig(
            access_token="seed-access",
            refresh_token="seed-refresh",
            expires_at=datetime.now() + timedelta(hours=1),
        ),
    )
    seed.save_to_file()

    from arcade_core.config import get_config

    # The arcade_core.config module may already be imported and cached from
    # earlier tests with a different (real) credentials file. Reset it so we
    # read fresh from the temp work-dir.
    get_config.cache_clear()
    seeded = get_config()
    assert seeded.coordinator_url == "https://seed.example.com"
    assert get_config.cache_info().currsize == 1

    tokens = TokenResponse(
        access_token="new-access",
        refresh_token="new-refresh",
        expires_in=3600,
        token_type="Bearer",
    )
    whoami = _whoami_full()

    asyncio.run(
        save_credentials_from_whoami(tokens, whoami, "https://api.example.com")
    )

    # Cache invalidated.
    assert get_config.cache_info().currsize == 0

    # File written with the new contents.
    cred_path = Config.get_config_file_path()
    assert cred_path.exists()
    if sys.platform != "win32":
        mode = os.stat(cred_path).st_mode & 0o777
        assert mode == 0o600

    fresh = get_config()
    assert fresh.coordinator_url == "https://api.example.com"
    assert fresh.auth is not None
    assert fresh.auth.access_token == "new-access"
    assert fresh.user is not None
    assert fresh.user.email == "user@example.com"
    assert fresh.context is not None
    assert fresh.context.org_id == "org-1"
    assert fresh.context.project_id == "proj-1"


# ---------------------------------------------------------------------------
# 10. fetch_cli_config — covered in test_auth_bootstrap.py
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 11. exchange_code_for_tokens failure
# ---------------------------------------------------------------------------


_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _patch_async_client(
    monkeypatch: pytest.MonkeyPatch, handler: Any
) -> None:
    transport = httpx.MockTransport(handler)

    def factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs.pop("transport", None)
        return _REAL_ASYNC_CLIENT(transport=transport, **kwargs)

    monkeypatch.setattr("arcade_core.oauth_login.httpx.AsyncClient", factory)


def test_exchange_code_for_tokens_failure_propagates_typed_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli_config = _cli_config()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    _patch_async_client(monkeypatch, handler)

    with pytest.raises(OAuthLoginError) as excinfo:
        asyncio.run(
            exchange_code_for_tokens(
                cli_config,
                code="bad-code",
                redirect_uri="http://127.0.0.1:1/callback",
                code_verifier="v" * 64,
            )
        )

    assert "400" in str(excinfo.value)


def test_exchange_code_for_tokens_success(monkeypatch: pytest.MonkeyPatch) -> None:
    cli_config = _cli_config()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "access_token": "ok-access",
                "refresh_token": "ok-refresh",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )

    _patch_async_client(monkeypatch, handler)
    tokens = asyncio.run(
        exchange_code_for_tokens(
            cli_config,
            code="good-code",
            redirect_uri="http://127.0.0.1:1/callback",
            code_verifier="v" * 64,
        )
    )

    assert tokens.access_token == "ok-access"
    assert tokens.refresh_token == "ok-refresh"


# ---------------------------------------------------------------------------
# 12. fetch_whoami failure
# ---------------------------------------------------------------------------


def test_fetch_whoami_failure_propagates_typed_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    _patch_async_client(monkeypatch, handler)
    with pytest.raises(OAuthLoginError) as excinfo:
        asyncio.run(fetch_whoami("https://api.example.com", "tok"))

    assert "401" in str(excinfo.value)


def test_fetch_whoami_success_unwraps_data_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer tok"
        return httpx.Response(
            200,
            json={
                "data": {
                    "account_id": "acc-x",
                    "email": "x@example.com",
                    "organizations": [
                        {"organization_id": "org-x", "name": "OrgX", "is_default": True}
                    ],
                    "projects": [
                        {"project_id": "proj-x", "name": "ProjX", "is_default": True}
                    ],
                }
            },
        )

    _patch_async_client(monkeypatch, handler)
    whoami = asyncio.run(fetch_whoami("https://api.example.com", "tok"))

    assert whoami.account_id == "acc-x"
    # AliasChoices: "organization_id" should map to org_id.
    assert whoami.organizations[0].org_id == "org-x"


# ---------------------------------------------------------------------------
# 13/14. validate_whoami_org_project
# ---------------------------------------------------------------------------


def test_validate_whoami_org_project_no_orgs_raises() -> None:
    whoami = WhoAmIResponse(account_id="a", email="e@example.com", organizations=[], projects=[])
    with pytest.raises(NoOrgsError):
        validate_whoami_org_project(whoami)


def test_validate_whoami_org_project_no_projects_raises() -> None:
    whoami = WhoAmIResponse(
        account_id="a",
        email="e@example.com",
        organizations=[OrgInfo(org_id="o", name="O", is_default=True)],
        projects=[],
    )
    with pytest.raises(NoProjectsError):
        validate_whoami_org_project(whoami)


def test_validate_whoami_org_project_happy_path() -> None:
    validate_whoami_org_project(_whoami_full())


# ---------------------------------------------------------------------------
# 15. Full happy-path silence test
# ---------------------------------------------------------------------------


def test_module_emits_no_stdout_or_stderr_under_full_flow(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("ARCADE_WORK_DIR", str(tmp_path))

    cli_config = _cli_config()
    state = "happy-state"

    # Real listener on ephemeral port.
    server = OAuthCallbackServer(expected_state=state, port=0)
    server.start()

    redirect_uri = server.get_redirect_uri()
    auth_url, code_verifier = generate_authorization_url(cli_config, redirect_uri, state)
    assert "code_challenge=" in auth_url

    def token_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "access_token": "ha-access",
                "refresh_token": "ha-refresh",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )

    def whoami_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": {
                    "account_id": "acc-h",
                    "email": "h@example.com",
                    "organizations": [
                        {"org_id": "org-h", "name": "OrgH", "is_default": True}
                    ],
                    "projects": [
                        {"project_id": "proj-h", "name": "ProjH", "is_default": True}
                    ],
                }
            },
        )

    # Drive the listener with a real HTTP request to /callback.
    def trigger_callback() -> None:
        url = f"{redirect_uri}?code=happy-code&state={state}"
        try:
            with urlopen(url) as resp:
                resp.read()
        except Exception:
            pass

    threading.Timer(0.05, trigger_callback).start()
    assert server.wait_for_result(timeout=3.0) is True
    code = server.result["code"]

    async def run_flow() -> None:
        _patch_async_client(monkeypatch, token_handler)
        tokens = await exchange_code_for_tokens(
            cli_config, code=code, redirect_uri=redirect_uri, code_verifier=code_verifier
        )
        _patch_async_client(monkeypatch, whoami_handler)
        whoami = await fetch_whoami("https://api.example.com", tokens.access_token)

        validate_whoami_org_project(whoami)
        await save_credentials_from_whoami(tokens, whoami, "https://api.example.com")
        await server.shutdown()

    asyncio.run(run_flow())


    fd_out, fd_err = capfd.readouterr()

    assert fd_out == "" and fd_err == ""
