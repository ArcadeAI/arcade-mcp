"""
Shared access-token utilities used by both the CLI and MCP server.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx
from pydantic import BaseModel

from arcade_core.config_model import Config
from arcade_core.constants import PROD_COORDINATOR_HOST


class CLIConfig(BaseModel):
    """OAuth configuration returned by the Coordinator."""

    client_id: str
    authorization_endpoint: str
    token_endpoint: str


class TokenResponse(BaseModel):
    """OAuth token response."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str


def fetch_cli_config(coordinator_url: str) -> CLIConfig:
    """Fetch OAuth configuration from the Coordinator."""
    url = f"{coordinator_url}/api/v1/auth/cli_config"
    response = httpx.get(url, timeout=30)
    response.raise_for_status()
    return CLIConfig.model_validate(response.json())


def refresh_access_token(
    cli_config: CLIConfig,
    refresh_token: str,
) -> TokenResponse:
    """Refresh the access token using authlib-compatible token endpoint."""
    response = httpx.post(
        cli_config.token_endpoint,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": cli_config.client_id,
        },
        timeout=30,
    )
    response.raise_for_status()
    token = response.json()
    return TokenResponse(
        access_token=token["access_token"],
        refresh_token=token.get("refresh_token", refresh_token),
        expires_in=token["expires_in"],
        token_type=token["token_type"],
    )


def get_valid_access_token(coordinator_url: str | None = None) -> str:
    """
    Get a valid access token, refreshing if necessary.

    Returns:
        Valid access token

    Raises:
        ValueError: If not logged in or token refresh fails
    """
    try:
        config = Config.load_from_file()
    except FileNotFoundError:
        raise ValueError("Not logged in. Please run 'arcade login' first.")

    resolved_coordinator_url = (
        coordinator_url
        or (config.coordinator_url if config.coordinator_url else None)
        or f"https://{PROD_COORDINATOR_HOST}"
    )

    if not config.auth:
        raise ValueError("Not logged in. Please run 'arcade login' first.")

    # Check if token needs refresh
    if config.is_token_expired():
        cli_config = fetch_cli_config(resolved_coordinator_url)

        try:
            new_tokens = refresh_access_token(cli_config, config.auth.refresh_token)
        except httpx.HTTPError as e:
            raise ValueError(
                f"Failed to refresh token: {e}. Please run 'arcade login' to re-authenticate."
            )

        # Update stored credentials
        expires_at = datetime.now() + timedelta(seconds=new_tokens.expires_in)
        config.coordinator_url = resolved_coordinator_url
        config.auth.access_token = new_tokens.access_token
        config.auth.refresh_token = new_tokens.refresh_token
        config.auth.expires_at = expires_at
        config.save_to_file()

        return new_tokens.access_token

    return config.auth.access_token
