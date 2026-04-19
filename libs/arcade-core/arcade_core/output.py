#
# ⚠️  DO NOT ADD NEW "LEAK-TO-AGENT" TOGGLES IN THIS FILE.
# ----------------------------------------------------------------------------
# The two env vars declared below (ARCADE_UNSAFE_DEBUG_LEAK_DEVELOPER_MESSAGE_
# TO_AGENT and ARCADE_UNSAFE_DEBUG_LEAK_STACKTRACE_TO_AGENT) intentionally
# bypass the safety boundary between `developer_message` / `stacktrace` (server
# -side, possibly containing paths, tokens, PII, internal state) and `message`
# (sent verbatim to the model and often to end users).
#
# They exist ONLY for local debugging of tool authors working on their own
# toolkits. They:
#   * have deliberately ugly, long names so nobody types them by accident,
#   * require a specific magic acknowledgement string — not `true`, not `1` —
#     to avoid being flipped on by generic "enable all debug flags" scripts,
#   * log a loud WARNING the first time they are read as enabled,
#   * are documented ONLY in CLAUDE.md, not in public READMEs.
#
# If you find yourself wanting to add a third such flag: don't. Put the debug
# info in logs (`logger.debug`) or in a dedicated diagnostic endpoint instead.
# Anything appended to `ToolCallError.message` WILL be shipped to the model
# and, for most tools, also shown to an end user in some UI.
#
from __future__ import annotations

import logging
import os
from typing import Any, TypeVar

from pydantic import BaseModel

from arcade_core.errors import ErrorKind
from arcade_core.schema import ToolCallError, ToolCallLog, ToolCallOutput
from arcade_core.utils import coerce_empty_list_to_none

T = TypeVar("T")

_logger = logging.getLogger(__name__)

# Acknowledgement string a developer must set as the env value. Picked to be
# impossible to set by mistake — no sane config management or CI will ever
# emit this string.
_DEBUG_LEAK_MAGIC = "yes-i-accept-leaking-internals-to-the-agent"

_ENV_LEAK_DEVELOPER_MESSAGE = "ARCADE_UNSAFE_DEBUG_LEAK_DEVELOPER_MESSAGE_TO_AGENT"
_ENV_LEAK_STACKTRACE = "ARCADE_UNSAFE_DEBUG_LEAK_STACKTRACE_TO_AGENT"

# Track one-shot warning state per flag. The rejection warning (truthy but
# not the magic string) and the activation warning (magic string set) are
# tracked in *separate* sets so that fixing a misconfigured flag within the
# same process still fires the critical activation warning.
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
                "acknowledgement string. Flag remains OFF. See arcade_core/output.py.",
                env_var,
            )
        return False
    if env_var not in _warned_activated:
        _warned_activated.add(env_var)
        _logger.warning(
            "%s is ENABLED. Tool error internals will be appended to agent-facing "
            "messages. This can leak paths, tokens, or PII to the model and any "
            "downstream UI. DO NOT USE IN PRODUCTION.",
            env_var,
        )
    return True


def _augment_message_for_debug(
    message: str,
    developer_message: str | None,
    stacktrace: str | None,
) -> str:
    extras: list[str] = []
    if developer_message and _leak_enabled(_ENV_LEAK_DEVELOPER_MESSAGE):
        extras.append(f"developer_message: {developer_message}")
    if stacktrace and _leak_enabled(_ENV_LEAK_STACKTRACE):
        extras.append(f"stacktrace:\n{stacktrace}")
    if not extras:
        return message
    return f"{message}\n\n[DEBUG] " + "\n\n[DEBUG] ".join(extras)


class ToolOutputFactory:
    """
    Singleton pattern for unified return method from tools.
    """

    def success(
        self,
        *,
        data: T | None = None,
        logs: list[ToolCallLog] | None = None,
    ) -> ToolCallOutput:
        # Extract the result value
        """
        Extracts the result value for the tool output.

        The executor guarantees that `data` is either a string, a dict, or None.
        """
        value: str | int | float | bool | dict | list | None
        if data is None:
            value = ""
        elif hasattr(data, "result"):
            result = getattr(data, "result", "")
            # Handle None result the same way as None data
            if result is None:
                value = ""
            # If the result is a BaseModel (e.g., from TypedDict conversion), convert to dict
            elif isinstance(result, BaseModel):
                value = result.model_dump()
            # If the result is a list, check if it contains BaseModel objects
            elif isinstance(result, list):
                value = [
                    item.model_dump() if isinstance(item, BaseModel) else item for item in result
                ]
            else:
                value = result
        elif isinstance(data, BaseModel):
            value = data.model_dump()
        elif isinstance(data, (str, int, float, bool, list, dict)):
            value = data
        else:
            raise ValueError(f"Unsupported data output type: {type(data)}")

        logs = coerce_empty_list_to_none(logs)
        return ToolCallOutput(
            value=value,
            logs=logs,
        )

    def fail(
        self,
        *,
        message: str,
        developer_message: str | None = None,
        stacktrace: str | None = None,
        logs: list[ToolCallLog] | None = None,
        additional_prompt_content: str | None = None,
        retry_after_ms: int | None = None,
        kind: ErrorKind = ErrorKind.UNKNOWN,
        can_retry: bool = False,
        status_code: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> ToolCallOutput:
        if not message or not message.strip():
            message = "Unspecified error during tool execution"
        message = _augment_message_for_debug(message, developer_message, stacktrace)
        return ToolCallOutput(
            error=ToolCallError(
                message=message,
                developer_message=developer_message,
                can_retry=can_retry,
                additional_prompt_content=additional_prompt_content,
                retry_after_ms=retry_after_ms,
                stacktrace=stacktrace,
                kind=kind,
                status_code=status_code,
                extra=extra,
            ),
            logs=coerce_empty_list_to_none(logs),
        )

    def fail_retry(
        self,
        *,
        message: str,
        developer_message: str | None = None,
        additional_prompt_content: str | None = None,
        retry_after_ms: int | None = None,
        stacktrace: str | None = None,
        logs: list[ToolCallLog] | None = None,
        kind: ErrorKind = ErrorKind.TOOL_RUNTIME_RETRY,
        status_code: int = 500,
        extra: dict[str, Any] | None = None,
    ) -> ToolCallOutput:
        """
        DEPRECATED: Use ToolOutputFactory.fail instead.
        This method will be removed in version 3.0.0
        """
        if not message or not message.strip():
            message = "Unspecified error during tool execution"
        message = _augment_message_for_debug(message, developer_message, stacktrace)
        return ToolCallOutput(
            error=ToolCallError(
                message=message,
                developer_message=developer_message,
                can_retry=True,
                additional_prompt_content=additional_prompt_content,
                retry_after_ms=retry_after_ms,
                stacktrace=stacktrace,
                kind=kind,
                status_code=status_code,
                extra=extra,
            ),
            logs=coerce_empty_list_to_none(logs),
        )


output_factory = ToolOutputFactory()
