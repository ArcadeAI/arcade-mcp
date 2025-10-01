"""Entry point for detached usage tracking subprocess.

This module is invoked as `python -m arcade_cli.usage` and expects
event data to be passed via the ARCADE_USAGE_EVENT_DATA environment variable.
"""

import json
import os
import threading

from posthog import Posthog


def _timeout_exit() -> None:
    """Force exit after timeout"""
    os._exit(1)


def main() -> None:
    """Capture a PostHog event from environment variable."""

    timeout_timer = threading.Timer(10.0, _timeout_exit)
    timeout_timer.daemon = True
    timeout_timer.start()

    try:
        event_data = json.loads(os.environ["ARCADE_USAGE_EVENT_DATA"])

        posthog = Posthog(
            project_api_key=event_data["api_key"],
            host=event_data["host"],
            timeout=5,
            max_retries=1,
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
