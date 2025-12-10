"""
OAuth authentication module for Arcade CLI.

Implements OAuth 2.0 Authorization Code flow with PKCE for secure CLI authentication.
Uses authlib for OAuth protocol handling.
"""

import os
import secrets
import threading
import uuid
import webbrowser
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs

import httpx
import yaml
from arcade_core.auth_tokens import (
    CLIConfig,
    TokenResponse,
    fetch_cli_config,
    get_valid_access_token,
)
from arcade_core.config_model import AuthConfig, Config, ContextConfig, UserConfig
from arcade_core.constants import ARCADE_CONFIG_PATH, CREDENTIALS_FILE_PATH
from authlib.integrations.httpx_client import OAuth2Client
from jinja2 import Environment, FileSystemLoader
from pydantic import AliasChoices, BaseModel, Field
from rich.console import Console

# Set up Jinja2 templates
_TEMPLATES_DIR = Path(__file__).parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR), autoescape=True)


def _render_template(template_name: str, **context: Any) -> bytes:
    """Render a Jinja2 template and return as bytes."""
    template = _jinja_env.get_template(template_name)
    return template.render(**context).encode("utf-8")


console = Console()

# OAuth constants
DEFAULT_SCOPES = "openid offline_access"
LOCAL_CALLBACK_PORT = 9905


def create_oauth_client(cli_config: CLIConfig) -> OAuth2Client:  # type: ignore[no-any-unimported]
    """
    Create an authlib OAuth2Client configured for the CLI.

    Args:
        cli_config: OAuth configuration from Coordinator

    Returns:
        Configured OAuth2Client with PKCE support
    """
    return OAuth2Client(
        client_id=cli_config.client_id,
        token_endpoint=cli_config.token_endpoint,
        code_challenge_method="S256",
    )


def generate_authorization_url(  # type: ignore[no-any-unimported]
    client: OAuth2Client,
    cli_config: CLIConfig,
    redirect_uri: str,
    state: str,
) -> tuple[str, str]:
    """
    Generate OAuth authorization URL with PKCE.

    Args:
        client: OAuth2Client instance
        cli_config: OAuth configuration from Coordinator
        redirect_uri: Callback URL for the authorization response
        state: Random state for CSRF protection

    Returns:
        Tuple of (authorization_url, code_verifier)
    """
    # Generate PKCE code verifier
    code_verifier = secrets.token_urlsafe(64)

    url, _ = client.create_authorization_url(
        cli_config.authorization_endpoint,
        redirect_uri=redirect_uri,
        scope=DEFAULT_SCOPES,
        state=state,
        code_verifier=code_verifier,
    )
    return url, code_verifier


