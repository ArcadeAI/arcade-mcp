"""Tests for ``arcade_mcp_server.auth_bootstrap``.

These tests exercise the server-side OAuth bootstrap orchestrator. They use
``port=0`` for every listener (no fixed-port races) and drive the listener with
real HTTP requests where useful, while mocking out the downstream HTTP-only
primitives (``fetch_cli_config``, ``exchange_code_for_tokens``, ``fetch_whoami``,
``save_credentials_from_whoami``, ``validate_whoami_org_project``).
"""

from __future__ import annotations

import asyncio
import socket
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import urlopen

import httpx
import pytest
import pytest_asyncio
from arcade_core.auth_tokens import CLIConfig, TokenResponse
from arcade_core.oauth_login import (
    NoOrgsError,
    NoProjectsError,
    OAuthCallbackServer,
    OrgInfo,
    ProjectInfo,
    WhoAmIResponse,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


_COORDINATOR = "https://api.example.com"


def _cli_config() -> CLIConfig:
    return CLIConfig(
        client_id="test-client",
        authorization_endpoint="https://auth.example.com/authorize",
        token_endpoint="https://auth.example.com/token",
    )


def _whoami() -> WhoAmIResponse:
    return WhoAmIResponse(
        account_id="acc-1",
        email="user@example.com",
        organizations=[OrgInfo(org_id="org-1", name="Acme", is_default=True)],
        projects=[ProjectInfo(project_id="proj-1", name="Main", is_default=True)],
    )


def _tokens() -> TokenResponse:
    return TokenResponse(
        access_token="acc-tok",
        refresh_token="ref-tok",
        expires_in=3600,
        token_type="Bearer",
    )


@dataclass
class _FakeElicitResult:
    """Minimal stand-in for ``ElicitResult`` so we don't import the real model."""

    action: str


def _patch_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    cli_config: CLIConfig | None = None,
    tokens: TokenResponse | None = None,
    whoami: WhoAmIResponse | None = None,
    fetch_cli_config_side_effect: Any = None,
    exchange_side_effect: Any = None,
    fetch_whoami_side_effect: Any = None,
    save_side_effect: Any = None,
    validate_side_effect: Any = None,
) -> dict[str, Any]:
    """Patch the bootstrap module's external dependencies and return counters."""
    counters: dict[str, Any] = {
        "fetch_cli_config_calls": 0,
        "exchange_calls": 0,
        "whoami_calls": 0,
        "save_calls": 0,
        "validate_calls": 0,
    }

    cfg = cli_config or _cli_config()
    tok = tokens or _tokens()
    woam = whoami or _whoami()

    def fake_fetch_cli_config(coordinator_url: str) -> CLIConfig:
        counters["fetch_cli_config_calls"] += 1
        if fetch_cli_config_side_effect is not None:
            if isinstance(fetch_cli_config_side_effect, Exception):
                raise fetch_cli_config_side_effect
            return fetch_cli_config_side_effect(coordinator_url)
        return cfg

    async def fake_exchange(
        cli_config: CLIConfig,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> TokenResponse:
        counters["exchange_calls"] += 1
        if exchange_side_effect is not None:
            if isinstance(exchange_side_effect, Exception):
                raise exchange_side_effect
            return await exchange_side_effect(cli_config, code, redirect_uri, code_verifier)
        return tok

    async def fake_whoami(coordinator_url: str, access_token: str) -> WhoAmIResponse:
        counters["whoami_calls"] += 1
        if fetch_whoami_side_effect is not None:
            if isinstance(fetch_whoami_side_effect, Exception):
                raise fetch_whoami_side_effect
            return await fetch_whoami_side_effect(coordinator_url, access_token)
        return woam

    async def fake_save(
        tokens: TokenResponse,
        whoami: WhoAmIResponse,
        coordinator_url: str,
    ) -> None:
        counters["save_calls"] += 1
        if save_side_effect is not None:
            if isinstance(save_side_effect, Exception):
                raise save_side_effect
            await save_side_effect(tokens, whoami, coordinator_url)

    def fake_validate(whoami: WhoAmIResponse) -> None:
        counters["validate_calls"] += 1
        if validate_side_effect is not None:
            if isinstance(validate_side_effect, Exception):
                raise validate_side_effect
            validate_side_effect(whoami)

    monkeypatch.setattr(
        "arcade_mcp_server.auth_bootstrap.fetch_cli_config", fake_fetch_cli_config
    )
    monkeypatch.setattr(
        "arcade_mcp_server.auth_bootstrap.exchange_code_for_tokens", fake_exchange
    )
    monkeypatch.setattr("arcade_mcp_server.auth_bootstrap.fetch_whoami", fake_whoami)
    monkeypatch.setattr(
        "arcade_mcp_server.auth_bootstrap.save_credentials_from_whoami", fake_save
    )
    monkeypatch.setattr(
        "arcade_mcp_server.auth_bootstrap.validate_whoami_org_project", fake_validate
    )
    return counters


def _hit_callback(url: str, *, code: str = "testcode", state: str | None = None) -> None:
    """Drive a successful callback to the listener via real HTTP."""
    full_url = f"{url}?code={code}&state={state}"
    try:
        with urlopen(full_url, timeout=2.0) as response:
            response.read()
    except HTTPError:
        # Some tests intentionally produce 4xx; the server still records state.
        pass
    except Exception:  # pragma: no cover - defensive
        pass


def _drive_callback_after(
    listener: OAuthCallbackServer, *, code: str = "testcode", delay: float = 0.05
) -> None:
    """Trigger the callback in a background thread after a small delay."""
    import threading

    def trigger() -> None:
        url = listener.get_redirect_uri()
        full_url = f"{url}?code={code}&state={listener._expected_state}"
        try:
            with urlopen(full_url, timeout=2.0) as response:
                response.read()
        except Exception:  # pragma: no cover - defensive
            pass

    t = threading.Timer(delay, trigger)
    t.daemon = True
    t.start()


# ---------------------------------------------------------------------------
# 16. With elicitation: callback arrives -> COMPLETED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_with_elicitation_completes_when_callback_arrives(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    counters = _patch_dependencies(monkeypatch)

    elicit_called: list[tuple[str, dict[str, Any]]] = []

    async def elicit(message: str, schema: dict[str, Any]) -> _FakeElicitResult:
        elicit_called.append((message, schema))
        return _FakeElicitResult(action="accept")

    slot = AttemptSlot()

    async def driver() -> None:
        # Drive the callback after the elicit returns accept and we're in the
        # waiting loop.
        await asyncio.sleep(0.1)
        attempt = slot.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="ok-code", delay=0.0)

    drive_task = asyncio.create_task(driver())
    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=elicit,
            slot=slot,
            timeout_seconds=5,
        )
    finally:
        drive_task.cancel()
        try:
            await drive_task
        except asyncio.CancelledError:
            pass
        await slot.shutdown()

    assert result.status == BootstrapStatus.COMPLETED
    assert len(elicit_called) == 1
    assert "Open this URL in your browser" in elicit_called[0][0]
    assert counters["fetch_cli_config_calls"] == 1
    assert counters["exchange_calls"] == 1
    assert counters["whoami_calls"] == 1
    assert counters["validate_calls"] == 1
    assert counters["save_calls"] == 1

    fd_out, fd_err = capfd.readouterr()
    assert fd_out == "" and fd_err == ""


