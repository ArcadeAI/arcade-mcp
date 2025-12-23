"""
Capture mode for EvalSuite.

Capture mode runs evaluation cases and records tool calls from the model
without scoring or evaluating them. This is useful for:
- Generating expected tool calls for new test cases
- Debugging model behavior
- Creating baseline recordings
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from openai import AsyncOpenAI

if TYPE_CHECKING:
    from arcade_evals.eval import EvalSuite


@dataclass
class CapturedToolCall:
    """
    A captured tool call from the model during capture mode.

    Attributes:
        name: The name of the tool that was called.
        args: The arguments passed to the tool.
    """

    name: str
    args: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"name": self.name, "args": self.args}


@dataclass
class CapturedCase:
    """
    Result of running a single case in capture mode.

    Attributes:
        case_name: The name of the evaluation case.
        user_message: The user message that triggered the tool calls.
        tool_calls: List of tool calls made by the model.
        system_message: The system message (included if include_context is True).
        additional_messages: Additional messages (included if include_context is True).
        track_name: The track name for comparative captures (None for regular cases).
    """

    case_name: str
    user_message: str
    tool_calls: list[CapturedToolCall] = field(default_factory=list)
    system_message: str | None = None
    additional_messages: list[dict[str, Any]] | None = None
    track_name: str | None = None

    @staticmethod
    def _try_parse_json(value: str) -> Any:
        """Try to parse a JSON string, returning the original string if parsing fails."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    @staticmethod
    def _normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Normalize additional_messages by parsing JSON strings into proper objects.

        OpenAI returns:
        - Tool call arguments as JSON strings in assistant messages
        - Tool response content as JSON strings in tool messages

        For cleaner output, we parse these into proper objects.
        """
        normalized = []
        for msg in messages:
            msg_copy = dict(msg)

            # Parse tool call arguments in assistant messages
            if "tool_calls" in msg_copy and isinstance(msg_copy["tool_calls"], list):
                normalized_tool_calls = []
                for tc in msg_copy["tool_calls"]:
                    tc_copy = dict(tc)
                    if "function" in tc_copy and isinstance(tc_copy["function"], dict):
                        func = dict(tc_copy["function"])
                        if "arguments" in func and isinstance(func["arguments"], str):
                            func["arguments"] = CapturedCase._try_parse_json(func["arguments"])
                        tc_copy["function"] = func
                    normalized_tool_calls.append(tc_copy)
                msg_copy["tool_calls"] = normalized_tool_calls

            # Parse content in tool response messages
            if msg_copy.get("role") == "tool" and isinstance(msg_copy.get("content"), str):
                msg_copy["content"] = CapturedCase._try_parse_json(msg_copy["content"])

            normalized.append(msg_copy)
        return normalized

    def to_dict(self, include_context: bool = False) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "case_name": self.case_name,
            "user_message": self.user_message,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
        }
        if self.track_name:
            result["track_name"] = self.track_name
        if include_context:
            result["system_message"] = self.system_message
            # Normalize additional_messages to parse JSON string arguments
            raw_messages = self.additional_messages or []
            result["additional_messages"] = self._normalize_messages(raw_messages)
        return result


@dataclass
class CaptureResult:
    """
    Result of running an EvalSuite in capture mode.

    Attributes:
        suite_name: The name of the evaluation suite.
        model: The model used for capture.
        provider: The provider used (openai, anthropic).
        captured_cases: List of captured cases with tool calls.
    """

    suite_name: str
    model: str
    provider: str
    captured_cases: list[CapturedCase] = field(default_factory=list)

    def to_dict(self, include_context: bool = False) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "suite_name": self.suite_name,
            "model": self.model,
            "provider": self.provider,
            "captured_cases": [c.to_dict(include_context) for c in self.captured_cases],
        }

    def to_json(self, include_context: bool = False, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(include_context), indent=indent)

    def write_to_file(self, file_path: str, include_context: bool = False, indent: int = 2) -> None:
        """Write capture results to a JSON file."""
        with open(file_path, "w") as f:
            f.write(self.to_json(include_context, indent))


# --- Helper functions for running capture mode ---


async def _capture_with_openai(
    suite: EvalSuite, api_key: str, model: str, include_context: bool = False
) -> CaptureResult:
    """Run capture mode with OpenAI client."""
    async with AsyncOpenAI(api_key=api_key) as client:
        return await suite.capture(
            client, model, provider="openai", include_context=include_context
        )


async def _capture_with_anthropic(
    suite: EvalSuite, api_key: str, model: str, include_context: bool = False
) -> CaptureResult:
    """Run capture mode with Anthropic client."""
    try:
        from anthropic import AsyncAnthropic
    except ImportError as e:
        raise ImportError(
            "The 'anthropic' package is required for Anthropic provider. "
            "Install it with: pip install anthropic"
        ) from e

    async with AsyncAnthropic(api_key=api_key) as client:
        return await suite.capture(
            client, model, provider="anthropic", include_context=include_context
        )
