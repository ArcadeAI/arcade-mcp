from arcade_core.errors import (
    ContextRequiredToolError,
    ErrorKind,
    FatalToolError,
    RetryableToolError,
    ToolExecutionError,
    ToolRuntimeError,
    UpstreamError,
    UpstreamRateLimitError,
)

__all__ = [
    "ErrorKind",
    "FatalToolError",
    "RetryableToolError",
    "SDKError",
    "ToolExecutionError",
    "ToolRuntimeError",
    "UpstreamError",
    "UpstreamRateLimitError",
    "ContextRequiredToolError",
    "WeightError",
]


class SDKError(Exception):
    """
    DEPRECATED: Base class for all SDK errors.

    SDKError is deprecated and will be removed in a future major version.
    """


class WeightError(SDKError):
    """Raised when the critic weights do not abide by SDK weight constraints."""
