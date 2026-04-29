"""Server-side OAuth bootstrap orchestration.

This module owns the in-server OAuth login flow. It is invoked from the MCP
server when an auth-requiring tool is called and no Arcade access token is
available. There are two paths:

* **Elicit path**: the MCP client supports the ``elicitation`` capability, so
  we send an elicit with the auth URL and race it against the callback.
  Returns ``COMPLETED`` or ``FAILED``.
* **Fallback path**: no elicitation. We return the URL synchronously to the
  caller (so it can be surfaced in a tool error response) and drive the
  callback in the background; the slot's ``completion`` future is fulfilled
  with the eventual result.

Concurrent calls join the live attempt — only one listener is bound and only
one ``fetch_cli_config`` HTTP call is made per attempt.

This module is stdio-safe: nothing prints; all logging goes through the
module-level :data:`logger`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
from arcade_core.auth_tokens import CLIConfig, fetch_cli_config
from arcade_core.oauth_login import (
    NoOrgsError,
    NoProjectsError,
    OAuthCallbackServer,
    WhoAmIResponse,
    exchange_code_for_tokens,
    fetch_whoami,
    generate_authorization_url,
    save_credentials_from_whoami,
    validate_whoami_org_project,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class BootstrapStatus(str, Enum):
    """Terminal status of an OAuth bootstrap attempt."""

    COMPLETED = "completed"
    URL_FOR_FALLBACK = "url_for_fallback"
    FAILED = "failed"


@dataclass
class BootstrapResult:
    """Result of a single :func:`bootstrap_login` call."""

    status: BootstrapStatus
    auth_url: str | None = None
    reason: str | None = None
    detail: str | None = None

    @classmethod
    def completed(cls) -> BootstrapResult:
        return cls(status=BootstrapStatus.COMPLETED)

    @classmethod
    def url_for_fallback(cls, url: str) -> BootstrapResult:
        return cls(status=BootstrapStatus.URL_FOR_FALLBACK, auth_url=url)

    @classmethod
    def failed(cls, reason: str, detail: str | None = None) -> BootstrapResult:
        return cls(status=BootstrapStatus.FAILED, reason=reason, detail=detail)


# Elicitation result shape from the MCP session — see ``session.py``.
# We accept anything with an ``action`` attribute (one of "accept", "decline",
# "cancel") to avoid coupling to a specific Pydantic model in this module.
ElicitCallable = Callable[[str, dict[str, Any]], Awaitable[Any]]


# ---------------------------------------------------------------------------
# Login attempt state
# ---------------------------------------------------------------------------


@dataclass
class LoginAttempt:
    """Single in-flight OAuth attempt shared across joiners."""

    auth_url: str
    state: str
    code_verifier: str
    cli_config: CLIConfig
    redirect_uri: str
    started_at: float
    expires_at: float
    listener: OAuthCallbackServer
    completion: asyncio.Future[BootstrapResult]
    background_task: asyncio.Task[None] | None = None

    def is_expired(self, now: float | None = None) -> bool:
        return (now if now is not None else time.monotonic()) >= self.expires_at


class AttemptSlot:
    """Owns the single in-flight login attempt for an MCPServer.

    All callers serialize through :meth:`acquire_or_join` to either start a
    new attempt or join the existing live one. :meth:`shutdown` cancels the
    background task and closes the listener.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._attempt: LoginAttempt | None = None

    @property
    def current(self) -> LoginAttempt | None:
        return self._attempt

    async def acquire_or_join(
        self,
        factory: Callable[[], Awaitable[LoginAttempt]],
    ) -> LoginAttempt:
        """Returns the live attempt, creating a new one if absent/expired/done."""
        async with self._lock:
            if (
                self._attempt is None
                or self._attempt.is_expired()
                or self._attempt.completion.done()
            ):
                if self._attempt is not None:
                    await self._teardown_locked(self._attempt)
                self._attempt = await factory()
            return self._attempt

    async def shutdown(self) -> None:
        """Cancel the background task and close the listener. Idempotent."""
        async with self._lock:
            if self._attempt is not None:
                await self._teardown_locked(self._attempt)
                self._attempt = None

    async def _teardown_locked(self, attempt: LoginAttempt) -> None:
        if attempt.background_task is not None and not attempt.background_task.done():
            attempt.background_task.cancel()
            try:
                await attempt.background_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug("Background task raised during teardown: %s", e)
        try:
            await attempt.listener.shutdown()
        except Exception as e:
            logger.debug("Listener shutdown raised: %s", e)
        if not attempt.completion.done():
            attempt.completion.cancel()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _default_listener_factory(state: str) -> OAuthCallbackServer:
    return OAuthCallbackServer(expected_state=state, port=0)


