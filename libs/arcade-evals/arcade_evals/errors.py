__all__ = [
    "EvalError",
    "JudgeError",
    "WeightError",
]


class EvalError(Exception):
    """Base class for all evaluation errors."""


class JudgeError(EvalError):
    """Raised when a judge backend call fails (caller falls back to the next tier)."""


class WeightError(EvalError):
    """Raised when the critic weights do not abide by evaluation weight constraints."""
