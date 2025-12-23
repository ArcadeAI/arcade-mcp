"""
Identity management for PostHog analytics tracking.

Handles anonymous/authenticated identity tracking with PostHog aliasing,
supporting pre-login anonymous tracking, post-login identity stitching,
and logout identity rotation.
"""

import fcntl
import json
import os
import tempfile
import uuid
from typing import Any

import httpx
import yaml

from arcade_core.constants import ARCADE_CONFIG_PATH, CREDENTIALS_FILE_PATH
from arcade_core.usage.constants import (
    KEY_ANON_ID,
    KEY_LINKED_PRINCIPAL_ID,
    TIMEOUT_ARCADE_API,
    USAGE_FILE_NAME,
)


class UsageIdentity:
    """Manages user identity for PostHog analytics tracking."""

    def __init__(self) -> None:
        self.usage_file_path = os.path.join(ARCADE_CONFIG_PATH, USAGE_FILE_NAME)
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
                        if isinstance(data, dict) and KEY_ANON_ID in data:
                            self._data = data
                            return self._data
                    finally:
                        # unlock file
                        if os.name != "nt":
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception:  # noqa: S110
                pass

        new_data = {KEY_ANON_ID: str(uuid.uuid4()), KEY_LINKED_PRINCIPAL_ID: None}

        self._write_atomic(new_data)
        self._data = new_data
        return self._data

    def _write_atomic(self, data: dict[str, Any]) -> None:
        """Write data atomically to usage.json file

        Args:
            data: The data to write to the usage file
        """
        # Create temp file in same directory for atomic rename
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
            import contextlib

            with contextlib.suppress(OSError):
                os.unlink(temp_path)
            raise

    def get_distinct_id(self) -> str:
        """Get distinct_id based on authentication state.

        We use principal_id for authenticated users and anon_id for anonymous users.

        Returns:
            str: Principal ID if authenticated, otherwise anon_id
        """
        data = self.load_or_create()

        # Check if we have a persisted principal_id first
        linked_principal_id = data.get(KEY_LINKED_PRINCIPAL_ID)
        if linked_principal_id:
            return str(linked_principal_id)

        # Try to fetch principal_id from API if not persisted
        principal_id = self.get_principal_id()
        if principal_id:
            return principal_id

        # Fall back to anon_id if not authenticated
        return str(data[KEY_ANON_ID])

    def get_principal_id(self) -> str | None:
        """Fetch principal_id (account_id) from Arcade Cloud API.

        Prefers any linked principal already stored in usage.json. If not
        found, attempts to fetch via OAuth access token and falls
        back to legacy API key validation if present.

        Returns:
            str | None: Principal ID if authenticated and API call succeeds, None otherwise
        """
        # Prefer already-linked principal_id in usage.json
        data = self.load_or_create()
        linked_principal_id = data.get(KEY_LINKED_PRINCIPAL_ID)
        if linked_principal_id:
            return str(linked_principal_id)

        if not os.path.exists(CREDENTIALS_FILE_PATH):
            return None

        try:
            with open(CREDENTIALS_FILE_PATH) as f:
                config = yaml.safe_load(f) or {}

            cloud_config = config.get("cloud", {}) if isinstance(config, dict) else {}

            # Determine coordinator/authority URL for auth calls
            coordinator_url = cloud_config.get("coordinator_url") or "https://cloud.arcade.dev"
            whoami_url = f"{coordinator_url}/api/v1/auth/whoami"
            validate_url = f"{coordinator_url}/api/v1/auth/validate"

            # OAuth credentials: use access_token to call /whoami
            auth_config = cloud_config.get("auth", {}) if isinstance(cloud_config, dict) else {}
            access_token = auth_config.get("access_token")
            if access_token:
                response = httpx.get(
                    whoami_url,
                    headers={
                        "accept": "application/json",
                        "Authorization": f"Bearer {access_token}",
                    },
                    timeout=TIMEOUT_ARCADE_API,
                )
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    principal_id = data.get("account_id") or data.get("principal_id")
                    if principal_id:
                        return str(principal_id)

            # Legacy API key credentials (deprecated)
            api_key = (
                cloud_config.get("api", {}).get("key") if isinstance(cloud_config, dict) else None
            )
            if api_key:
                response = httpx.get(
                    validate_url,
                    headers={"accept": "application/json", "Authorization": f"Bearer {api_key}"},
                    timeout=TIMEOUT_ARCADE_API,
                )
                if response.status_code == 200:
                    data = response.json()
                    principal_id = data.get("data", {}).get("principal_id")
                    if principal_id:
                        return str(principal_id)

        except Exception:  # noqa: S110
            # Silent failure - don't disrupt CLI
            pass

        return None

    def should_alias(self) -> bool:
        """Check if PostHog alias is needed.

        Alias is needed when the user is authenticated,
        but the retrieved principal_id doesn't match the persisted linked_principal_id

        Returns:
            bool: True if user is authenticated but not yet aliased
        """
        data = self.load_or_create()
        principal_id = self.get_principal_id()

        return principal_id is not None and principal_id != data.get(KEY_LINKED_PRINCIPAL_ID)

    def reset_to_anonymous(self) -> None:
        """Generate new anonymous ID and clear linked principal_id.

        Used after logout to prevent cross-contamination between multiple
        accounts on the same machine
        """
        # Create fresh data with only anon_id
        new_data = {KEY_ANON_ID: str(uuid.uuid4()), KEY_LINKED_PRINCIPAL_ID: None}

        self._write_atomic(new_data)
        self._data = new_data

    def set_linked_principal_id(self, principal_id: str) -> None:
        """Update linked_principal_id in usage.json.

        Args:
            principal_id: The principal_id to link to the current anon_id
        """
        data = self.load_or_create()
        data[KEY_LINKED_PRINCIPAL_ID] = principal_id

        self._write_atomic(data)
        self._data = data

    @property
    def anon_id(self) -> str:
        """Get the current anonymous ID.

        Returns:
            str: The anonymous ID
        """
        data = self.load_or_create()
        return str(data[KEY_ANON_ID])