def _build_elicit_message(auth_url: str) -> str:
    return (
        "Sign in to Arcade to continue.\n\n"
        f"Open this URL in your browser:\n{auth_url}\n\n"
        "This page will refresh automatically when you finish."
    )


_ELICIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "acknowledge": {
            "type": "boolean",
            "description": "Acknowledge that you've started the sign-in flow",
        }
    },
    "required": [],
}


async def _create_attempt(
    *,
    coordinator_url: str,
    timeout_seconds: int,
    listener_factory: Callable[[str], OAuthCallbackServer],
) -> LoginAttempt:
    """Build URL + start listener. Raises on cli_config / bind failure."""
    cli_config = await asyncio.to_thread(fetch_cli_config, coordinator_url)

    state = secrets.token_urlsafe(32)
    listener = listener_factory(state)

    if not listener.started_event.is_set():
        # Bind synchronously in a thread so we don't block the loop on the
        # OS bind call. ``start()`` raises ``OSError`` on bind failure.
        await asyncio.to_thread(listener.start)

    redirect_uri = listener.get_redirect_uri()
    auth_url, code_verifier = generate_authorization_url(cli_config, redirect_uri, state)

    started = time.monotonic()
    completion: asyncio.Future[BootstrapResult] = asyncio.get_running_loop().create_future()

    return LoginAttempt(
        auth_url=auth_url,
        state=state,
        code_verifier=code_verifier,
        cli_config=cli_config,
        redirect_uri=redirect_uri,
        started_at=started,
        expires_at=started + timeout_seconds,
        listener=listener,
        completion=completion,
    )


async def _drive_post_callback(attempt: LoginAttempt, coordinator_url: str) -> BootstrapResult:
    """Run exchange/whoami/validate/save after the listener fires.

    Assumes :meth:`OAuthCallbackServer.wait_for_result` already returned True.
    """
    listener_result = attempt.listener.result
    if "error" in listener_result:
        error_text = str(listener_result.get("error", "unknown listener error"))
        # CSRF error is the primary listener-recorded error; treat as
        # user-cancelled-ish to avoid leaking implementation details.
        reason = "user_cancelled" if "CSRF" in error_text else "internal_error"
        return BootstrapResult.failed(reason, error_text)

    code = listener_result.get("code")
    if not code:
        return BootstrapResult.failed("internal_error", "Callback succeeded without a code.")

    try:
        tokens = await exchange_code_for_tokens(
            attempt.cli_config,
            code,
            attempt.redirect_uri,
            attempt.code_verifier,
        )
    except Exception as e:
        logger.warning("Token exchange failed during bootstrap: %s", e)
        return BootstrapResult.failed("token_exchange_failed", str(e))

    try:
        whoami: WhoAmIResponse = await fetch_whoami(coordinator_url, tokens.access_token)
    except Exception as e:
        logger.warning("Whoami failed during bootstrap: %s", e)
        return BootstrapResult.failed("whoami_failed", str(e))

    try:
        validate_whoami_org_project(whoami)
    except NoOrgsError as e:
        logger.warning("Bootstrap validation failed: no orgs (%s)", e)
        return BootstrapResult.failed("no_orgs", str(e))
    except NoProjectsError as e:
        logger.warning("Bootstrap validation failed: no projects (%s)", e)
        return BootstrapResult.failed("no_projects", str(e))
    except Exception as e:
        logger.warning("Bootstrap validation raised unexpectedly: %s", e)
        return BootstrapResult.failed("internal_error", str(e))

    try:
        await save_credentials_from_whoami(tokens, whoami, coordinator_url)
    except Exception as e:
        logger.warning("Credentials save failed during bootstrap: %s", e)
        return BootstrapResult.failed("save_failed", str(e))

    return BootstrapResult.completed()