# ---------------------------------------------------------------------------
# 17. With elicitation: accept arrives FIRST, callback later -> still COMPLETED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_with_elicitation_accept_before_callback_keeps_waiting_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    async def elicit(message: str, schema: dict[str, Any]) -> _FakeElicitResult:
        # Returns *immediately* with accept — well before any callback can arrive.
        return _FakeElicitResult(action="accept")

    async def driver() -> None:
        # Wait so accept goes first; the bootstrap_login should keep waiting.
        await asyncio.sleep(0.2)
        attempt = slot.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="late-code", delay=0.0)

    drive_task = asyncio.create_task(driver())
    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=elicit,
            slot=slot,
            timeout_seconds=5,
        )
    finally:
        drive_task.cancel()
        try:
            await drive_task
        except asyncio.CancelledError:
            pass
        await slot.shutdown()

    assert result.status == BootstrapStatus.COMPLETED


# ---------------------------------------------------------------------------
# 18. Decline -> FAILED("user_cancelled")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_with_elicitation_decline_is_failed_user_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    async def elicit(message: str, schema: dict[str, Any]) -> _FakeElicitResult:
        return _FakeElicitResult(action="decline")

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=elicit,
            slot=slot,
            timeout_seconds=5,
        )
    finally:
        await slot.shutdown()

    assert result.status == BootstrapStatus.FAILED
    assert result.reason == "user_cancelled"


