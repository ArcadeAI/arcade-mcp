"""
MCP Settings Management

Provides Pydantic-based settings with validation and environment variable support.
"""

import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class NotificationSettings(BaseSettings):
    """Notification-related settings."""

    rate_limit_per_minute: int = Field(
        default=60,
        description="Maximum notifications per minute per client",
        ge=1,
        le=1000,
    )
    default_debounce_ms: int = Field(
        default=100,
        description="Default debounce time in milliseconds",
        ge=0,
        le=10000,
    )
    max_queued_notifications: int = Field(
        default=1000,
        description="Maximum queued notifications per client",
        ge=10,
        le=10000,
    )

    model_config = {"env_prefix": "MCP_NOTIFICATION_"}


class TransportSettings(BaseSettings):
    """Transport-related settings."""

    session_timeout_seconds: int = Field(
        default=300,
        description="Session timeout in seconds",
        ge=30,
        le=3600,
    )
    cleanup_interval_seconds: int = Field(
        default=10,
        description="Cleanup interval in seconds",
        ge=1,
        le=60,
    )
    max_sessions: int = Field(
        default=1000,
        description="Maximum concurrent sessions",
        ge=1,
        le=10000,
    )
    max_queue_size: int = Field(
        default=1000,
        description="Maximum queue size per session",
        ge=10,
        le=10000,
    )

    model_config = {"env_prefix": "MCP_TRANSPORT_"}


class ServerSettings(BaseSettings):
    """Server-related settings."""

    name: str = Field(
        default="ArcadeMCP",
        description="Server name",
    )
    version: str = Field(
        default="0.1.0dev",
        description="Server version",
    )
    title: str | None = Field(
        default="ArcadeMCP",
        description="Server title for display",
    )
    instructions: str | None = Field(
        default=(
            "ArcadeMCP provides access to a wide range of tools and toolkits."
            "Use 'tools/list' to see available tools and 'tools/call' to execute them."
        ),
        description="Server instructions for clients",
    )

    model_config = {"env_prefix": "MCP_SERVER_"}


class ResourceServerSettings(BaseSettings):
    """Settings for ResourceServer configuration via environment variables."""

    canonical_url: str | None = Field(
        default=None,
        description="Canonical URL of this MCP server (e.g., https://mcp.example.com/mcp)",
    )
    authorization_servers: list[dict[str, Any]] | None = Field(
        default=None,
        description="JSON array of authorization server entries."
        'Example: \'[{"authorization_server_url":"https://auth.example.com","issuer":"https://auth.example.com","jwks_uri":"https://auth.example.com/oauth2/jwks","algorithm":"RS256"}]\'',
    )

    @field_validator("authorization_servers", mode="before")
    @classmethod
    def parse_authorization_servers(cls, v: Any) -> list[dict[str, Any]] | None:
        """Parse JSON array from environment variable."""
        if v is None:
            return None
        if isinstance(v, str):
            import json

            try:
                parsed = json.loads(v)
                if not isinstance(parsed, list):
                    raise TypeError("authorization_servers must be a JSON array")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in authorization_servers: {e}") from e
            else:
                return parsed
        if isinstance(v, list):
            return v
        return None

    def to_authorization_server_entries(self) -> list[Any]:
        """Convert settings to list of AuthorizationServerEntry objects."""
        if not self.authorization_servers:
            return []

        from arcade_mcp_server.resource_server import (
            AccessTokenValidationOptions,
            AuthorizationServerEntry,
        )

        return [
            AuthorizationServerEntry(
                authorization_server_url=config["authorization_server_url"],
                issuer=config["issuer"],
                jwks_uri=config["jwks_uri"],
                algorithm=config.get("algorithm", "RS256"),
                expected_audiences=config.get("expected_audiences"),
                validation_options=AccessTokenValidationOptions(
                    verify_exp=config.get("validation_options", {}).get("verify_exp", True),
                    verify_iat=config.get("validation_options", {}).get("verify_iat", True),
                    verify_iss=config.get("validation_options", {}).get("verify_iss", True),
                    verify_nbf=config.get("validation_options", {}).get("verify_nbf", True),
                    leeway=config.get("validation_options", {}).get("leeway", 0),
                ),
            )
            for config in self.authorization_servers
        ]

    model_config = {"env_prefix": "MCP_RESOURCE_SERVER_"}


