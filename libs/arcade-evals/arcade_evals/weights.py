"""
Weight definitions and normalization for arcade-evals.

This module contains:
- FuzzyWeight enum for qualitative weight assignment
- Weight type alias (float | FuzzyWeight)
- Normalization functions for critic weights
- Validation utilities for weight constraints
"""

from enum import Enum
from typing import TYPE_CHECKING

from arcade_evals.errors import WeightError

if TYPE_CHECKING:
    from arcade_evals.critic import Critic


def _is_placeholder_critic(critic: "Critic") -> bool:
    """
    Check if a critic is a placeholder (like NoneCritic).

    Uses duck typing via the _is_placeholder class attribute to avoid
    circular imports between weights.py and critic.py.
    """
    return getattr(critic, "_is_placeholder", False)


class FuzzyWeight(Enum):
    """
    Qualitative weight buckets for critic importance.

    Instead of manually calculating float weights, use these qualitative
    buckets to express relative importance. Weights are auto-normalized
    using Softmax-inspired scaling.

    Example:
        >>> critics = [
        ...     BinaryCritic(critic_field="owner", weight=FuzzyWeight.HIGH),
        ...     BinaryCritic(critic_field="state", weight=FuzzyWeight.LOW),
        ... ]
        # HIGH (5) gets 62.5% weight, LOW (3) gets 37.5% weight

    Weight Buckets (linear scale, uniform increment of 1):
        - MINIMAL: 1 - Almost negligible, rarely affects outcome
        - VERY_LOW: 2 - Rarely important, edge case checking
        - LOW: 3 - Minor importance
        - MEDIUM: 4 - Standard importance (default)
        - HIGH: 5 - Important parameter
        - VERY_HIGH: 6 - Critical, must-match parameter
        - CRITICAL: 7 - Absolutely essential, highest priority
    """

    MINIMAL = 1
    VERY_LOW = 2
    LOW = 3
    MEDIUM = 4
    HIGH = 5
    VERY_HIGH = 6
    CRITICAL = 7


# Type alias for weight parameter
Weight = float | FuzzyWeight


def normalize_fuzzy_weights(critics: list["Critic"]) -> list[float]:
    """
    Normalize a list of critic weights to sum to 1.0.

    Uses Softmax-inspired normalization: each weight is divided by the
    sum of all weights, ensuring:
    1. All weights sum to exactly 1.0
    2. Relative proportions are preserved

    Args:
        critics: List of critics with weight attributes.
                 Weights can be float or FuzzyWeight.

    Returns:
        List of normalized float weights in the same order as input critics.

    Example:
        >>> from arcade_evals.critic import BinaryCritic
        >>> critics = [
        ...     BinaryCritic("a", FuzzyWeight.HIGH),
        ...     BinaryCritic("b", FuzzyWeight.LOW),
        ... ]
        >>> normalize_fuzzy_weights(critics)
        [0.625, 0.375]  # HIGH (5) / (5 + 3), LOW (3) / (5 + 3)
    """
    if not critics:
        return []

    # Extract raw weight values (convert FuzzyWeight to float)
    raw_weights: list[float] = []
    for critic in critics:
        if isinstance(critic.weight, FuzzyWeight):
            raw_weights.append(float(critic.weight.value))
        else:
            raw_weights.append(float(critic.weight))

    # Calculate total for normalization
    total = sum(raw_weights)
    if total <= 0:
        # Edge case: all weights are zero or negative
        # Return zeros to indicate no scoring should occur
        return [0.0] * len(critics)

    # Normalize weights (simple division by sum)
    return [w / total for w in raw_weights]


def resolve_weight(weight: Weight) -> float:
    """
    Resolve a Weight value to a float.

    Used when a single weight needs to be resolved without full normalization.

    Args:
        weight: Either a float or FuzzyWeight enum.

    Returns:
        Float weight value.
    """
    if isinstance(weight, FuzzyWeight):
        return weight.value
    return float(weight)


# =============================================================================
# Critic Weight Validation and Normalization
# =============================================================================


def validate_and_normalize_critic_weights(critics: list["Critic"]) -> None:
    """
    Validate and normalize critic weights in-place.

    If any critic uses FuzzyWeight, all weights are normalized using
    Softmax-inspired scaling to sum to 1.0. Otherwise, validates that
    all float weights are non-negative.

    This function modifies critics in-place, setting their `weight` attribute
    to the normalized float value. The original weight is preserved in
    `_original_weight` for FuzzyWeight critics.

    Args:
        critics: List of critics to validate and normalize.

    Raises:
        WeightError: If any float weight is negative.

    Example:
        >>> critics = [
        ...     BinaryCritic(critic_field="a", weight=FuzzyWeight.HIGH),
        ...     BinaryCritic(critic_field="b", weight=FuzzyWeight.LOW),
        ... ]
        >>> validate_and_normalize_critic_weights(critics)
        >>> critics[0].weight  # Now normalized float
        0.625
    """
    if not critics:
        return

    # Check if any critic uses FuzzyWeight
    has_fuzzy = any(isinstance(c.weight, FuzzyWeight) for c in critics)

    if has_fuzzy:
        _normalize_fuzzy_critic_weights(critics)
    else:
        _validate_float_critic_weights(critics)


def _normalize_fuzzy_critic_weights(critics: list["Critic"]) -> None:
    """
    Normalize critic weights when FuzzyWeight is used.

    Filters out placeholder critics (like NoneCritic, which always has weight=0)
    and normalizes the remaining critics' weights to sum to 1.0.

    Args:
        critics: List of critics to normalize (modified in-place).
    """
    # Filter out placeholder critics for normalization (they keep weight=0)
    non_placeholder_critics = [c for c in critics if not _is_placeholder_critic(c)]

    if not non_placeholder_critics:
        return

    normalized = normalize_fuzzy_weights(non_placeholder_critics)

    for critic, norm_weight in zip(non_placeholder_critics, normalized):
        # Store original weight for reference
        critic._original_weight = critic.weight  # type: ignore[attr-defined]
        # Set normalized weight for evaluation
        critic.weight = norm_weight


def _validate_float_critic_weights(critics: list["Critic"]) -> None:
    """
    Validate that all float critic weights are non-negative.

    This is the legacy validation path used when no FuzzyWeight is present.
    Float weights are allowed to be any non-negative value; normalization
    happens implicitly through the scoring calculation.

    Args:
        critics: List of critics to validate.

    Raises:
        WeightError: If any weight is negative.
    """
    for critic in critics:
        if _is_placeholder_critic(critic):
            continue

        weight = resolve_weight(critic.weight)
        if weight < 0:
            raise WeightError(f"Critic weight must be non-negative, got {weight}")
