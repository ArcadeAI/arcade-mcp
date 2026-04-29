"""
OAuth login primitives shared by the Arcade CLI and the MCP server.

This module is intentionally pure-stdlib + httpx — no authlib, no Jinja2, no
extra dependencies. It is safe to import in MCP stdio paths because no code
in this module writes to ``sys.stdout`` or ``sys.stderr`` (the request
handler suppresses logging, ``handle_error`` routes exceptions through a
NullHandler-only logger, and broken pipes are silently swallowed).

Public surface:

* Constants: ``LOCAL_CALLBACK_HOST``, ``LOCAL_CALLBACK_PORT``,
  ``DEFAULT_SCOPES``, ``DEFAULT_OAUTH_TIMEOUT_SECONDS``.
* Models: ``OrgInfo``, ``ProjectInfo``, ``WhoAmIResponse``.
* Errors: ``OAuthLoginError``, ``NoOrgsError``, ``NoProjectsError``.
* Functions: ``generate_authorization_url``, ``exchange_code_for_tokens``,
  ``fetch_whoami``, ``validate_whoami_org_project``,
  ``save_credentials_from_whoami``.
* Listener: ``OAuthCallbackServer`` and ``oauth_callback_server``.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import secrets
import socketserver
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode

import httpx
from pydantic import AliasChoices, BaseModel, Field

from arcade_core.auth_tokens import CLIConfig, TokenResponse
from arcade_core.config_model import AuthConfig, Config, ContextConfig, UserConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOCAL_CALLBACK_HOST: str = "127.0.0.1"
LOCAL_CALLBACK_PORT: int = 9905
DEFAULT_SCOPES: str = "openid offline_access"

_DEFAULT_OAUTH_TIMEOUT_FALLBACK_SECONDS: int = 600


def _get_default_oauth_timeout_seconds() -> int:
    value = os.environ.get(
        "ARCADE_LOGIN_TIMEOUT_SECONDS", str(_DEFAULT_OAUTH_TIMEOUT_FALLBACK_SECONDS)
    )
    try:
        parsed = int(value)
    except ValueError:
        return _DEFAULT_OAUTH_TIMEOUT_FALLBACK_SECONDS
    return parsed if parsed > 0 else _DEFAULT_OAUTH_TIMEOUT_FALLBACK_SECONDS


DEFAULT_OAUTH_TIMEOUT_SECONDS: int = _get_default_oauth_timeout_seconds()


# ---------------------------------------------------------------------------
# Logging — keep callback-server errors off stdout/stderr.
# ---------------------------------------------------------------------------

# A dedicated logger for the callback HTTP server. We attach a NullHandler
# and disable propagation so unhandled records (in particular records
# emitted from ``handle_error``) never reach stderr via the root logger.
_callback_logger = logging.getLogger("arcade_core.oauth_login.callback")
_callback_logger.addHandler(logging.NullHandler())
_callback_logger.propagate = False


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class OrgInfo(BaseModel):
    """Organization info from Coordinator."""

    org_id: str = Field(validation_alias=AliasChoices("org_id", "organization_id"))
    name: str
    is_default: bool = False


class ProjectInfo(BaseModel):
    """Project info from Coordinator."""

    project_id: str
    name: str
    is_default: bool = False


def _select_default_org(orgs: list[OrgInfo]) -> OrgInfo | None:
    if not orgs:
        return None
    for org in orgs:
        if org.is_default:
            return org
    return orgs[0]


def _select_default_project(projects: list[ProjectInfo]) -> ProjectInfo | None:
    if not projects:
        return None
    for project in projects:
        if project.is_default:
            return project
    return projects[0]


class WhoAmIResponse(BaseModel):
    """Response from Coordinator /whoami endpoint."""

    account_id: str
    email: str
    organizations: list[OrgInfo] = []
    projects: list[ProjectInfo] = []

    def get_selected_org(self) -> OrgInfo | None:
        return _select_default_org(self.organizations)

    def get_selected_project(self) -> ProjectInfo | None:
        return _select_default_project(self.projects)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class OAuthLoginError(Exception):
    """Error during OAuth login flow."""


class NoOrgsError(OAuthLoginError):
    """Whoami response contained no organizations."""


class NoProjectsError(OAuthLoginError):
    """Whoami response contained no projects in the selected organization."""


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def _pkce_challenge_from_verifier(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    # URL-safe base64 with no padding, per RFC 7636.
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_authorization_url(
    cli_config: CLIConfig,
    redirect_uri: str,
    state: str,
) -> tuple[str, str]:
    """Build an OAuth authorization URL with PKCE (S256).

    Returns ``(authorization_url, code_verifier)``. The caller is responsible
    for keeping ``code_verifier`` until token exchange.
    """
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = _pkce_challenge_from_verifier(code_verifier)

    params = {
        "response_type": "code",
        "client_id": cli_config.client_id,
        "redirect_uri": redirect_uri,
        "scope": DEFAULT_SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    separator = "&" if "?" in cli_config.authorization_endpoint else "?"
    auth_url = f"{cli_config.authorization_endpoint}{separator}{urlencode(params)}"
    return auth_url, code_verifier


async def exchange_code_for_tokens(
    cli_config: CLIConfig,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> TokenResponse:
    """Exchange an authorization code for OAuth tokens.

    Uses a single ``httpx.AsyncClient.post`` to ``cli_config.token_endpoint``.
    Raises :class:`OAuthLoginError` on HTTP failure.
    """
    payload = {
        "grant_type": "authorization_code",
        "client_id": cli_config.client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(cli_config.token_endpoint, data=payload)
    except httpx.HTTPError as exc:
        raise OAuthLoginError(f"Token exchange request failed: {exc}") from exc

    if response.status_code >= 400:
        raise OAuthLoginError(
            f"Token exchange failed with status {response.status_code}: {response.text}"
        )

    try:
        token = response.json()
    except ValueError as exc:
        raise OAuthLoginError(f"Token exchange returned invalid JSON: {exc}") from exc

    try:
        return TokenResponse(
            access_token=token["access_token"],
            refresh_token=token["refresh_token"],
            expires_in=token["expires_in"],
            token_type=token["token_type"],
        )
    except KeyError as exc:
        raise OAuthLoginError(f"Token exchange response missing field: {exc}") from exc


async def fetch_whoami(coordinator_url: str, access_token: str) -> WhoAmIResponse:
    """Fetch the current user's info and orgs/projects from the Coordinator.

    Expects a JSON response of the shape ``{"data": {...}}``. Raises
    :class:`OAuthLoginError` on HTTP failure or invalid JSON.
    """
    url = f"{coordinator_url}/api/v1/auth/whoami"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise OAuthLoginError(f"Whoami request failed: {exc}") from exc

    if response.status_code >= 400:
        raise OAuthLoginError(f"Whoami failed with status {response.status_code}: {response.text}")

    try:
        body = response.json()
    except ValueError as exc:
        raise OAuthLoginError(f"Whoami returned invalid JSON: {exc}") from exc

    data = body.get("data", {}) if isinstance(body, dict) else {}
    return WhoAmIResponse.model_validate(data)


def validate_whoami_org_project(whoami: WhoAmIResponse) -> None:
    """Ensure the whoami response has a selectable org and project.

    Raises :class:`NoOrgsError` if no org is available, or
    :class:`NoProjectsError` if an org exists but no project.
    """
    selected_org = whoami.get_selected_org()
    if selected_org is None:
        raise NoOrgsError(
            "No organizations found for your account. "
            "Please contact support@arcade.dev for assistance."
        )

    if whoami.get_selected_project() is None:
        raise NoProjectsError(
            f"No projects found in organization '{selected_org.name}'. "
            "Please contact support@arcade.dev for assistance."
        )


def _build_config_from_whoami(
    tokens: TokenResponse,
    whoami: WhoAmIResponse,
    coordinator_url: str,
) -> Config:
    expires_at = datetime.now() + timedelta(seconds=tokens.expires_in)

    context: ContextConfig | None = None
    selected_org = whoami.get_selected_org()
    selected_project = whoami.get_selected_project()
    if selected_org is not None and selected_project is not None:
        context = ContextConfig(
            org_id=selected_org.org_id,
            org_name=selected_org.name,
            project_id=selected_project.project_id,
            project_name=selected_project.name,
        )

    return Config(
        coordinator_url=coordinator_url,
        auth=AuthConfig(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_at=expires_at,
        ),
        user=UserConfig(email=whoami.email),
        context=context,
    )


async def save_credentials_from_whoami(
    tokens: TokenResponse,
    whoami: WhoAmIResponse,
    coordinator_url: str,
) -> None:
    """Persist OAuth credentials derived from a whoami response.

    Writes to ``~/.arcade/credentials.yaml`` (or the path resolved by
    ``Config.get_config_file_path()``). Runs the synchronous file write in a
    worker thread so we don't block the event loop, then invalidates the
    ``arcade_core.config.get_config`` LRU cache.
    """
    config = _build_config_from_whoami(tokens, whoami, coordinator_url)
    await asyncio.to_thread(config.save_to_file)

    # Invalidate the singleton config cache so callers reading config
    # immediately after login see the freshly written credentials.
    from arcade_core.config import get_config

    get_config.cache_clear()


# ---------------------------------------------------------------------------
# Local callback HTTP server
# ---------------------------------------------------------------------------


_SUCCESS_HTML = (
    b"<!doctype html><html><head><meta charset='utf-8'>"
    b"<title>Arcade login complete</title></head>"
    b"<body style='font-family:sans-serif;padding:2rem'>"
    b"<h1>Login complete</h1>"
    b"<p>You can close this tab and return to your terminal.</p>"
    b"</body></html>"
)

_ERROR_HTML = (
    b"<!doctype html><html><head><meta charset='utf-8'>"
    b"<title>Arcade login failed</title></head>"
    b"<body style='font-family:sans-serif;padding:2rem'>"
    b"<h1>Login failed</h1>"
    b"<p>Return to your terminal for details.</p>"
    b"</body></html>"
)


class _LoopbackHTTPServer(HTTPServer):
    """HTTPServer that skips the potentially slow ``getfqdn()`` reverse-DNS
    lookup in ``server_bind()``.

    ``HTTPServer.server_bind()`` calls ``socket.getfqdn(host)`` which invokes
    ``gethostbyaddr("127.0.0.1")`` via the system resolver.  On macOS CI
    runners (Apple Silicon / macOS 14) the mDNSResponder can take 5-30 s to
    resolve the loopback PTR record when the DNS cache is cold, causing the
    daemon thread to block inside the constructor and ``ready_event`` to never
    fire within the timeout window.

    We only listen on ``127.0.0.1`` for the OAuth callback, so we hard-set
    ``server_name`` to ``"127.0.0.1"`` and skip the DNS round-trip entirely.
    """

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host if isinstance(host, str) else host.decode()
        self.server_port = port

    def handle_error(self, request: Any, client_address: Any) -> None:
        # Keep all errors off stderr — route them through the dedicated
        # NullHandler logger so an unhandled handler exception does not
        # corrupt MCP stdio output.
        _callback_logger.debug("callback server error from %r", client_address, exc_info=True)


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the OAuth callback.

    Behaviors:

    * ``/callback`` with matching ``state`` and ``code``: 200 + success HTML;
      records ``code``/``state`` and shuts the server down.
    * ``/callback`` with mismatched ``state``: 400 + error HTML; records a
      CSRF error and shuts down.
    * ``/callback`` with ``error=...``: 400 + error HTML; records error and
      shuts down.
    * Any other path (``/``, ``/favicon.ico``, etc.): 404. The result is NOT
      modified, ``result_event`` is NOT set, and the server keeps running.
    """

    # Populated via the partial in ``_make_handler``. The class attributes
    # exist purely to satisfy the type checker.
    _expected_state: str
    _result_holder: dict[str, Any]
    _result_event: threading.Event
    _shutdown_callback: Any

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Suppress the default "GET /callback ..." stderr noise.
        return

    def handle_one_request(self) -> None:
        # Suppress broken-pipe / reset-by-peer races where the browser closes
        # before we finish writing the response.
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path != "/callback":
            self._send_404()
            return

        query_string = self.path.split("?", 1)[-1] if "?" in self.path else ""
        params = parse_qs(query_string)

        returned_state = params.get("state", [None])[0]
        code = params.get("code", [None])[0]
        error = params.get("error", [None])[0]
        error_description = params.get("error_description", [None])[0]

        if returned_state != self._expected_state:
            self._result_holder["error"] = "Invalid state parameter. Possible CSRF attack."
            self._send_simple_response(400, _ERROR_HTML)
            self._signal_done()
            return

        if error:
            self._result_holder["error"] = error_description or error
            self._send_simple_response(400, _ERROR_HTML)
            self._signal_done()
            return

        if not code:
            self._result_holder["error"] = "No authorization code received."
            self._send_simple_response(400, _ERROR_HTML)
            self._signal_done()
            return

        self._result_holder["code"] = code
        self._result_holder["state"] = returned_state
        self._send_simple_response(200, _SUCCESS_HTML)
        self._signal_done()

    def _send_simple_response(self, status: int, body: bytes) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _send_404(self) -> None:
        body = b"Not Found"
        try:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _signal_done(self) -> None:
        self._result_event.set()
        # Run shutdown in a background thread because ``shutdown()`` blocks
        # until ``serve_forever`` returns and we are currently inside a
        # request executed from that loop.
        threading.Thread(target=self._shutdown_callback, daemon=True).start()


