from arcade.core.errors import (
    RetryableToolError,
    ThirdPartyApiError,
    ThirdPartyApiRateLimitError,
    ThirdPartyApiServerError,
    ToolExecutionError,
    ToolRuntimeError,
)

__all__ = [
    "SDKError",
    "WeightError",
    "ToolRuntimeError",
    "ToolExecutionError",
    "RetryableToolError",
    "ThirdPartyApiError",
    "ThirdPartyApiRateLimitError",
    "ThirdPartyApiServerError",
]


class SDKError(Exception):
    """Base class for all SDK errors."""


class WeightError(SDKError):
    """Raised when the critic weights do not abide by SDK weight constraints."""
