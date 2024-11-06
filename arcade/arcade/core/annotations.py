from dataclasses import dataclass


@dataclass(frozen=True)
class Inferrable:
    """An annotation indicating that a parameter can be inferred by a model (default: True)."""

    value: bool = True
