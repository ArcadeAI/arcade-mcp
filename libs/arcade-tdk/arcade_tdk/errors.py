from arcade_core.errors import (
    ContextRequiredToolError,
    FatalToolError,
    RetryableToolError,
    ToolExecutionError,
    ToolRuntimeError,
    UpstreamError,
    UpstreamRateLimitError,
)

__all__ = [
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
    """Base class for all SDK errors."""


class WeightError(SDKError):
    """Raised when the critic weights do not abide by SDK weight constraints."""
