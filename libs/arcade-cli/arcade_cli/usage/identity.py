"""
Identity management for PostHog analytics tracking.

Handles anonymous/authenticated identity tracking with PostHog aliasing,
supporting pre-login anonymous tracking, post-login identity stitching,
and logout identity rotation.
"""

import contextlib
import fcntl
import json
import os
import tempfile
import uuid
from typing import Any

import yaml
from arcade_cli.constants import ARCADE_CONFIG_PATH, CREDENTIALS_FILE_PATH


class UsageIdentity:
    """Manages user identity for PostHog analytics tracking."""

    def __init__(self) -> None:
        self.usage_file_path = os.path.join(ARCADE_CONFIG_PATH, "usage.json")
        self._data: dict[str, Any] | None = None

    def load_or_create(self) -> dict[str, Any]:
        """Load or create usage.json file with atomic writes and file locking.

        Returns:
            dict: The usage data containing anon_id and optionally linked_email
        """
        if self._data is not None:
            return self._data

        os.makedirs(ARCADE_CONFIG_PATH, exist_ok=True)

        if os.path.exists(self.usage_file_path):
            try:
                with open(self.usage_file_path) as f:
                    # lock file
                    if os.name != "nt":  # Unix-like systems
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        data = json.load(f)
                        # validate usage file
                        if isinstance(data, dict) and "anon_id" in data:
                            self._data = data
                            return self._data
                    finally:
                        # unlock file
                        if os.name != "nt":
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception:  # noqa: S110
                pass

        new_data = {"anon_id": str(uuid.uuid4()), "linked_email": None}

        self._write_atomic(new_data)
        self._data = new_data
        return self._data

    def _write_atomic(self, data: dict[str, Any]) -> None:
        """Write data atomically using temp file and rename.

        Args:
            data: The data to write to the usage file
        """
        temp_fd, temp_path = tempfile.mkstemp(
            dir=ARCADE_CONFIG_PATH, prefix=".usage_", suffix=".tmp"
        )

        try:
            with os.fdopen(temp_fd, "w") as f:
                # lock file
                if os.name != "nt":  # Unix-like systems
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # ensure data is written to disk
                finally:
                    if os.name != "nt":
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            os.rename(temp_path, self.usage_file_path)
        except Exception:
            # clean up
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise

    def get_distinct_id(self) -> str:
        """Get distinct_id based on authentication state.

        Returns:
            str: Email if authenticated, otherwise anon_id
        """
        data = self.load_or_create()
        email = self.get_email()

        if email:
            return email
        return data["anon_id"]

    def get_email(self) -> str | None:
        """Read email from credentials.yaml file.

        Returns:
            str | None: User email if authenticated, None otherwise
        """
        if not os.path.exists(CREDENTIALS_FILE_PATH):
            return None

        try:
            with open(CREDENTIALS_FILE_PATH) as f:
                config = yaml.safe_load(f)

            cloud_config = config.get("cloud", {})
            email = cloud_config.get("user", {}).get("email")

        except Exception:
            return None
        else:
            return email if email else None

    def should_alias(self) -> bool:
        """Check if PostHog alias is needed.

        Alias is needed is the user is authenticated (has email in credentials.yaml),
        but the email doesn't match linked_email (in usage.json)

        Returns:
            bool: True if user is authenticated but not yet aliased
        """
        data = self.load_or_create()
        email = self.get_email()

        return email is not None and email != data.get("linked_email")

    def rotate_anon_id(self) -> None:
        """Generate new anonymous ID and clear linked email.

        Used after logout to prevent cross-contamination between multiple
        accounts on the same machine
        """
        data = self.load_or_create()
        data["anon_id"] = str(uuid.uuid4())
        data["linked_email"] = None

        self._write_atomic(data)
        self._data = data

    def set_linked_email(self, email: str) -> None:
        """Update linked_email in usage.json.

        Args:
            email: The email to link to the current anon_id
        """
        data = self.load_or_create()
        data["linked_email"] = email

        self._write_atomic(data)
        self._data = data

    @property
    def anon_id(self) -> str:
        """Get the current anonymous ID.

        Returns:
            str: The anonymous ID
        """
        data = self.load_or_create()
        return data["anon_id"]
