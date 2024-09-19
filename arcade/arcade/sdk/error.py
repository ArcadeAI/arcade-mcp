class SDKError(Exception):
    """Base class for all SDK errors."""


class WeightError(SDKError):
    """Raised when the critic weights do not abide by SDK weight constraints."""
