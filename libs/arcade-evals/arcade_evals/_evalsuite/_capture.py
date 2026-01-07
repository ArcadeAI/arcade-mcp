"""Capture mode mixin for EvalSuite.

This module provides the capture functionality as a mixin class,
keeping it separate from the main evaluation logic in eval.py.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from arcade_evals.capture import CapturedCase, CapturedToolCall, CaptureResult

if TYPE_CHECKING:
    from arcade_evals._evalsuite._comparative import ComparativeCaseBuilder
    from arcade_evals._evalsuite._providers import ProviderName
    from arcade_evals._evalsuite._tool_registry import EvalSuiteToolRegistry
    from arcade_evals._evalsuite._tracks import TrackManager
    from arcade_evals._evalsuite._types import EvalRubric
    from arcade_evals.eval import EvalCase


class _EvalSuiteCaptureMixin:
    """Mixin providing capture mode functionality for EvalSuite."""

    # These attributes are defined in EvalSuite
    name: str
    cases: list[EvalCase]
    max_concurrent: int
    rubric: EvalRubric
    _internal_registry: EvalSuiteToolRegistry | None
    _comparative_case_builders: list[ComparativeCaseBuilder]
    _track_manager: TrackManager

    # These methods are defined in EvalSuite
    async def _run_openai(
        self,
        client: Any,
        model: str,
        case: EvalCase,
        registry: EvalSuiteToolRegistry | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        raise NotImplementedError  # Implemented in EvalSuite

    async def _run_anthropic(
        self,
        client: Any,
        model: str,
        case: EvalCase,
        registry: EvalSuiteToolRegistry | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        raise NotImplementedError  # Implemented in EvalSuite

    def _process_tool_calls(
        self,
        tool_calls: list[tuple[str, dict[str, Any]]],
        registry: EvalSuiteToolRegistry | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        raise NotImplementedError  # Implemented in EvalSuite

    def _create_eval_case(self, *args: Any, **kwargs: Any) -> EvalCase:
        raise NotImplementedError  # Implemented in EvalSuite

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

        Handles both regular cases and comparative cases. For comparative cases,
        each track is captured separately with its own tool registry.

        Args:
            client: The LLM client instance (AsyncOpenAI or AsyncAnthropic).
            model: The model to use.
            provider: The provider name ("openai" or "anthropic").
            include_context: Whether to include system_message and additional_messages
                           in the output.

        Returns:
            A CaptureResult containing all captured tool calls.
        """
        all_captured: list[CapturedCase] = []
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def capture_case(
            case: EvalCase,
            registry: EvalSuiteToolRegistry | None = None,
            track: str | None = None,
        ) -> CapturedCase:
            """Capture a case using the specified registry."""
            async with semaphore:
                use_registry = registry or self._internal_registry
                if use_registry is None or use_registry.tool_count() == 0:
                    raise ValueError(
                        "No tools registered. Use add_* convenience methods or pass catalog=ToolCatalog."
                    )

                # Get tool calls based on provider
                if provider == "anthropic":
                    predicted_args = await self._run_anthropic(
                        client, model, case, registry=use_registry
                    )
                else:
                    predicted_args = await self._run_openai(
                        client, model, case, registry=use_registry
                    )

                # Process tool calls (resolve names, fill defaults)
                filled_actual_tool_calls = self._process_tool_calls(
                    predicted_args, registry=use_registry
                )

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
                    track_name=track,
                )

        # Capture regular cases (using default registry)
        if self.cases:
            tasks = [capture_case(case) for case in self.cases]
            regular_captured = await asyncio.gather(*tasks)
            all_captured.extend(regular_captured)

        # Capture comparative cases (each track separately)
        if self._comparative_case_builders:
            for builder in self._comparative_case_builders:
                comp_case = builder.build()

                # For each track configured in this comparative case
                for track_name in comp_case.track_configs:
                    if not self._track_manager.has_track(track_name):
                        continue  # Skip missing tracks

                    track_registry = self._track_manager.get_registry(track_name)

                    # Create an EvalCase from the comparative case
                    # Use case-specific rubric if defined, otherwise use suite default
                    case_rubric = comp_case.rubric or self.rubric
                    eval_case = self._create_eval_case(
                        name=comp_case.name,  # Don't embed track in name - use track_name field
                        user_message=comp_case.user_message,
                        system_message=comp_case.system_message,
                        additional_messages=comp_case.additional_messages,
                        expected_tool_calls=[],  # Not needed for capture
                        rubric=case_rubric,
                        critics=[],  # Not needed for capture
                    )

                    captured = await capture_case(
                        eval_case, registry=track_registry, track=track_name
                    )
                    all_captured.append(captured)

        return CaptureResult(
            suite_name=self.name,
            model=model,
            provider=provider,
            captured_cases=list(all_captured),
        )