def exchange_code_for_tokens(  # type: ignore[no-any-unimported]
    client: OAuth2Client,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> TokenResponse:
    """
    Exchange authorization code for tokens using authlib.

    Args:
        client: OAuth2Client instance
        code: Authorization code from callback
        redirect_uri: Same redirect URI used in authorization request
        code_verifier: PKCE code verifier from authorization request

    Returns:
        TokenResponse with access and refresh tokens
    """
    token = client.fetch_token(
        client.session.metadata["token_endpoint"],
        grant_type="authorization_code",
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
    )

    return TokenResponse(
        access_token=token["access_token"],
        refresh_token=token["refresh_token"],
        expires_in=token["expires_in"],
        token_type=token["token_type"],
    )


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


def select_default_org(orgs: list[OrgInfo]) -> OrgInfo | None:
    """
    Select the default organization.

    Args:
        orgs: List of organizations

    Returns:
        Default org, or first org, or None if empty
    """
    if not orgs:
        return None
    for org in orgs:
        if org.is_default:
            return org
    return orgs[0]


def select_default_project(projects: list[ProjectInfo]) -> ProjectInfo | None:
    """
    Select the default project.

    Args:
        projects: List of projects

    Returns:
        Default project, or first project, or None if empty
    """
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
        """Get the org to use: default if available, otherwise first in list."""
        return select_default_org(self.organizations)

    def get_selected_project(self) -> ProjectInfo | None:
        """Get the project to use: default if available, otherwise first in list."""
        return select_default_project(self.projects)


def fetch_whoami(coordinator_url: str, access_token: str) -> WhoAmIResponse:
    """
    Fetch user info and all orgs/projects from the Coordinator.

    This is the preferred way to get user info after OAuth login, as it:
    - Only accepts short-lived access tokens (not API keys)
    - Returns user email and account ID
    - Returns all orgs and projects the user has access to

    Args:
        coordinator_url: Base URL of the Coordinator
        access_token: Valid OAuth access token

    Returns:
        WhoAmIResponse with account info and all orgs/projects
    """
    url = f"{coordinator_url}/api/v1/auth/whoami"
    response = httpx.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json().get("data", {})

    return WhoAmIResponse.model_validate(data)


def fetch_organizations(coordinator_url: str) -> list[OrgInfo]:
    """
    Fetch organizations the user belongs to.

    Args:
        coordinator_url: Base URL of the Coordinator
        access_token: Valid access token

    Returns:
        List of organizations
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
    """
    Fetch projects in an organization.

    Args:
        coordinator_url: Base URL of the Coordinator
        access_token: Valid access token
        org_id: Organization ID

    Returns:
        List of projects
    """
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


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    def __init__(self, *args, state: str, result_holder: dict, **kwargs):  # type: ignore[no-untyped-def]
        self.state = state
        self.result_holder = result_holder
        # Store error details for template rendering
        self._error: str | None = None
        self._error_description: str | None = None
        self._returned_state: str | None = None
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Suppress logging to stdout
        pass

    def do_GET(self) -> None:
        """Handle GET request (OAuth callback)."""
        query_string = self.path.split("?", 1)[-1] if "?" in self.path else ""
        params = parse_qs(query_string)

        self._returned_state = params.get("state", [None])[0]
        code = params.get("code", [None])[0]
        self._error = params.get("error", [None])[0]
        self._error_description = params.get("error_description", [None])[0]

        if self._returned_state != self.state:
            self.result_holder["error"] = "Invalid state parameter. Possible CSRF attack."
            self._send_error_response(
                message="Invalid state parameter. This may be a security issue."
            )
            return

        if self._error:
            self.result_holder["error"] = self._error_description or self._error
            self._send_error_response()
            return

        if not code:
            self.result_holder["error"] = "No authorization code received."
            self._send_error_response(message="No authorization code was received from the server.")
            return

        self.result_holder["code"] = code
        self._send_success_response()

    def _send_success_response(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_render_template("cli_login_success.jinja"))
        threading.Thread(target=self.server.shutdown).start()

    def _send_error_response(self, message: str | None = None) -> None:
        self.send_response(400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            _render_template(
                "cli_login_failed.jinja",
                message=message,
                error=self._error,
                error_description=self._error_description,
                state=self._returned_state,
            )
        )
        threading.Thread(target=self.server.shutdown).start()


class OAuthCallbackServer:
    """Local HTTP server for OAuth callback."""

    def __init__(self, state: str, port: int = LOCAL_CALLBACK_PORT):
        self.state = state
        self.port = port
        self.httpd: HTTPServer | None = None
        self.result: dict[str, Any] = {}

    def run_server(self) -> None:
        """Start the callback server."""
        server_address = ("", self.port)
        handler = lambda *args, **kwargs: OAuthCallbackHandler(
            *args, state=self.state, result_holder=self.result, **kwargs
        )
        self.httpd = HTTPServer(server_address, handler)
        self.httpd.serve_forever()

    def shutdown_server(self) -> None:
        """Shut down the callback server."""
        if self.httpd:
            self.httpd.shutdown()

    def get_redirect_uri(self) -> str:
        """Get the redirect URI for this server."""
        return f"http://localhost:{self.port}/callback"


def save_credentials_from_whoami(
    tokens: TokenResponse,
    whoami: WhoAmIResponse,
    coordinator_url: str,
) -> None:
    """
    Save OAuth credentials to the config file using WhoAmI response.

    Picks the org/project marked as default, or falls back to the first one
    in the list if none are marked as default.

    Args:
        tokens: OAuth tokens
        whoami: Response from /whoami endpoint with user and orgs/projects
    """
    # Ensure config directory exists
    os.makedirs(ARCADE_CONFIG_PATH, exist_ok=True)

    expires_at = datetime.now() + timedelta(seconds=tokens.expires_in)

    context = None
    selected_org = whoami.get_selected_org()
    selected_project = whoami.get_selected_project()

    if selected_org and selected_project:
        context = ContextConfig(
            org_id=selected_org.org_id,
            org_name=selected_org.name,
            project_id=selected_project.project_id,
            project_name=selected_project.name,
        )

    config = Config(
        coordinator_url=coordinator_url,
        auth=AuthConfig(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_at=expires_at,
        ),
        user=UserConfig(email=whoami.email),
        context=context,
    )

    config.save_to_file()


def get_active_context() -> tuple[str, str]:
    """
    Get the active org and project IDs.

    Returns:
        Tuple of (org_id, project_id)

    Raises:
        ValueError: If not logged in or no context set
    """
    try:
        config = Config.load_from_file()
    except FileNotFoundError:
        raise ValueError("Not logged in. Please run 'arcade login' first.")

    if not config.context:
        raise ValueError("No active organization/project. Please run 'arcade login' first.")

    return config.context.org_id, config.context.project_id


# =============================================================================
# High-level OAuth login flow
# =============================================================================


class OAuthLoginError(Exception):
    """Error during OAuth login flow."""

    pass


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
    """
    Build the Coordinator URL from host and optional port.

    Args:
        host: The Arcade Coordinator host
        port: Optional port (used for local development)

    Returns:
        Full coordinator URL (e.g., https://api.arcade.dev)
    """
    if port:
        scheme = "http" if host == "localhost" else "https"
        return f"{scheme}://{host}:{port}"
    else:
        scheme = "http" if host == "localhost" else "https"
        default_port = ":8000" if host == "localhost" else ""
        return f"{scheme}://{host}{default_port}"


@contextmanager
def oauth_callback_server(state: str) -> Generator[OAuthCallbackServer, None, None]:
    """
    Context manager for the OAuth callback server.

    Ensures the server is properly shut down even if an error occurs.
    Waits for the callback to be received before exiting.

    Usage:
        with oauth_callback_server(state) as server:
            # server is running and waiting for callback
            ...
        # After the with block, the server has received the callback
    """
    server = OAuthCallbackServer(state)
    server_thread = threading.Thread(target=server.run_server)
    server_thread.start()
    try:
        yield server
        # Wait for the callback to be received (server shuts itself down after handling)
        server_thread.join()
    finally:
        # Clean up if interrupted or if something went wrong
        if server_thread.is_alive():
            server.shutdown_server()
            server_thread.join(timeout=2)


def perform_oauth_login(
    coordinator_url: str,
    on_status: Callable[[str], None] | None = None,
) -> OAuthLoginResult:
    """
    Perform the complete OAuth login flow.

    This function:
    1. Fetches OAuth config from the Coordinator
    2. Starts a local callback server
    3. Opens browser for user authentication
    4. Exchanges authorization code for tokens
    5. Fetches user info and validates org/project

    Args:
        coordinator_url: Base URL of the Coordinator
        on_status: Optional callback for status messages (e.g., console.print)

    Returns:
        OAuthLoginResult with tokens and user info

    Raises:
        OAuthLoginError: If any step of the login flow fails
    """

    def status(msg: str) -> None:
        if on_status:
            on_status(msg)

    # Step 1: Fetch OAuth config
    try:
        cli_config = fetch_cli_config(coordinator_url)
    except Exception as e:
        raise OAuthLoginError(f"Could not connect to Arcade at {coordinator_url}") from e

    # Step 2: Create OAuth client and prepare PKCE
    oauth_client = create_oauth_client(cli_config)
    state = str(uuid.uuid4())

    # Step 3: Start local callback server and run browser auth
    with oauth_callback_server(state) as server:
        redirect_uri = server.get_redirect_uri()

        # Step 4: Generate authorization URL and open browser
        auth_url, code_verifier = generate_authorization_url(
            oauth_client, cli_config, redirect_uri, state
        )

        status("Opening a browser to log you in...")
        if not webbrowser.open(auth_url):
            status(f"Copy this URL into your browser:\n{auth_url}")

        # Step 5: Wait for callback (server thread handles this via serve_forever)
        # The thread will exit when the callback handler calls server.shutdown()

    # Check for errors from callback
    if "error" in server.result:
        raise OAuthLoginError(f"Login failed: {server.result['error']}")

    if "code" not in server.result:
        raise OAuthLoginError("No authorization code received")

    # Step 6: Exchange code for tokens
    code = server.result["code"]
    tokens = exchange_code_for_tokens(oauth_client, code, redirect_uri, code_verifier)

    # Step 7: Fetch user info
    whoami = fetch_whoami(coordinator_url, tokens.access_token)

    # Validate org/project exist
    if not whoami.get_selected_org():
        raise OAuthLoginError(
            "No organizations found for your account. "
            "Please contact support@arcade.dev for assistance."
        )

    if not whoami.get_selected_project():
        org_name = whoami.get_selected_org().name  # type: ignore[union-attr]
        raise OAuthLoginError(
            f"No projects found in organization '{org_name}'. "
            "Please contact support@arcade.dev for assistance."
        )

    return OAuthLoginResult(tokens=tokens, whoami=whoami)


def _credentials_file_contains_legacy() -> bool:
    """
    Detect legacy (API key) credentials in the credentials file.
    """
    try:
        with open(CREDENTIALS_FILE_PATH) as f:
            data = yaml.safe_load(f) or {}
            cloud = data.get("cloud", {})
            return isinstance(cloud, dict) and "api" in cloud
    except Exception:
        return False


def check_existing_login(suppress_message: bool = False) -> bool:
    """
    Check if the user is already logged in.

    Args:
        suppress_message: If True, suppress the logged in message.

    Returns:
        True if the user is already logged in, False otherwise.
    """
    if not os.path.exists(CREDENTIALS_FILE_PATH):
        return False

    try:
        with open(CREDENTIALS_FILE_PATH) as f:
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
