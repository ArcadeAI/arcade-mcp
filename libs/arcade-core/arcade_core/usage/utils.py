import os

from arcade_core.usage.constants import ARCADE_USAGE_TRACKING


def is_tracking_enabled() -> bool:
    """Check if usage tracking is enabled via environment variable.

    Returns:
        bool: True if tracking is enabled (default), False if explicitly disabled.
    """
    value = os.environ.get(ARCADE_USAGE_TRACKING, "1")
    return value.lower() not in ("false", "0", "no", "off")
