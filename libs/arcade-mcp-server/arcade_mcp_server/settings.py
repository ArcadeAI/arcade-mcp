"""
MCP Settings Management

Provides Pydantic-based settings with validation and environment variable support.
"""

import os
import tempfile
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


class DatacacheSettings(BaseSettings):
    """Datacache (DuckDB + S3 + Redis) settings."""

    storage_backend: str | None = Field(
        default=None,
        description="Datacache storage backend: 's3' or 'local' (required when datacache is enabled)",
    )
    redis_url: str | None = Field(
        default=None,
        description="Redis URL used for datacache locking (e.g. redis://localhost:6379/0)",
    )
    s3_bucket: str | None = Field(
        default=None,
        description="S3 bucket for storing datacache DuckDB files",
    )
    s3_prefix: str = Field(
        default="arcade/datacache",
        description="S3 key prefix for datacache DuckDB files",
    )
    aws_access_key_id: str | None = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: str | None = Field(default=None, description="AWS secret access key")
    aws_session_token: str | None = Field(default=None, description="AWS session token")
    aws_region: str | None = Field(default=None, description="AWS region")
    s3_endpoint_url: str | None = Field(
        default=None,
        description="Custom S3 endpoint URL (e.g. for MinIO)",
    )
    local_dir: str = Field(
        default_factory=lambda: os.path.join(tempfile.gettempdir(), "arcade_datacache"),
        description="Local directory for storing active datacache DuckDB files",
    )
    lock_ttl_seconds: int = Field(
        default=900,
        description="Redis lock TTL in seconds (safety to prevent deadlocks)",
        ge=1,
        le=86400,
    )
    lock_wait_seconds: int = Field(
        default=900,
        description="How long to wait to acquire the datacache lock before failing",
        ge=0,
        le=86400,
    )

    @field_validator("storage_backend")
    @classmethod
    def validate_storage_backend(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v_norm = v.strip().lower()
        if v_norm not in {"s3", "local"}:
            raise ValueError("ARCADE_DATACACHE_STORAGE_BACKEND must be one of: s3, local")
        return v_norm

    model_config = {"env_prefix": "ARCADE_DATACACHE_"}


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
            # IMPORTANT: do not leak server/runtime config into tool secrets.
            # In particular, ARCADE_DATACACHE_* can include credentials and endpoints.
            excluded_prefixes = ("MCP_", "_", "ARCADE_DATACACHE_")
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
    middleware: MiddlewareSettings = Field(
        default_factory=MiddlewareSettings,
        description="Middleware settings",
    )
    arcade: ArcadeSettings = Field(
        default_factory=ArcadeSettings,
        description="Arcade integration settings",
    )
    datacache: DatacacheSettings = Field(
        default_factory=DatacacheSettings,
        description="Datacache settings (DuckDB + S3 + Redis)",
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
        """Create settings from environment variables."""
        return cls()

    def tool_secrets(self) -> dict[str, Any]:
        """Get tool secrets."""
        return self.tool_environment.tool_environment

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary."""
        return self.model_dump(exclude_unset=True)


# Global settings instance
settings = MCPSettings.from_env()
