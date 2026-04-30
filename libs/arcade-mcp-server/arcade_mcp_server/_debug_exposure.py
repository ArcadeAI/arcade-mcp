"""
Debug-only escape hatch for MCP tool error responses.

MCP clients typically render only the ``message`` field of a tool error
response, dropping ``developer_message`` and ``stacktrace``. That makes
server-side iteration painful when a tool is failing. The flags in this
module let a toolkit author opt in to appending those internals to the
``message`` field while debugging.

DEBUG-ONLY. Activating these flags can leak paths, tokens, or PII to
callers. Don't add more flags of this shape — put debug info in logs
instead.
"""

from __future__ import annotations

import logging
import os

_logger = logging.getLogger(__name__)

# Acknowledgement string a developer must set as the env value. Picked to be
# impossible to set by mistake — no sane config management or CI will ever
# emit this string.
_DEBUG_LEAK_MAGIC = "yes-i-accept-leaking-internals-to-the-agent"

_ENV_EXPOSE_DEVELOPER_MESSAGE = "ARCADE_DEBUG_EXPOSE_DEVELOPER_MESSAGE_IN_TOOL_ERROR_RESPONSES"
_ENV_EXPOSE_STACKTRACE = "ARCADE_DEBUG_EXPOSE_STACKTRACE_IN_TOOL_ERROR_RESPONSES"

# One-shot warning state per flag. The rejection warning (truthy but not the
# magic string) and the activation warning (magic string set) are tracked in
# *separate* sets so that fixing a misconfigured flag within the same process
# still fires the critical activation warning.
_warned_rejected: set[str] = set()
_warned_activated: set[str] = set()


def _leak_enabled(env_var: str) -> bool:
    raw = os.environ.get(env_var)
    if raw is None:
        return False
    if raw.strip() != _DEBUG_LEAK_MAGIC:
        # A value is set but it isn't the magic ack. Treat as off and, if it
        # looks like someone tried a boolean, nudge them via a log so the
        # silence isn't confusing.
        if raw.strip().lower() in {"1", "true", "yes", "on"} and env_var not in _warned_rejected:
            _warned_rejected.add(env_var)
            _logger.warning(
                "%s is set to a truthy value but not to the required "
                "acknowledgement string. Flag remains OFF. "
                "See arcade_mcp_server/_debug_exposure.py.",
                env_var,
            )
        return False
    if env_var not in _warned_activated:
        _warned_activated.add(env_var)
        _logger.warning(
            "%s is ENABLED. Tool error internals will be appended to the "
            "`message` field of MCP tool error responses. This can leak paths, "
            "tokens, or PII to callers. DO NOT USE IN PRODUCTION.",
            env_var,
        )
    return True


def augment_error_message_for_debug(
    message: str,
    developer_message: str | None,
    stacktrace: str | None,
) -> str:
    """Append debug internals to ``message`` when the corresponding env flags are set.

    This is a no-op in the default case (both flags off), and also a no-op when
    the flags are set to anything other than the activation ack string. See
    module docstring for the full rationale.
    """
    extras: list[str] = []
    if developer_message and _leak_enabled(_ENV_EXPOSE_DEVELOPER_MESSAGE):
        extras.append(f"developer_message: {developer_message}")
    if _leak_enabled(_ENV_EXPOSE_STACKTRACE):
        if stacktrace:
            extras.append(f"stacktrace:\n{stacktrace}")
        else:
            extras.append("stacktrace: unavailable (tool error payload did not include one)")
    if not extras:
        return message
    return f"{message}\n\n[DEBUG] " + "\n\n[DEBUG] ".join(extras)
