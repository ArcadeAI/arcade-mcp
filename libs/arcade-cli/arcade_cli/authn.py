"""
OAuth authentication module for Arcade CLI.

This module is a thin CLI-shaped facade over :mod:`arcade_core.oauth_login`,
which holds the actual OAuth 2.0 + PKCE primitives. The CLI keeps:

* ``perform_oauth_login`` — synchronous orchestration tied to ``webbrowser``,
  status callbacks, and ``ARCADE_LOGIN_TIMEOUT_SECONDS``.
* ``_open_browser`` — Windows tiered helper to avoid CMD-window flash.
* Credentials helpers used by other CLI modules (``check_existing_login``,
  ``get_active_context``, ``_credentials_file_contains_legacy``).
* Sync wrappers around the async core primitives so existing CLI call sites
  (``connect.py``, ``main.py``, ``org.py``, ``project.py``) can stay sync.
* Sync ``fetch_organizations`` / ``fetch_projects`` (these use the locally
  stored access token rather than a fresh OAuth code, so they live here).

Re-exports from :mod:`arcade_core.oauth_login`: constants
(``LOCAL_CALLBACK_HOST``, ``LOCAL_CALLBACK_PORT``, ``DEFAULT_SCOPES``,
``DEFAULT_OAUTH_TIMEOUT_SECONDS``), models (``OrgInfo``, ``ProjectInfo``,
``WhoAmIResponse``), errors (``OAuthLoginError``, ``NoOrgsError``,
``NoProjectsError``), and the listener (``OAuthCallbackServer``,
``oauth_callback_server``).
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import uuid
import webbrowser
from dataclasses import dataclass
from typing import Any, Callable

import httpx
import yaml
from arcade_core.auth_tokens import (
    CLIConfig,
    TokenResponse,
    fetch_cli_config,
    get_valid_access_token,
)
from arcade_core.constants import CREDENTIALS_FILE_PATH
from arcade_core.oauth_login import (
    DEFAULT_OAUTH_TIMEOUT_SECONDS,
    DEFAULT_SCOPES,
    LOCAL_CALLBACK_HOST,
    LOCAL_CALLBACK_PORT,
    NoOrgsError,
    NoProjectsError,
    OAuthCallbackServer,
    OAuthLoginError,
    OrgInfo,
    ProjectInfo,
    WhoAmIResponse,
    oauth_callback_server,
    validate_whoami_org_project,
)
from arcade_core.oauth_login import (
    exchange_code_for_tokens as _async_exchange_code_for_tokens,
)
from arcade_core.oauth_login import (
    fetch_whoami as _async_fetch_whoami,
)
from arcade_core.oauth_login import (
    generate_authorization_url as _core_generate_authorization_url,
)
from arcade_core.oauth_login import (
    save_credentials_from_whoami as _async_save_credentials_from_whoami,
)
from arcade_core.subprocess_utils import build_windows_hidden_startupinfo

from arcade_cli.console import console

logger = logging.getLogger(__name__)


__all__ = [
    "DEFAULT_OAUTH_TIMEOUT_SECONDS",
    "DEFAULT_SCOPES",
    "LOCAL_CALLBACK_HOST",
    "LOCAL_CALLBACK_PORT",
    "NoOrgsError",
    "NoProjectsError",
    "OAuthCallbackServer",
    "OAuthLoginError",
    "OAuthLoginResult",
    "OrgInfo",
    "ProjectInfo",
    "WhoAmIResponse",
    "_credentials_file_contains_legacy",
    "_open_browser",
    "build_coordinator_url",
    "check_existing_login",
    "exchange_code_for_tokens",
    "fetch_cli_config",
    "fetch_organizations",
    "fetch_projects",
    "fetch_whoami",
    "generate_authorization_url",
    "get_active_context",
    "get_valid_access_token",
    "oauth_callback_server",
    "perform_oauth_login",
    "save_credentials_from_whoami",
    "select_default_org",
    "select_default_project",
    "validate_whoami_org_project",
]


# ---------------------------------------------------------------------------
# Sync shims around the async core primitives.
# ---------------------------------------------------------------------------


def generate_authorization_url(
    cli_config: CLIConfig,
    redirect_uri: str,
    state: str,
) -> tuple[str, str]:
    """Synchronous wrapper around :func:`arcade_core.oauth_login.generate_authorization_url`."""
    return _core_generate_authorization_url(cli_config, redirect_uri, state)


def exchange_code_for_tokens(
    cli_config: CLIConfig,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> TokenResponse:
    """Synchronous wrapper around the async core token-exchange primitive."""
    return asyncio.run(
        _async_exchange_code_for_tokens(cli_config, code, redirect_uri, code_verifier)
    )


def fetch_whoami(coordinator_url: str, access_token: str) -> WhoAmIResponse:
    """Synchronous wrapper around the async core ``fetch_whoami``."""
    return asyncio.run(_async_fetch_whoami(coordinator_url, access_token))


def save_credentials_from_whoami(
    tokens: TokenResponse,
    whoami: WhoAmIResponse,
    coordinator_url: str,
) -> None:
    """Synchronous wrapper around the async core ``save_credentials_from_whoami``."""
    asyncio.run(_async_save_credentials_from_whoami(tokens, whoami, coordinator_url))


# ---------------------------------------------------------------------------
# Org/project selection helpers (kept here as CLI-facing utilities).
# ---------------------------------------------------------------------------


def select_default_org(orgs: list[OrgInfo]) -> OrgInfo | None:
    """Return the default org, the first org, or None if empty."""
    if not orgs:
        return None
    for org in orgs:
        if org.is_default:
            return org
    return orgs[0]


def select_default_project(projects: list[ProjectInfo]) -> ProjectInfo | None:
    """Return the default project, the first project, or None if empty."""
    if not projects:
        return None
    for project in projects:
        if project.is_default:
            return project
    return projects[0]


# ---------------------------------------------------------------------------
# Coordinator REST helpers used outside the OAuth login flow.
# ---------------------------------------------------------------------------


def fetch_organizations(coordinator_url: str) -> list[OrgInfo]:
    """Fetch the organizations the current user belongs to.

    Uses the locally cached access token from credentials.yaml — this is
    distinct from :func:`fetch_whoami`, which is part of the OAuth flow and
    is invoked with a freshly issued access token.
    """
    url = f"{coordinator_url}/api/v1/orgs"
    access_token = get_valid_access_token(coordinator_url)
    response = httpx.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [OrgInfo.model_validate(item) for item in data.get("data", {}).get("items", [])]


def fetch_projects(coordinator_url: str, org_id: str) -> list[ProjectInfo]:
    """Fetch the projects in an organization."""
    url = f"{coordinator_url}/api/v1/orgs/{org_id}/projects"
    access_token = get_valid_access_token(coordinator_url)
    response = httpx.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [ProjectInfo.model_validate(item) for item in data.get("data", {}).get("items", [])]


# ---------------------------------------------------------------------------
# Credentials inspection helpers.
# ---------------------------------------------------------------------------


def get_active_context() -> tuple[str, str]:
    """Return the active ``(org_id, project_id)`` tuple from credentials.

    Raises:
        ValueError: If not logged in or no context is set.
    """
    from arcade_core.config_model import Config

    try:
        config = Config.load_from_file()
    except FileNotFoundError:
        raise ValueError("Not logged in. Please run 'arcade login' first.")

    if not config.context:
        raise ValueError("No active organization/project. Please run 'arcade login' first.")

    return config.context.org_id, config.context.project_id


def _credentials_file_contains_legacy() -> bool:
    """Detect legacy (API key) credentials in the credentials file."""
    try:
        with open(CREDENTIALS_FILE_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            cloud = data.get("cloud", {})
            return isinstance(cloud, dict) and "api" in cloud
    except Exception:
        return False


def check_existing_login(suppress_message: bool = False) -> bool:
    """Check whether the user is already logged in.

    Args:
        suppress_message: If True, suppress the "already logged in" message.

    Returns:
        True if the user is already logged in, False otherwise.
    """
    if not os.path.exists(CREDENTIALS_FILE_PATH):
        return False

    try:
        with open(CREDENTIALS_FILE_PATH, encoding="utf-8") as f:
            config_data: dict[str, Any] = yaml.safe_load(f)

        cloud_config = config_data.get("cloud", {}) if isinstance(config_data, dict) else {}

        auth = cloud_config.get("auth", {})
        if auth.get("access_token"):
            email = cloud_config.get("user", {}).get("email", "unknown")
            context = cloud_config.get("context", {})
            org_name = context.get("org_name", "unknown")
            project_name = context.get("project_name", "unknown")

            if not suppress_message:
                console.print(f"You're already logged in as {email}.", style="bold green")
                console.print(f"Active: {org_name} / {project_name}", style="dim")
            return True

    except yaml.YAMLError:
        console.print(
            f"Error: Invalid configuration file at {CREDENTIALS_FILE_PATH}", style="bold red"
        )
    except Exception as e:
        console.print(f"Error: Unable to read configuration file: {e!s}", style="bold red")

    return False


# ---------------------------------------------------------------------------
# Browser-launch helper (Windows tiered approach).
# ---------------------------------------------------------------------------


def _open_browser(url: str) -> bool:
    """Open a URL in the default browser without flashing a CMD window on Windows.

    On Windows, both ``webbrowser.open`` and ``os.startfile`` call
    ``ShellExecuteW`` under the hood which can briefly flash a console window
    depending on how the default-browser handler is registered.

    This helper uses a tiered approach on Windows:

    1. **ctypes ShellExecuteW** — calls the Win32 API directly so we can
       pass ``SW_SHOWNORMAL`` explicitly.  No intermediate ``cmd.exe``
       involved, so no console window should appear.
    2. **rundll32 url.dll** — a well-known Windows technique to open URLs
       via a pure-GUI helper DLL.  ``rundll32.exe`` is a GUI subsystem
       binary so it never allocates a console.  Used as a fallback when
       ctypes is unavailable or ShellExecuteW returns an error code.
    3. **webbrowser.open** — stdlib last-resort fallback.

    On non-Windows platforms this simply delegates to ``webbrowser.open``.
    """
    if sys.platform != "win32":
        try:
            return webbrowser.open(url)
        except Exception:
            return False

    # --- Windows path ---

    # Attempt 1: ctypes ShellExecuteW — most direct, avoids any console.
    try:
        import ctypes

        SW_SHOWNORMAL = 1
        result = ctypes.windll.shell32.ShellExecuteW(
            None,  # hwnd
            "open",  # operation
            url,  # file/URL
            None,  # parameters
            None,  # directory
            SW_SHOWNORMAL,
        )
        # ShellExecuteW returns > 32 on success.
        if result > 32:
            return True
    except Exception as exc:
        logger.debug("_open_browser: ShellExecuteW failed: %s", exc)

    # Attempt 2: rundll32 url.dll — a GUI-subsystem binary, no console.
    try:
        startupinfo = build_windows_hidden_startupinfo()
        popen_kwargs: dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if startupinfo is not None:
            popen_kwargs["startupinfo"] = startupinfo

        subprocess.Popen(["rundll32", "url.dll,FileProtocolHandler", url], **popen_kwargs)  # noqa: S607
    except Exception as exc:
        logger.debug("_open_browser: rundll32 fallback failed: %s", exc)
    else:
        return True

    # Attempt 3: stdlib fallback.
    try:
        return webbrowser.open(url)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# OAuth login orchestration.
# ---------------------------------------------------------------------------


@dataclass
class OAuthLoginResult:
    """Result of a successful OAuth login flow."""

    tokens: TokenResponse
    whoami: WhoAmIResponse

    @property
    def email(self) -> str:
        return self.whoami.email

    @property
    def selected_org(self) -> OrgInfo | None:
        return self.whoami.get_selected_org()

    @property
    def selected_project(self) -> ProjectInfo | None:
        return self.whoami.get_selected_project()


def build_coordinator_url(host: str, port: int | None) -> str:
    """Build a Coordinator URL from host and optional port."""
    if port:
        scheme = "http" if host == "localhost" else "https"
        return f"{scheme}://{host}:{port}"
    else:
        scheme = "http" if host == "localhost" else "https"
        default_port = ":8000" if host == "localhost" else ""
        return f"{scheme}://{host}{default_port}"


def perform_oauth_login(
    coordinator_url: str,
    on_status: Callable[[str], None] | None = None,
    callback_timeout_seconds: int | None = None,
) -> OAuthLoginResult:
    """
    Perform the complete OAuth login flow.

    1. Fetch OAuth config from the Coordinator.
    2. Start a local callback server.
    3. Open a browser for user authentication.
    4. Exchange the authorization code for tokens.
    5. Fetch user info and validate that an org and project exist.

    Args:
        coordinator_url: Base URL of the Coordinator.
        on_status: Optional callback for status messages.
        callback_timeout_seconds: Optional timeout for the local callback server.

    Returns:
        OAuthLoginResult with tokens and user info.

    Raises:
        OAuthLoginError: If any step of the login flow fails.
    """

    def status(msg: str) -> None:
        if on_status:
            on_status(msg)

    # Step 1: Fetch OAuth config.
    try:
        cli_config = fetch_cli_config(coordinator_url)
    except Exception as e:
        raise OAuthLoginError(f"Could not connect to Arcade at {coordinator_url}") from e

    state = str(uuid.uuid4())

    timeout_seconds = (
        callback_timeout_seconds
        if callback_timeout_seconds is not None
        else DEFAULT_OAUTH_TIMEOUT_SECONDS
    )
    if timeout_seconds <= 0:
        timeout_seconds = DEFAULT_OAUTH_TIMEOUT_SECONDS

    # Step 2: Start local callback server and run browser auth.
    try:
        with oauth_callback_server(expected_state=state) as server:
            redirect_uri = server.get_redirect_uri()

            # Step 3: Generate authorization URL and open browser.
            auth_url, code_verifier = generate_authorization_url(cli_config, redirect_uri, state)

            status("Opening a browser to log you in...")
            browser_opened = _open_browser(auth_url)

            if not browser_opened:
                status(
                    "Could not open a browser automatically.\n"
                    f"Open this link to log in:\n{auth_url}"
                )

            status(f"Waiting for login to complete (timeout: {timeout_seconds}s)...")
            server.wait_for_result(timeout_seconds)
    except OAuthLoginError:
        raise
    except Exception as e:
        raise OAuthLoginError(str(e)) from e

    # Check for errors from callback.
    if "error" in server.result:
        raise OAuthLoginError(f"Login failed: {server.result['error']}")

    if "code" not in server.result:
        raise OAuthLoginError("No authorization code received")

    # Step 4: Exchange code for tokens.
    code = server.result["code"]
    tokens = exchange_code_for_tokens(cli_config, code, redirect_uri, code_verifier)

    # Step 5: Fetch user info.
    whoami = fetch_whoami(coordinator_url, tokens.access_token)

    # Validate org/project exist (raises NoOrgsError / NoProjectsError, both
    # subclasses of OAuthLoginError, with messages matching the legacy CLI
    # wording).
    validate_whoami_org_project(whoami)

    return OAuthLoginResult(tokens=tokens, whoami=whoami)
