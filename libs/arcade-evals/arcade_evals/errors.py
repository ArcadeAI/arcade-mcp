__all__ = [
    "EvalError",
    "WeightError",
]


class EvalError(Exception):
    """Base class for all evaluation errors."""


class WeightError(EvalError):
    """Raised when the critic weights do not abide by evaluation weight constraints."""