class MiddlewareSettings(BaseSettings):
    """Middleware-related settings."""

    enable_logging: bool = Field(
        default=True,
        description="Enable logging middleware",
    )
    log_level: str = Field(
        default="INFO",
        description="Log level",
    )
    enable_error_handling: bool = Field(
        default=True,
        description="Enable error handling middleware",
    )
    mask_error_details: bool = Field(
        default=False,
        description="Mask error details in production",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v

    model_config = {"env_prefix": "MCP_MIDDLEWARE_"}


class ArcadeSettings(BaseSettings):
    """Arcade-specific settings."""

    api_key: str | None = Field(
        default=None,
        description="Arcade API key",
    )
    api_url: str = Field(
        default="https://api.arcade.dev",
        description="Arcade API URL",
    )
    auth_disabled: bool = Field(
        default=False,
        description="Disable authentication",
    )
    server_secret: str | None = Field(
        default=None,
        description="Server secret for worker endpoints (required to enable worker routes)",
        validation_alias="ARCADE_WORKER_SECRET",
    )
    environment: str = Field(
        default="dev",
        description="Environment (dev or prod.)",
    )
    user_id: str | None = Field(
        default=None,
        description="User ID for Arcade environment",
    )

    model_config = {"env_prefix": "ARCADE_"}


class ToolEnvironmentSettings(BaseSettings):
    """Tool environment settings.

    Every environment variable that is not prefixed
    with one of the prefixes for the other settings
    will be added to the tool environment as an
    available tool secret in the ToolContext
    """

    tool_environment: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool environment",
    )

    def model_post_init(self, __context: Any) -> None:
        """Populate tool_environment from process env if not provided."""
        if not self.tool_environment:
            excluded_prefixes = ("MCP_", "_")
            self.tool_environment = {
                key: value
                for key, value in os.environ.items()
                if not any(key.startswith(prefix) for prefix in excluded_prefixes)
            }

    model_config = {
        "env_prefix": "",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow",
    }


class MCPSettings(BaseSettings):
    """Main MCP settings container."""

    # Sub-settings
    notification: NotificationSettings = Field(
        default_factory=NotificationSettings,
        description="Notification settings",
    )
    transport: TransportSettings = Field(
        default_factory=TransportSettings,
        description="Transport settings",
    )
    server: ServerSettings = Field(
        default_factory=ServerSettings,
        description="Server settings",
    )
    resource_server: ResourceServerSettings = Field(
        default_factory=ResourceServerSettings,
        description="Server authentication settings",
    )
    middleware: MiddlewareSettings = Field(
        default_factory=MiddlewareSettings,
        description="Middleware settings",
    )
    arcade: ArcadeSettings = Field(
        default_factory=ArcadeSettings,
        description="Arcade integration settings",
    )
    tool_environment: ToolEnvironmentSettings = Field(
        default_factory=ToolEnvironmentSettings,
        description="Tool environment settings",
    )

    # Global settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    model_config = {
        "env_prefix": "MCP_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow",
    }

    @classmethod
    def from_env(cls) -> "MCPSettings":
        """Create settings from environment variables.

        Automatically loads .env file from current directory if it exists,
        then creates settings from the combined environment.

        The .env file is loaded with override=False, meaning existing
        environment variables take precedence. Multiple calls are safe
        """
        from dotenv import load_dotenv

        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)

        return cls()

    def tool_secrets(self) -> dict[str, Any]:
        """Get tool secrets."""
        return self.tool_environment.tool_environment

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary."""
        return self.model_dump(exclude_unset=True)


# Global settings instance
settings = MCPSettings.from_env()