async def _run_callback_pipeline(
    attempt: LoginAttempt, coordinator_url: str, timeout_seconds: int
) -> BootstrapResult:
    """Wait for the listener, then run the post-callback pipeline.

    The listener wait is offloaded to a worker thread because the underlying
    primitive is a blocking ``threading.Event.wait``.
    """
    arrived = await asyncio.to_thread(attempt.listener.wait_for_result, timeout_seconds)
    if not arrived:
        return BootstrapResult.failed(
            "timed_out",
            f"Timed out waiting for callback after {timeout_seconds}s.",
        )
    return await _drive_post_callback(attempt, coordinator_url)


def _spawn_background_task(
    attempt: LoginAttempt, coordinator_url: str, timeout_seconds: int
) -> asyncio.Task[None]:
    """Drive the post-callback pipeline and fulfil ``attempt.completion``.

    Errors are swallowed and converted into ``BootstrapResult.failed`` so the
    task never raises into the event loop.
    """

    async def runner() -> None:
        try:
            result = await _run_callback_pipeline(attempt, coordinator_url, timeout_seconds)
        except asyncio.CancelledError:
            if not attempt.completion.done():
                attempt.completion.cancel()
            raise
        except Exception as e:
            logger.exception("Bootstrap background task crashed")
            result = BootstrapResult.failed("internal_error", str(e))
        if not attempt.completion.done():
            attempt.completion.set_result(result)

    return asyncio.create_task(runner())


async def _run_elicit_safely(
    elicit: ElicitCallable, message: str, schema: dict[str, Any]
) -> BootstrapResult | str:
    """Run the elicit and translate the outcome.

    Returns ``"accept"`` to indicate "keep waiting on completion", or a
    terminal :class:`BootstrapResult` otherwise.
    """
    try:
        elicit_result = await elicit(message, schema)
    except asyncio.TimeoutError as e:
        logger.warning("Elicit timed out: %s", e)
        return BootstrapResult.failed("timed_out", str(e) or "Elicit timed out.")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.warning("Elicit raised unexpectedly: %s", e)
        return BootstrapResult.failed("internal_error", str(e))

    action = getattr(elicit_result, "action", None)
    if action == "accept":
        return "accept"
    if action == "decline":
        return BootstrapResult.failed("user_cancelled", "User declined the sign-in prompt.")
    if action == "cancel":
        return BootstrapResult.failed("user_cancelled", "User cancelled the sign-in prompt.")
    if action is None:
        return BootstrapResult.failed("user_cancelled", "Elicit returned None.")
    return BootstrapResult.failed("user_cancelled", f"Unexpected elicit action: {action}")


async def _await_completion_with_deadline(
    attempt: LoginAttempt,
) -> BootstrapResult:
    """Await ``attempt.completion`` honoring its overall expiry."""
    now = time.monotonic()
    remaining = attempt.expires_at - now
    if remaining <= 0:
        return BootstrapResult.failed(
            "timed_out", "Sign-in attempt expired before the callback arrived."
        )
    try:
        return await asyncio.wait_for(asyncio.shield(attempt.completion), timeout=remaining)
    except asyncio.TimeoutError:
        return BootstrapResult.failed(
            "timed_out", "Sign-in attempt expired before the callback arrived."
        )
    except asyncio.CancelledError:
        raise


