"""Entry point for detached usage tracking subprocess.

This module is invoked as `python -m arcade_core.usage` and expects
event data to be passed via the ARCADE_USAGE_EVENT_DATA environment variable.
"""

import json
import os
import threading

from posthog import Posthog

from arcade_core.usage.constants import (
    ARCADE_USAGE_EVENT_DATA,
    MAX_RETRIES_POSTHOG,
    PROP_PROCESS_PERSON_PROFILE,
    TIMEOUT_POSTHOG_CAPTURE,
    TIMEOUT_SUBPROCESS_EXIT,
)


def _timeout_exit() -> None:
    """Force exit after timeout"""
    os._exit(1)


def main() -> None:
    """Capture a PostHog event from environment variable."""

    timeout_timer = threading.Timer(TIMEOUT_SUBPROCESS_EXIT, _timeout_exit)
    timeout_timer.daemon = True
    timeout_timer.start()

    try:
        event_data = json.loads(os.environ[ARCADE_USAGE_EVENT_DATA])

        if event_data.get("is_anon", False):
            event_data["properties"][PROP_PROCESS_PERSON_PROFILE] = False

        posthog = Posthog(
            project_api_key=event_data["api_key"],
            host=event_data["host"],
            timeout=TIMEOUT_POSTHOG_CAPTURE,
            max_retries=MAX_RETRIES_POSTHOG,
        )

        posthog.capture(
            event_data["event_name"],
            distinct_id=event_data["distinct_id"],
            properties=event_data["properties"],
        )

        posthog.flush()

        timeout_timer.cancel()
    except Exception:
        # Silent failure. We don't want to disrupt anything
        timeout_timer.cancel()
        pass


if __name__ == "__main__":
    main()