# ---------------------------------------------------------------------------
# 19. Cancel -> FAILED("user_cancelled")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_with_elicitation_cancel_is_failed_user_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    async def elicit(message: str, schema: dict[str, Any]) -> _FakeElicitResult:
        return _FakeElicitResult(action="cancel")

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=elicit,
            slot=slot,
            timeout_seconds=5,
        )
    finally:
        await slot.shutdown()

    assert result.status == BootstrapStatus.FAILED
    assert result.reason == "user_cancelled"


# ---------------------------------------------------------------------------
# 20. Elicit timeout -> FAILED("timed_out")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_with_elicitation_timeout_is_failed_timed_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    async def elicit(message: str, schema: dict[str, Any]) -> Any:
        raise asyncio.TimeoutError("elicit timed out")

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=elicit,
            slot=slot,
            timeout_seconds=5,
        )
    finally:
        await slot.shutdown()

    assert result.status == BootstrapStatus.FAILED
    assert result.reason == "timed_out"


# ---------------------------------------------------------------------------
# 21. Unexpected elicit error -> FAILED("internal_error")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_with_elicitation_unexpected_session_error_is_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    async def elicit(message: str, schema: dict[str, Any]) -> Any:
        raise RuntimeError("session blew up")

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=elicit,
            slot=slot,
            timeout_seconds=5,
        )
    finally:
        await slot.shutdown()

    assert result.status == BootstrapStatus.FAILED
    assert result.reason == "internal_error"


# ---------------------------------------------------------------------------
# 22. No elicit -> URL_FOR_FALLBACK returned synchronously
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_without_elicitation_returns_url_synchronously(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    counters = _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
        )
        # URL is returned BEFORE any callback arrives.
        assert result.status == BootstrapStatus.URL_FOR_FALLBACK
        assert result.auth_url is not None
        assert "code_challenge=" in result.auth_url
        assert counters["fetch_cli_config_calls"] == 1
        # No exchange/whoami/save yet — the background task is waiting on the
        # listener.
        assert counters["exchange_calls"] == 0
        assert counters["whoami_calls"] == 0
        assert counters["save_calls"] == 0
    finally:
        await slot.shutdown()


# ---------------------------------------------------------------------------
# 23. No elicit + later callback -> COMPLETED via background task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_without_elicitation_writes_credentials_on_later_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    counters = _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
        )
        assert result.status == BootstrapStatus.URL_FOR_FALLBACK

        attempt = slot.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="bg-code", delay=0.05)

        completion = await asyncio.wait_for(
            asyncio.shield(attempt.completion), timeout=5.0
        )
        assert completion.status == BootstrapStatus.COMPLETED
        assert counters["exchange_calls"] == 1
        assert counters["whoami_calls"] == 1
        assert counters["save_calls"] == 1
        assert counters["validate_calls"] == 1
    finally:
        await slot.shutdown()


