"""Enum for :class:`SmartCritic` evaluation modes.

Kept in a standalone module so that :mod:`arcade_evals.smart_critic_prompts`
can import the enum without introducing a circular dependency with
:mod:`arcade_evals.smart_critic`.
"""

from __future__ import annotations

from enum import Enum


class SmartCriticMode(str, Enum):
    """Evaluation modes supported by :class:`SmartCritic`.

    Each non-``CUSTOM`` mode maps to a default criteria prompt that instructs
    the judge LLM how to score the (expected, actual) pair. ``CUSTOM`` leaves
    the criteria to the user; they must pass ``criteria_prompt=...`` when
    constructing the critic.
    """

    SIMILARITY = "similarity"
    """How semantically similar the actual value is to the expected value."""

    CORRECTNESS = "correctness"
    """How factually correct the actual value is vs. expected ground truth."""

    RELEVANCE = "relevance"
    """How relevant the actual value is to the expected topic/intent."""

    COMPLETENESS = "completeness"
    """How completely the actual value covers all aspects of the expected."""

    COHERENCE = "coherence"
    """Logical consistency and clarity of the actual value."""

    CUSTOM = "custom"
    """User-provided criteria — requires ``criteria_prompt`` at construction."""
