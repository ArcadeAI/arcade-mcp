import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError


class BaseConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")


class AuthConfig(BaseConfig):
    """
    OAuth authentication configuration.
    """

    access_token: str
    """
    OAuth access token (JWT).
    """
    refresh_token: str
    """
    OAuth refresh token for obtaining new access tokens.
    """
    expires_at: datetime
    """
    When the access token expires.
    """


class UserConfig(BaseConfig):
    """
    Arcade user configuration.
    """

    email: str | None = None
    """
    User email.
    """


class ContextConfig(BaseConfig):
    """
    Active organization and project context.
    """

    org_id: str
    """
    Active organization ID.
    """
    org_name: str
    """
    Active organization name.
    """
    project_id: str
    """
    Active project ID.
    """
    project_name: str
    """
    Active project name.
    """


class Config(BaseConfig):
    """
    Configuration for Arcade CLI.
    """

    coordinator_url: str | None = None
    """
    Base URL of the Arcade Coordinator used for authentication flows.
    """

    auth: AuthConfig | None = None
    """
    OAuth authentication configuration.
    """

    # Active org/project context
    context: ContextConfig | None = None
    """
    Active organization and project context.
    """

    # User info
    user: UserConfig | None = None
    """
    Arcade user configuration.
    """

    def __init__(self, **data: Any):
        super().__init__(**data)

    def is_authenticated(self) -> bool:
        """
        Check if the user is authenticated (has valid auth config).
        """
        return self.auth is not None

    def is_token_expired(self) -> bool:
        """
        Check if the access token is expired or will expire within 5 minutes.
        """
        if not self.auth:
            return True
        # Consider expired if less than 5 minutes remaining
        buffer_seconds = 300
        return datetime.now() >= self.auth.expires_at.replace(tzinfo=None) - timedelta(
            seconds=buffer_seconds
        )

    def get_access_token(self) -> str | None:
        """
        Get the current access token if available.
        """
        if self.auth:
            return self.auth.access_token
        return None

    def get_active_org_id(self) -> str | None:
        """
        Get the active organization ID.
        """
        if self.context:
            return self.context.org_id
        return None

    def get_active_project_id(self) -> str | None:
        """
        Get the active project ID.
        """
        if self.context:
            return self.context.project_id
        return None

    @classmethod
    def get_config_dir_path(cls) -> Path:
        """
        Get the path to the Arcade configuration directory.
        """
        config_path = os.getenv("ARCADE_WORK_DIR") or Path.home() / ".arcade"
        return Path(config_path).resolve()

    @classmethod
    def get_config_file_path(cls) -> Path:
        """
        Get the path to the Arcade configuration file.
        """
        return cls.get_config_dir_path() / "credentials.yaml"

    @classmethod
    def ensure_config_dir_exists(cls) -> None:
        """
        Create the configuration directory if it does not exist.
        """
        config_dir = Config.get_config_dir_path()
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_from_file(cls) -> "Config":
        """
        Load the configuration from the YAML file in the configuration directory.

        Returns:
            Config: The loaded configuration.

        Raises:
            FileNotFoundError: If no configuration file exists.
            ValueError: If the existing configuration file is invalid.
        """
        cls.ensure_config_dir_exists()

        config_file_path = cls.get_config_file_path()

        if not config_file_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found at {config_file_path}. "
                "Please run 'arcade login' to create your configuration."
            )

        config_data = yaml.safe_load(config_file_path.read_text())

        if config_data is None:
            raise ValueError(
                "Invalid credentials.yaml file. Please ensure it is a valid YAML file or "
                "run `arcade logout`, then `arcade login` to start from a clean slate."
            )

        if "cloud" not in config_data:
            raise ValueError(
                "Invalid credentials.yaml file. Expected a 'cloud' key. "
                "Run `arcade logout`, then `arcade login` to start from a clean slate."
            )

        try:
            return cls(**config_data["cloud"])
        except ValidationError as e:
            # Get only the errors with {type:missing} and combine them
            # into a nicely-formatted string message.
            missing_field_errors = [
                ".".join(map(str, error["loc"]))
                for error in e.errors()
                if error["type"] == "missing"
            ]
            other_errors = [str(error) for error in e.errors() if error["type"] != "missing"]

            missing_field_errors_str = ", ".join(missing_field_errors)
            other_errors_str = "\n".join(other_errors)

            pretty_str: str = "Invalid Arcade configuration."
            if missing_field_errors_str:
                pretty_str += f"\nMissing fields: {missing_field_errors_str}\n"
            if other_errors_str:
                pretty_str += f"\nOther errors:\n{other_errors_str}"

            raise ValueError(pretty_str) from e

    def save_to_file(self) -> None:
        """
        Save the configuration to the YAML file in the configuration directory.

        Sets file permissions to 600 (owner read/write only) for security.
        """
        Config.ensure_config_dir_exists()
        config_file_path = Config.get_config_file_path()

        # Convert to dict, excluding None values for cleaner output
        data = {"cloud": self.model_dump(exclude_none=True, mode="json")}
        config_file_path.write_text(yaml.dump(data, default_flow_style=False))

        # Set restrictive permissions (owner read/write only)
        config_file_path.chmod(0o600)
