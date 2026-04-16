from arcade_core.errors import (
    ContextRequiredToolError,
    ErrorKind,
    FatalToolError,
    NetworkTransportError,
    RetryableToolError,
    ToolExecutionError,
    ToolRuntimeError,
    UpstreamError,
    UpstreamRateLimitError,
)

__all__ = [
    "ContextRequiredToolError",
    "ErrorKind",
    "FatalToolError",
    "NetworkTransportError",
    "RetryableToolError",
    "SDKError",
    "ToolExecutionError",
    "ToolRuntimeError",
    "UpstreamError",
    "UpstreamRateLimitError",
    "WeightError",
]


class SDKError(Exception):
    """
    DEPRECATED: Base class for all SDK errors.

    SDKError is deprecated and will be removed in a future major version.
    """


class WeightError(SDKError):
    """Raised when the critic weights do not abide by SDK weight constraints."""
