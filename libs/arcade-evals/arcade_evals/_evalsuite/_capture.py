"""Capture mode mixin for EvalSuite.

This module provides the capture functionality as a mixin class,
keeping it separate from the main evaluation logic in eval.py.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from arcade_evals.capture import CapturedCase, CapturedToolCall, CaptureResult

if TYPE_CHECKING:
    from arcade_evals._evalsuite._providers import ProviderName
    from arcade_evals._evalsuite._tool_registry import EvalSuiteToolRegistry
    from arcade_evals.eval import EvalCase


class _EvalSuiteCaptureMixin:
    """Mixin providing capture mode functionality for EvalSuite."""

    # These attributes are defined in EvalSuite
    name: str
    cases: list[EvalCase]
    max_concurrent: int
    _internal_registry: EvalSuiteToolRegistry | None

    # These methods are defined in EvalSuite
    async def _run_openai(
        self, client: Any, model: str, case: EvalCase
    ) -> list[tuple[str, dict[str, Any]]]: ...

    async def _run_anthropic(
        self, client: Any, model: str, case: EvalCase
    ) -> list[tuple[str, dict[str, Any]]]: ...

    def _process_tool_calls(
        self, tool_calls: list[tuple[str, dict[str, Any]]]
    ) -> list[tuple[str, dict[str, Any]]]: ...

    async def capture(
        self,
        client: Any,  # AsyncOpenAI | AsyncAnthropic
        model: str,
        provider: ProviderName = "openai",
        include_context: bool = False,
    ) -> CaptureResult:
        """
        Run the evaluation suite in capture mode - records tool calls without scoring.

        Capture mode runs each case and records the tool calls made by the model,
        without evaluating or scoring them. This is useful for:
        - Generating expected tool calls for new test cases
        - Debugging model behavior
        - Creating baseline recordings

        Args:
            client: The LLM client instance (AsyncOpenAI or AsyncAnthropic).
            model: The model to use.
            provider: The provider name ("openai" or "anthropic").
            include_context: Whether to include system_message and additional_messages
                           in the output.

        Returns:
            A CaptureResult containing all captured tool calls.
        """
        captured_cases: list[CapturedCase] = []
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def capture_case(case: EvalCase) -> CapturedCase:
            async with semaphore:
                if self._internal_registry is None or self._internal_registry.tool_count() == 0:
                    raise ValueError(
                        "No tools registered. Use add_* convenience methods or pass catalog=ToolCatalog."
                    )

                # Get tool calls based on provider
                if provider == "anthropic":
                    predicted_args = await self._run_anthropic(client, model, case)
                else:
                    predicted_args = await self._run_openai(client, model, case)

                # Process tool calls (resolve names, fill defaults)
                filled_actual_tool_calls = self._process_tool_calls(predicted_args)

                # Convert to CapturedToolCall objects
                tool_calls = [
                    CapturedToolCall(name=name, args=args)
                    for name, args in filled_actual_tool_calls
                ]

                return CapturedCase(
                    case_name=case.name,
                    user_message=case.user_message,
                    tool_calls=tool_calls,
                    system_message=case.system_message if include_context else None,
                    additional_messages=case.additional_messages if include_context else None,
                )

        tasks = [capture_case(case) for case in self.cases]
        captured_cases = await asyncio.gather(*tasks)

        return CaptureResult(
            suite_name=self.name,
            model=model,
            provider=provider,
            captured_cases=list(captured_cases),
        )
