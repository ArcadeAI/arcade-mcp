import json
import os
import subprocess
import sys

from arcade_core.usage.constants import (
    ARCADE_USAGE_EVENT_DATA,
    MAX_RETRIES_POSTHOG,
    TIMEOUT_POSTHOG_ALIAS,
)
from arcade_core.usage.utils import is_tracking_enabled


class UsageService:
    def __init__(self) -> None:
        self.api_key = "phc_hIqUQyJpf2TP4COePO5jEpkGeUXipa7KqTEyDeRsTmB"
        self.host = "https://us.i.posthog.com"

    def alias(self, previous_id: str, distinct_id: str) -> None:
        """Perform PostHog alias synchronously (blocking).

        Must be called BEFORE the first event with the new distinct_id.
        This is done synchronously to guarantee ordering.

        Args:
            previous_id: The previous distinct_id (usually anon_id)
            distinct_id: The new distinct_id (usually email)
        """
        if not is_tracking_enabled():
            return

        try:
            from posthog import Posthog

            posthog = Posthog(
                project_api_key=self.api_key,
                host=self.host,
                timeout=TIMEOUT_POSTHOG_ALIAS,
                max_retries=MAX_RETRIES_POSTHOG,
            )

            posthog.alias(previous_id=previous_id, distinct_id=distinct_id)
            posthog.flush()
        except Exception:  # noqa: S110
            # Silent failure - don't disrupt CLI
            pass

    def capture(
        self, event_name: str, distinct_id: str, properties: dict, is_anon: bool = False
    ) -> None:
        """Capture event in a detached subprocess that is non-blocking.

        Spawns a completely independent subprocess that continues running
        even after the parent CLI process exits. Works cross-platform.

        Args:
            event_name: Name of the event to capture
            distinct_id: The distinct_id for the user
            properties: Event properties
            is_anon: Whether this is an anonymous user (sets $process_person_profile to false)
        """
        if not is_tracking_enabled():
            return

        event_data = json.dumps({
            "event_name": event_name,
            "properties": properties,
            "distinct_id": distinct_id,
            "api_key": self.api_key,
            "host": self.host,
            "is_anon": is_anon,
        })

        cmd = [sys.executable, "-m", "arcade_core.usage"]

        # Pass data via environment variable (works on all platforms)
        env = os.environ.copy()
        env[ARCADE_USAGE_EVENT_DATA] = event_data

        if sys.platform == "win32":
            # Windows: Use DETACHED_PROCESS to fully detach from parent console
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200

            subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
                env=env,
            )
        else:
            # Unix: Use start_new_session to detach from terminal
            subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
                env=env,
            )