def _make_handler_factory(
    *,
    expected_state: str,
    result_holder: dict[str, Any],
    result_event: threading.Event,
    shutdown_callback: Any,
) -> Any:
    def factory(*args: Any, **kwargs: Any) -> _OAuthCallbackHandler:
        # Bind state onto the instance via a subclass to avoid the
        # ``__init__`` ordering quirks of ``BaseHTTPRequestHandler``.
        cls = type(
            "_BoundOAuthCallbackHandler",
            (_OAuthCallbackHandler,),
            {
                "_expected_state": expected_state,
                "_result_holder": result_holder,
                "_result_event": result_event,
                "_shutdown_callback": staticmethod(shutdown_callback),
            },
        )
        instance: _OAuthCallbackHandler = cls(*args, **kwargs)
        return instance

    return factory


class OAuthCallbackServer:
    """Local HTTP server that receives the OAuth authorization-code redirect.

    Bind host is hard-coded to ``127.0.0.1`` (loopback) to avoid Windows
    Firewall prompts and keep the redirect URI host aligned with the bind
    host. Pass ``port=0`` to let the OS pick an ephemeral port; the
    actually-bound port is then exposed via :attr:`port`.
    """

    def __init__(self, *, expected_state: str, port: int = LOCAL_CALLBACK_PORT) -> None:
        self._expected_state = expected_state
        self._requested_port = port
        self._port = port
        self._httpd: _LoopbackHTTPServer | None = None
        self._serve_thread: threading.Thread | None = None
        self._result: dict[str, Any] = {}
        self._started_event = threading.Event()
        self._failed_event = threading.Event()
        self._result_event = threading.Event()
        self._shutdown_lock = threading.Lock()
        self._shutdown_done = False

    # ----- Properties -------------------------------------------------------

    @property
    def port(self) -> int:
        return self._port

    @property
    def started_event(self) -> threading.Event:
        return self._started_event

    @property
    def result_event(self) -> threading.Event:
        return self._result_event

    @property
    def result(self) -> dict[str, Any]:
        return self._result

    # ----- Lifecycle --------------------------------------------------------

    def start(self) -> None:
        """Bind the listener and start serving in a background thread.

        Blocks until the socket is bound (or bind fails). Raises ``OSError``
        if binding fails — does NOT let the worker thread leak the
        exception to its top level (which would print a traceback).
        """
        bind_error: list[BaseException] = []

        def _serve() -> None:
            try:
                server = _LoopbackHTTPServer(
                    (LOCAL_CALLBACK_HOST, self._requested_port),
                    _make_handler_factory(
                        expected_state=self._expected_state,
                        result_holder=self._result,
                        result_event=self._result_event,
                        shutdown_callback=self._inner_shutdown,
                    ),
                )
            except (OSError, OverflowError) as exc:
                bind_error.append(exc)
                self._failed_event.set()
                self._started_event.set()
                return

            self._httpd = server
            self._port = server.server_port
            self._started_event.set()
            try:
                server.serve_forever()
            except Exception as exc:  # pragma: no cover - defensive
                _callback_logger.debug("serve_forever raised: %r", exc, exc_info=True)
            finally:
                try:
                    server.server_close()
                except Exception:  # pragma: no cover - defensive
                    _callback_logger.debug("server_close raised", exc_info=True)

        thread = threading.Thread(target=_serve, daemon=True)
        thread.start()
        self._serve_thread = thread

        # Wait for either bind success or bind failure.
        self._started_event.wait()
        if self._failed_event.is_set() and bind_error:
            raise bind_error[0]

    async def shutdown(self) -> None:
        """Stop the listener and join the worker thread.

        Idempotent. Safe to call from async code — the blocking join runs in
        a worker thread.
        """
        await asyncio.to_thread(self._sync_shutdown)

    def _inner_shutdown(self) -> None:
        # Called from the request handler when a terminal callback arrives.
        with self._shutdown_lock:
            if self._shutdown_done:
                return
            self._shutdown_done = True
            httpd = self._httpd
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:  # pragma: no cover - defensive
                _callback_logger.debug("inner shutdown failed", exc_info=True)

    def _sync_shutdown(self) -> None:
        with self._shutdown_lock:
            already_done = self._shutdown_done
            self._shutdown_done = True
            httpd = self._httpd
        if httpd is not None and not already_done:
            try:
                httpd.shutdown()
            except Exception:  # pragma: no cover - defensive
                _callback_logger.debug("sync shutdown failed", exc_info=True)
        thread = self._serve_thread
        if thread is not None:
            thread.join(timeout=2.0)

    # ----- Helpers ----------------------------------------------------------

    def get_redirect_uri(self) -> str:
        return f"http://{LOCAL_CALLBACK_HOST}:{self._port}/callback"

    def wait_for_result(self, timeout: float | None) -> bool:
        if self._result_event.wait(timeout=timeout):
            return True

        timeout_desc = f"{int(timeout)}s" if timeout else "the configured timeout"
        self._result["error"] = (
            f"Timed out waiting for the login callback after {timeout_desc}. "
            "If your browser completed login, check firewall/antivirus settings "
            "and re-run 'arcade login' (you can increase --timeout if needed)."
        )
        self._inner_shutdown()
        return False


@contextmanager
def oauth_callback_server(
    *, expected_state: str, port: int = LOCAL_CALLBACK_PORT
) -> Iterator[OAuthCallbackServer]:
    """Synchronous context manager wrapping :class:`OAuthCallbackServer`.

    Used by the CLI; tests should generally instantiate the server directly.
    """
    server = OAuthCallbackServer(expected_state=expected_state, port=port)
    server.start()
    try:
        yield server
    finally:
        server._sync_shutdown()