# ---------------------------------------------------------------------------
# 24. Invalid callback paths do not kill pending attempt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_invalid_callback_paths_do_not_kill_pending_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
        )
        assert result.status == BootstrapStatus.URL_FOR_FALLBACK

        attempt = slot.current
        assert attempt is not None
        port = attempt.listener.port

        # Hit /favicon.ico and confirm 404.
        try:
            with urlopen(f"http://127.0.0.1:{port}/favicon.ico", timeout=2.0) as response:
                response.read()
        except HTTPError as e:
            assert e.code == 404

        # Listener should not have advanced.
        await asyncio.sleep(0.05)
        assert not attempt.listener.result_event.is_set()
        assert attempt.listener.result == {}
        assert not attempt.completion.done()

        # Now drive the real callback.
        _drive_callback_after(attempt.listener, code="zzz", delay=0.0)
        completion = await asyncio.wait_for(
            asyncio.shield(attempt.completion), timeout=5.0
        )
        assert completion.status == BootstrapStatus.COMPLETED
    finally:
        await slot.shutdown()


# ---------------------------------------------------------------------------
# 25. Concurrent elicitation joiners share one listener and completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_concurrent_elicitation_callers_each_receive_url_via_elicit_and_share_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    counters = _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    listener_created: list[OAuthCallbackServer] = []

    def listener_factory(state: str) -> OAuthCallbackServer:
        srv = OAuthCallbackServer(expected_state=state, port=0)
        listener_created.append(srv)
        return srv

    elicit_messages: list[str] = []

    async def elicit(message: str, schema: dict[str, Any]) -> _FakeElicitResult:
        elicit_messages.append(message)
        # Sleep a bit so both callers have a chance to enter elicit before any
        # callback arrives.
        await asyncio.sleep(0.2)
        return _FakeElicitResult(action="accept")

    async def caller() -> Any:
        return await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=elicit,
            slot=slot,
            timeout_seconds=5,
            listener_factory=listener_factory,
        )

    async def driver() -> None:
        # Wait for both attempts to be in elicit-wait, then trigger callback.
        await asyncio.sleep(0.5)
        attempt = slot.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="shared", delay=0.0)

    drive_task = asyncio.create_task(driver())
    try:
        results = await asyncio.gather(caller(), caller())
    finally:
        drive_task.cancel()
        try:
            await drive_task
        except asyncio.CancelledError:
            pass
        await slot.shutdown()

    assert all(r.status == BootstrapStatus.COMPLETED for r in results)
    assert len(elicit_messages) == 2
    assert elicit_messages[0] == elicit_messages[1]
    # Exactly one listener bound; one fetch_cli_config; one exchange/whoami/save.
    assert len(listener_created) == 1
    assert counters["fetch_cli_config_calls"] == 1
    assert counters["exchange_calls"] == 1
    assert counters["whoami_calls"] == 1
    assert counters["save_calls"] == 1


# ---------------------------------------------------------------------------
# 26. Concurrent no-elicit callers share one listener and URL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_concurrent_no_elicitation_callers_share_one_url_and_listener(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    counters = _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    listener_created: list[OAuthCallbackServer] = []

    def listener_factory(state: str) -> OAuthCallbackServer:
        srv = OAuthCallbackServer(expected_state=state, port=0)
        listener_created.append(srv)
        return srv

    async def caller() -> Any:
        return await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
            listener_factory=listener_factory,
        )

    try:
        results = await asyncio.gather(caller(), caller())
        assert all(r.status == BootstrapStatus.URL_FOR_FALLBACK for r in results)
        assert results[0].auth_url == results[1].auth_url
        assert len(listener_created) == 1
        assert counters["fetch_cli_config_calls"] == 1
    finally:
        await slot.shutdown()


