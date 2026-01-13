"""Shared types for eval suite modules.

This module contains dataclasses and types that are shared between
eval.py and the _evalsuite submodules, avoiding circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from arcade_evals.critic import Critic


@dataclass
class ExpectedToolCall:
    """
    Represents an expected tool call for a Python tool (registered via ToolCatalog).

    Use this for Python functions decorated with @tool.

    Attributes:
        func: The Python function itself.
        args: A dictionary containing the expected arguments for the tool.

    Example:
        ExpectedToolCall(func=my_tool_function, args={"x": 1, "y": 2})
        ExpectedToolCall(my_tool_function, {"x": 1})  # Positional args supported
    """

    func: Callable
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpectedMCPToolCall:
    """
    Represents an expected tool call identified by tool name (string).

    Use this for:
    - Tools loaded from MCP servers (local stdio or remote HTTP)
    - Tools loaded from Arcade Gateways
    - Manual tool definitions (dictionaries with name/description/inputSchema)

    Attributes:
        tool_name: The name of the tool (e.g., "Weather_GetCurrent").
        args: A dictionary containing the expected arguments for the tool.

    Example:
        ExpectedMCPToolCall(tool_name="Calculator_Add", args={"a": 5, "b": 3})
        ExpectedMCPToolCall("Calculator_Add", {"a": 5})  # Positional args supported
    """

    tool_name: str
    args: dict[str, Any] = field(default_factory=dict)


# Type alias for mixed usage (Python tools + MCP tools in same test case)
AnyExpectedToolCall = ExpectedToolCall | ExpectedMCPToolCall


@dataclass
class NamedExpectedToolCall:
    """
    Represents a tool call with its name and arguments.

    Attributes:
        name: The name of the tool.
        args: A dictionary containing the expected arguments for the tool.
    """

    name: str
    args: dict[str, Any]


@dataclass
class EvalRubric:
    """
    Defines the rubric for evaluating an AI model's performance on a task.

    Attributes:
        fail_threshold: The minimum score required to pass the evaluation (between 0.0 and 1.0).
        warn_threshold: The score threshold for issuing a warning (between 0.0 and 1.0).
        fail_on_tool_selection: Whether to fail the evaluation if the tool selection is incorrect.
        fail_on_tool_call_quantity: Whether to fail the evaluation if the number of tool calls is incorrect.
        tool_selection_weight: The weight assigned to the tool selection score (between 0.0 and 1.0).
    """

    fail_threshold: float = 0.8
    warn_threshold: float = 0.9
    fail_on_tool_selection: bool = True
    fail_on_tool_call_quantity: bool = True
    tool_selection_weight: float = 1.0

    def __str__(self) -> str:
        """Return a complete string representation of the rubric configuration."""
        return (
            f"EvalRubric(fail_threshold={self.fail_threshold}, "
            f"warn_threshold={self.warn_threshold}, "
            f"fail_on_tool_selection={self.fail_on_tool_selection}, "
            f"fail_on_tool_call_quantity={self.fail_on_tool_call_quantity}, "
            f"tool_selection_weight={self.tool_selection_weight})"
        )

    def __repr__(self) -> str:
        """Return the same string representation for repr."""
        return self.__str__()


@dataclass
class TrackConfig:
    """Configuration for a single track within a comparative case.

    Attributes:
        expected_tool_calls: Expected tool calls for this track.
        critics: Critics to evaluate tool arguments for this track.
    """

    expected_tool_calls: list[ExpectedToolCall | ExpectedMCPToolCall]
    critics: list[Critic] = field(default_factory=list)


@dataclass
class ComparativeCase:
    """A case that runs against multiple tracks for comparison.

    Shared context (messages) is defined once, while each track has
    its own expected tool calls and critics.

    Attributes:
        name: Unique case name.
        user_message: User message (shared across tracks).
        system_message: System message (shared across tracks).
        additional_messages: Additional context messages (shared).
        rubric: Evaluation rubric (shared, can be overridden per track).
        track_configs: Track-specific configurations.
    """

    name: str
    user_message: str
    system_message: str = ""
    additional_messages: list[dict[str, str]] = field(default_factory=list)
    rubric: EvalRubric | None = None
    track_configs: dict[str, TrackConfig] = field(default_factory=dict)

    def add_track_config(
        self,
        track_name: str,
        expected_tool_calls: list[ExpectedToolCall | ExpectedMCPToolCall],
        critics: list[Critic] | None = None,
    ) -> None:
        """Add configuration for a track.

        Args:
            track_name: The track name.
            expected_tool_calls: Expected tool calls for this track.
            critics: Critics for this track.

        Raises:
            ValueError: If track already configured.
        """
        if track_name in self.track_configs:
            raise ValueError(f"Track '{track_name}' already configured for case '{self.name}'.")
        self.track_configs[track_name] = TrackConfig(
            expected_tool_calls=expected_tool_calls,
            critics=critics or [],
        )

    def get_configured_tracks(self) -> list[str]:
        """Get list of tracks configured for this case.

        Returns:
            List of track names.
        """
        return list(self.track_configs.keys())
