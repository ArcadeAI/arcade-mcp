from arcade_core.errors import RetryableToolError, ToolExecutionError, ToolRuntimeError

__all__ = [
    "RetryableToolError",
    "SDKError",
    "ToolExecutionError",
    "ToolRuntimeError",
    "WeightError",
]


class SDKError(Exception):
    """Base class for all SDK errors."""


class WeightError(SDKError):
    """Raised when the critic weights do not abide by SDK weight constraints."""
