import json
import os
import subprocess
import sys


class UsageService:
    def __init__(self) -> None:
        self.api_key = "phc_g7OuFqZEAVwIgRdtnZkjvBpy9weQ1f9VJW6YP1SzQRF"
        self.host = "https://us.i.posthog.com"

    def alias(self, previous_id: str, distinct_id: str) -> None:
        """Perform PostHog alias synchronously (blocking).

        Must be called BEFORE the first event with the new distinct_id.
        This is done synchronously to guarantee ordering.

        Args:
            previous_id: The previous distinct_id (usually anon_id)
            distinct_id: The new distinct_id (usually email)
        """
        try:
            from posthog import Posthog

            posthog = Posthog(
                project_api_key=self.api_key,
                host=self.host,
                timeout=2,
                max_retries=1,
            )

            posthog.alias(previous_id=previous_id, distinct_id=distinct_id)
            posthog.flush()
        except Exception:  # noqa: S110
            # Silent failure - don't disrupt CLI
            pass

    def merge_dangerously(self, distinct_id: str, anon_distinct_id: str) -> None:
        """Merge anonymous user into existing user using $merge_dangerously.

        This bypasses merge restrictions for existing users who already have
        events associated with them. Used when alias would fail due to merge
        restrictions.

        Args:
            distinct_id: The authenticated user's ID (email)
            anon_distinct_id: The anonymous ID to merge into the authenticated user
        """
        try:
            from posthog import Posthog

            posthog = Posthog(
                project_api_key=self.api_key,
                host=self.host,
                timeout=2,  # Short timeout
                max_retries=1,
            )

            # Send a special event to force merge the users
            posthog.capture(
                distinct_id=distinct_id,
                event="$merge_dangerously",
                properties={"alias": anon_distinct_id},
            )
            posthog.flush()
        except Exception:
            # Silent failure - don't disrupt CLI
            pass

    def capture(self, event_name: str, distinct_id: str, properties: dict) -> None:
        """Capture event in a detached subprocess without blocking.

        Spawns a completely independent subprocess that continues running
        even after the parent CLI process exits. Works cross-platform.
        """
        event_data = json.dumps({
            "event_name": event_name,
            "properties": properties,
            "distinct_id": distinct_id,
            "api_key": self.api_key,
            "host": self.host,
        })

        cmd = [sys.executable, "-m", "arcade_cli.usage"]

        # Pass data to subprocess via environment variable
        env = os.environ.copy()
        env["ARCADE_USAGE_EVENT_DATA"] = event_data

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