# ---------------------------------------------------------------------------
# 27. Mixed callers: no-elicit then elicit join completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_mixed_callers_no_elicit_then_elicit_join_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    counters = _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    listener_created: list[OAuthCallbackServer] = []

    def listener_factory(state: str) -> OAuthCallbackServer:
        srv = OAuthCallbackServer(expected_state=state, port=0)
        listener_created.append(srv)
        return srv

    # 1: no-elicit
    result_no_elicit = await bootstrap_login(
        coordinator_url=_COORDINATOR,
        elicit=None,
        slot=slot,
        timeout_seconds=5,
        listener_factory=listener_factory,
    )
    assert result_no_elicit.status == BootstrapStatus.URL_FOR_FALLBACK
    fallback_url = result_no_elicit.auth_url

    # 2: elicit-capable joiner
    elicit_messages: list[str] = []

    async def elicit(message: str, schema: dict[str, Any]) -> _FakeElicitResult:
        elicit_messages.append(message)
        return _FakeElicitResult(action="accept")

    async def driver() -> None:
        # Drive the callback after the elicit joiner has had a chance.
        await asyncio.sleep(0.2)
        attempt = slot.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="mixed", delay=0.0)

    drive_task = asyncio.create_task(driver())
    try:
        result_with_elicit = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=elicit,
            slot=slot,
            timeout_seconds=5,
            listener_factory=listener_factory,
        )
    finally:
        drive_task.cancel()
        try:
            await drive_task
        except asyncio.CancelledError:
            pass

    try:
        assert result_with_elicit.status == BootstrapStatus.COMPLETED
        assert len(listener_created) == 1
        # The same URL was offered to both callers.
        assert fallback_url is not None
        assert fallback_url in elicit_messages[0]
        # 1 + 1 = 2 callers, but only 1 underlying flow.
        assert counters["fetch_cli_config_calls"] == 1
        assert counters["exchange_calls"] == 1
        assert counters["whoami_calls"] == 1
        assert counters["save_calls"] == 1
    finally:
        await slot.shutdown()


# ---------------------------------------------------------------------------
# 28. Expired attempt is replaced
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_expired_attempt_is_replaced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    counters = _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    listener_created: list[OAuthCallbackServer] = []

    def listener_factory(state: str) -> OAuthCallbackServer:
        srv = OAuthCallbackServer(expected_state=state, port=0)
        listener_created.append(srv)
        return srv

    try:
        result1 = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
            listener_factory=listener_factory,
        )
        assert result1.status == BootstrapStatus.URL_FOR_FALLBACK
        first_attempt = slot.current
        assert first_attempt is not None

        # Force expiry.
        first_attempt.expires_at = time.monotonic() - 1.0

        result2 = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
            listener_factory=listener_factory,
        )
        assert result2.status == BootstrapStatus.URL_FOR_FALLBACK
        new_attempt = slot.current
        assert new_attempt is not None
        assert new_attempt is not first_attempt
        # Two listeners constructed (old + new).
        assert len(listener_created) == 2
        # Two fetch_cli_config calls (old + new).
        assert counters["fetch_cli_config_calls"] == 2
    finally:
        await slot.shutdown()


# ---------------------------------------------------------------------------
# 29. Port-in-use returns FAILED, no output
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_port_in_use_returns_failed_no_output(
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    try:
        _, blocked_port = blocker.getsockname()

        def listener_factory(state: str) -> OAuthCallbackServer:
            return OAuthCallbackServer(expected_state=state, port=blocked_port)

        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
            listener_factory=listener_factory,
        )
        assert result.status == BootstrapStatus.FAILED
        assert result.reason == "port_in_use"
        # Slot remains empty since listener never started.
        assert slot.current is None
    finally:
        blocker.close()
        await slot.shutdown()

    fd_out, fd_err = capfd.readouterr()
    assert fd_out == "" and fd_err == ""