async def _race_elicit_against_completion(
    elicit: ElicitCallable,
    attempt: LoginAttempt,
) -> BootstrapResult:
    """Race a single elicit call against ``attempt.completion``.

    Loops if elicit returns ``accept`` (the user acknowledged but the
    callback hasn't arrived yet). The total time budget is bounded by
    ``attempt.expires_at``.
    """
    message = _build_elicit_message(attempt.auth_url)

    while True:
        if attempt.completion.done():
            try:
                return attempt.completion.result()
            except asyncio.CancelledError:
                return BootstrapResult.failed(
                    "internal_error", "Login completion future was cancelled."
                )

        now = time.monotonic()
        remaining = attempt.expires_at - now
        if remaining <= 0:
            return BootstrapResult.failed(
                "timed_out",
                "Sign-in attempt expired before the user acknowledged the prompt.",
            )

        elicit_task: asyncio.Task[BootstrapResult | str] = asyncio.create_task(
            _run_elicit_safely(elicit, message, _ELICIT_SCHEMA)
        )
        completion_task: asyncio.Task[BootstrapResult] = asyncio.ensure_future(
            asyncio.shield(attempt.completion)
        )
        tasks: set[asyncio.Task[Any]] = {elicit_task, completion_task}

        try:
            done, _pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
                timeout=remaining,
            )
        except asyncio.CancelledError:
            elicit_task.cancel()
            completion_task.cancel()
            raise

        if not done:
            # Timed out at the deadline.
            elicit_task.cancel()
            completion_task.cancel()
            return BootstrapResult.failed(
                "timed_out",
                "Sign-in attempt expired before the user acknowledged the prompt.",
            )

        if completion_task in done:
            elicit_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await elicit_task
            try:
                return completion_task.result()
            except asyncio.CancelledError:
                return BootstrapResult.failed(
                    "internal_error", "Login completion future was cancelled."
                )

        # elicit finished first
        completion_task.cancel()
        try:
            elicit_outcome = elicit_task.result()
        except Exception as e:
            logger.warning("Elicit task surfaced an exception: %s", e)
            return BootstrapResult.failed("internal_error", str(e))

        if isinstance(elicit_outcome, BootstrapResult):
            return elicit_outcome

        # elicit returned "accept" — keep waiting on completion alone.
        return await _await_completion_with_deadline(attempt)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def bootstrap_login(
    *,
    coordinator_url: str,
    elicit: ElicitCallable | None,
    slot: AttemptSlot,
    timeout_seconds: int,
    listener_factory: Callable[[str], OAuthCallbackServer] | None = None,
) -> BootstrapResult:
    """Orchestrate an Arcade OAuth login from inside the MCP server.

    See module docstring for the full behavior matrix.
    """
    factory_callable = listener_factory or _default_listener_factory

    # Build the attempt. ``acquire_or_join`` serializes via the slot lock so
    # concurrent callers either share an existing live attempt or wait for
    # exactly one factory invocation.
    creation_failure: list[BootstrapResult] = []

    async def factory() -> LoginAttempt:
        try:
            attempt = await _create_attempt(
                coordinator_url=coordinator_url,
                timeout_seconds=timeout_seconds,
                listener_factory=factory_callable,
            )
        except OSError as e:
            logger.warning("OAuth callback listener bind failed: %s", e)
            creation_failure.append(BootstrapResult.failed("port_in_use", str(e)))
            raise
        except httpx.HTTPError as e:
            logger.warning("Bootstrap fetch_cli_config failed: %s", e)
            creation_failure.append(BootstrapResult.failed("cli_config_failed", str(e)))
            raise
        except Exception as e:
            logger.warning("Bootstrap attempt creation failed: %s", e)
            creation_failure.append(BootstrapResult.failed("cli_config_failed", str(e)))
            raise
        return attempt

    try:
        attempt = await slot.acquire_or_join(factory)
    except (OSError, httpx.HTTPError, Exception):
        if creation_failure:
            return creation_failure[0]
        return BootstrapResult.failed("internal_error", "Attempt creation failed.")

    # If this is a brand-new attempt and there's no background task, the
    # ``acquire_or_join`` callsite is responsible for spinning one up.
    is_owner = attempt.background_task is None

    if is_owner and elicit is None:
        # Fallback path: spawn the background task and return URL.
        attempt.background_task = _spawn_background_task(attempt, coordinator_url, timeout_seconds)

    if elicit is None:
        return BootstrapResult.url_for_fallback(attempt.auth_url)

    # Elicit path — joiners and owners both run this.
    if is_owner:
        # Owner needs a background task too so that the listener post-callback
        # pipeline runs even if the elicit caller hangs/aborts.
        attempt.background_task = _spawn_background_task(attempt, coordinator_url, timeout_seconds)

    try:
        return await _race_elicit_against_completion(elicit, attempt)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("Bootstrap login orchestration crashed")
        return BootstrapResult.failed("internal_error", str(e))
