"""Comparative case builder for multi-track evaluations.

Provides a fluent API for defining evaluation cases that run against
multiple tool tracks with track-specific expected results and critics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from arcade_evals._evalsuite._types import (
    ComparativeCase,
    EvalRubric,
    ExpectedMCPToolCall,
    ExpectedToolCall,
)

if TYPE_CHECKING:
    from arcade_evals.critic import Critic


class ComparativeCaseBuilder:
    """Fluent builder for creating comparative cases.

    Example:
        builder = ComparativeCaseBuilder(
            suite=suite,
            name="weather_query",
            user_message="What's the weather?",
        )
        builder.for_track(
            "Google Weather",
            expected_tool_calls=[...],
            critics=[...],
        ).for_track(
            "OpenWeather",
            expected_tool_calls=[...],
            critics=[...],
        )
    """

    def __init__(
        self,
        suite: Any,  # EvalSuite - avoid circular import
        name: str,
        user_message: str,
        system_message: str = "",
        additional_messages: list[dict[str, str]] | None = None,
        rubric: EvalRubric | None = None,
    ) -> None:
        """Initialize the builder.

        Args:
            suite: The parent EvalSuite.
            name: Unique case name.
            user_message: User message (shared across tracks).
            system_message: System message (shared across tracks).
            additional_messages: Additional context (shared).
            rubric: Default rubric (shared, can be overridden).
        """
        self._suite = suite
        self._case = ComparativeCase(
            name=name,
            user_message=user_message,
            system_message=system_message,
            additional_messages=additional_messages or [],
            rubric=rubric,
        )

    def for_track(
        self,
        track_name: str,
        expected_tool_calls: list[ExpectedToolCall | ExpectedMCPToolCall],
        critics: list[Critic] | None = None,
    ) -> ComparativeCaseBuilder:
        """Add track-specific configuration.

        Args:
            track_name: The track name (must be registered via add_*_tools).
            expected_tool_calls: Expected tool calls for this track.
            critics: Critics for this track.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If track doesn't exist.
        """
        # Validate track exists
        if not self._suite._track_manager.has_track(track_name):
            available = self._suite._track_manager.get_track_names()
            raise ValueError(
                f"Track '{track_name}' not found. "
                f"Available tracks: {available}. "
                f"Register tracks first using add_*_tools(track=...)."
            )

        self._case.add_track_config(
            track_name=track_name,
            expected_tool_calls=expected_tool_calls,
            critics=critics,
        )
        return self

    def build(self) -> ComparativeCase:
        """Build and return the comparative case.

        Returns:
            The configured ComparativeCase.

        Raises:
            ValueError: If no tracks configured.
        """
        if not self._case.track_configs:
            raise ValueError(
                f"No tracks configured for comparative case '{self._case.name}'. "
                f"Use .for_track() to add at least one track configuration."
            )
        return self._case

    @property
    def case(self) -> ComparativeCase:
        """Access the underlying case for inspection.

        Note: This is primarily for testing. The case may be incomplete
        if tracks haven't been configured yet. Use build() to validate
        and finalize the case.

        Returns:
            The ComparativeCase (may be incomplete).
        """
        return self._case