# ---------------------------------------------------------------------------
# 30. Token exchange failure -> FAILED clean
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_token_exchange_failure_is_failed_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    request = httpx.Request("POST", "https://auth.example.com/token")
    response = httpx.Response(400, text="invalid_grant", request=request)
    counters = _patch_dependencies(
        monkeypatch,
        exchange_side_effect=httpx.HTTPStatusError(
            "boom", request=request, response=response
        ),
    )
    slot = AttemptSlot()

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
        )
        assert result.status == BootstrapStatus.URL_FOR_FALLBACK

        attempt = slot.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="bad-token-flow", delay=0.05)
        completion = await asyncio.wait_for(
            asyncio.shield(attempt.completion), timeout=5.0
        )
        assert completion.status == BootstrapStatus.FAILED
        assert completion.reason == "token_exchange_failed"
        assert counters["save_calls"] == 0
    finally:
        await slot.shutdown()


# ---------------------------------------------------------------------------
# 31. Whoami failure -> FAILED clean
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_whoami_failure_is_failed_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    request = httpx.Request("GET", "https://api.example.com/whoami")
    response = httpx.Response(401, text="unauth", request=request)
    counters = _patch_dependencies(
        monkeypatch,
        fetch_whoami_side_effect=httpx.HTTPStatusError(
            "boom", request=request, response=response
        ),
    )
    slot = AttemptSlot()

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
        )
        assert result.status == BootstrapStatus.URL_FOR_FALLBACK

        attempt = slot.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="whoami-fail", delay=0.05)
        completion = await asyncio.wait_for(
            asyncio.shield(attempt.completion), timeout=5.0
        )
        assert completion.status == BootstrapStatus.FAILED
        assert completion.reason == "whoami_failed"
        assert counters["save_calls"] == 0
    finally:
        await slot.shutdown()


# ---------------------------------------------------------------------------
# 32. NoOrgsError -> FAILED clean, no creds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_no_orgs_is_failed_clean_no_credentials_written(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    counters = _patch_dependencies(
        monkeypatch, validate_side_effect=NoOrgsError("no orgs")
    )
    slot = AttemptSlot()

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
        )
        assert result.status == BootstrapStatus.URL_FOR_FALLBACK
        attempt = slot.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="no-orgs", delay=0.05)
        completion = await asyncio.wait_for(
            asyncio.shield(attempt.completion), timeout=5.0
        )
        assert completion.status == BootstrapStatus.FAILED
        assert completion.reason == "no_orgs"
        assert counters["save_calls"] == 0
    finally:
        await slot.shutdown()


# ---------------------------------------------------------------------------
# 33. NoProjectsError -> FAILED clean, no creds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_no_projects_is_failed_clean_no_credentials_written(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    counters = _patch_dependencies(
        monkeypatch, validate_side_effect=NoProjectsError("no projects")
    )
    slot = AttemptSlot()

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
        )
        assert result.status == BootstrapStatus.URL_FOR_FALLBACK
        attempt = slot.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="no-projects", delay=0.05)
        completion = await asyncio.wait_for(
            asyncio.shield(attempt.completion), timeout=5.0
        )
        assert completion.status == BootstrapStatus.FAILED
        assert completion.reason == "no_projects"
        assert counters["save_calls"] == 0
    finally:
        await slot.shutdown()


# ---------------------------------------------------------------------------
# 34. Save failure -> FAILED clean
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_credentials_save_failure_is_failed_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    counters = _patch_dependencies(
        monkeypatch, save_side_effect=OSError("disk full")
    )
    slot = AttemptSlot()

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
        )
        assert result.status == BootstrapStatus.URL_FOR_FALLBACK
        attempt = slot.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="save-fail", delay=0.05)
        completion = await asyncio.wait_for(
            asyncio.shield(attempt.completion), timeout=5.0
        )
        assert completion.status == BootstrapStatus.FAILED
        assert completion.reason == "save_failed"
        # Save was attempted exactly once.
        assert counters["save_calls"] == 1
    finally:
        await slot.shutdown()


