import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

logger = logging.getLogger(__name__)


def _set_windows_owner_acl(config_file_path: Path) -> None:
    """Restrict a file so only the current user can read/write it on Windows.

    On POSIX systems ``chmod 600`` removes group/other access.  On Windows,
    ``Path.chmod()`` only toggles the read-only flag and does **not** change
    who can access the file.  To get equivalent protection we use the built-in
    ``icacls`` command to manipulate NTFS Access Control Lists (ACLs):

    1. ``/inheritance:r`` — remove all inherited Access Control Entries (ACEs).
       By default every file inherits broad permissions from its parent folder
       (e.g. ``Users:(RX)``).  Stripping inheritance leaves the file with an
       empty ACL, meaning *no one* can access it yet.
    2. ``/grant:r USERNAME:(R,W)`` — add a single explicit ACE that grants
       the current user Read and Write access.  The ``:r`` flag replaces any
       existing ACE for that user rather than merging.

    Both flags are passed in a **single** ``icacls`` invocation so there is no
    window where the file has an empty ACL (which would make it temporarily
    inaccessible to everyone, including the owner).

    The net effect is that only the logged-in Windows user can read or modify
    the credentials file — the same security posture as ``chmod 600`` on Unix.
    """
    username = os.environ.get("USERNAME")
    if not username:
        raise OSError("USERNAME is not set; cannot apply Windows ACL restrictions")

    # Strip inherited permissions and grant only the current user R+W access in
    # a single icacls call.  Using two separate calls would leave the file with
    # an empty ACL (nobody can access it) between the first and second call; if
    # the second call were to fail the file would be permanently inaccessible.
    subprocess.run(
        [  # noqa: S607
            "icacls",
            str(config_file_path),
            "/inheritance:r",
            "/grant:r",
            f"{username}:(R,W)",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


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

        config_data = yaml.safe_load(config_file_path.read_text(encoding="utf-8"))

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
        config_file_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

        # Restrict the credentials file so only the current user can read it.
        # - Unix:    chmod 600 (removes group/other access via file-mode bits).
        # - Windows: icacls to strip inherited ACEs and grant only the current
        #            user R/W access (see _set_windows_owner_acl for details).
        # Failure is non-fatal: the file is still written, but a warning is
        # logged so the user knows the permissions could not be tightened.
        try:
            if os.name == "nt":
                _set_windows_owner_acl(config_file_path)
            else:
                config_file_path.chmod(0o600)
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning(
                "Unable to apply restrictive permissions to %s: %s",
                config_file_path,
                exc,
            )