# ---------------------------------------------------------------------------
# 35. No stdout/stderr across both paths and several errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_emits_no_stdout_or_stderr(
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        bootstrap_login,
    )

    # Path 1: elicit + accept + callback success
    _patch_dependencies(monkeypatch)
    slot1 = AttemptSlot()

    async def elicit_accept(message: str, schema: dict[str, Any]) -> _FakeElicitResult:
        return _FakeElicitResult(action="accept")

    async def driver1() -> None:
        await asyncio.sleep(0.05)
        attempt = slot1.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="silent-1", delay=0.0)

    drive1 = asyncio.create_task(driver1())
    try:
        await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=elicit_accept,
            slot=slot1,
            timeout_seconds=5,
        )
    finally:
        drive1.cancel()
        try:
            await drive1
        except asyncio.CancelledError:
            pass
        await slot1.shutdown()

    # Path 2: no elicit, callback flow
    _patch_dependencies(monkeypatch)
    slot2 = AttemptSlot()
    try:
        await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot2,
            timeout_seconds=5,
        )
        attempt = slot2.current
        assert attempt is not None
        _drive_callback_after(attempt.listener, code="silent-2", delay=0.05)
        await asyncio.wait_for(asyncio.shield(attempt.completion), timeout=5.0)
    finally:
        await slot2.shutdown()

    # Path 3: decline
    _patch_dependencies(monkeypatch)
    slot3 = AttemptSlot()

    async def elicit_decline(message: str, schema: dict[str, Any]) -> _FakeElicitResult:
        return _FakeElicitResult(action="decline")

    try:
        await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=elicit_decline,
            slot=slot3,
            timeout_seconds=5,
        )
    finally:
        await slot3.shutdown()

    # Path 4: cli_config failure
    counters = _patch_dependencies(
        monkeypatch, fetch_cli_config_side_effect=httpx.HTTPError("connect refused")
    )
    slot4 = AttemptSlot()
    try:
        await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot4,
            timeout_seconds=5,
        )
    finally:
        await slot4.shutdown()
    assert counters["fetch_cli_config_calls"] == 1

    fd_out, fd_err = capfd.readouterr()
    assert fd_out == "" and fd_err == ""


# ---------------------------------------------------------------------------
# 36. AttemptSlot.shutdown cancels task and closes listener
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attempt_slot_shutdown_cancels_task_and_closes_listener(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    _patch_dependencies(monkeypatch)
    slot = AttemptSlot()

    result = await bootstrap_login(
        coordinator_url=_COORDINATOR,
        elicit=None,
        slot=slot,
        timeout_seconds=5,
    )
    assert result.status == BootstrapStatus.URL_FOR_FALLBACK

    attempt = slot.current
    assert attempt is not None
    assert attempt.background_task is not None
    assert not attempt.background_task.done()
    assert attempt.listener.started_event.is_set()

    await slot.shutdown()
    assert slot.current is None
    # The background task is either cancelled or done.
    assert attempt.background_task.done()

    # Idempotent.
    await slot.shutdown()


# ---------------------------------------------------------------------------
# Bonus: cli_config failure on initial build returns FAILED("cli_config_failed")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_cli_config_failure_is_failed_no_listener(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arcade_mcp_server.auth_bootstrap import (
        AttemptSlot,
        BootstrapStatus,
        bootstrap_login,
    )

    listener_created: list[OAuthCallbackServer] = []

    def listener_factory(state: str) -> OAuthCallbackServer:
        srv = OAuthCallbackServer(expected_state=state, port=0)
        listener_created.append(srv)
        return srv

    _patch_dependencies(
        monkeypatch, fetch_cli_config_side_effect=httpx.HTTPError("connect refused")
    )
    slot = AttemptSlot()

    try:
        result = await bootstrap_login(
            coordinator_url=_COORDINATOR,
            elicit=None,
            slot=slot,
            timeout_seconds=5,
            listener_factory=listener_factory,
        )
        assert result.status == BootstrapStatus.FAILED
        assert result.reason == "cli_config_failed"
        # No listener was constructed because cli_config failed first.
        assert len(listener_created) == 0
        assert slot.current is None
    finally:
        await slot.shutdown()
