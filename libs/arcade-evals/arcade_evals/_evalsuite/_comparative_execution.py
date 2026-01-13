"""Comparative evaluation execution mixin for EvalSuite.

This module provides the execution logic for comparative evaluations,
allowing the same cases to be run against multiple tool tracks.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from arcade_evals._evalsuite._comparative import ComparativeCaseBuilder
from arcade_evals._evalsuite._types import ComparativeCase, EvalRubric

if TYPE_CHECKING:
    from arcade_evals._evalsuite._providers import ProviderName
    from arcade_evals._evalsuite._tool_registry import EvalSuiteToolRegistry
    from arcade_evals._evalsuite._tracks import TrackManager


class _EvalSuiteComparativeMixin:
    """Mixin providing comparative evaluation execution methods."""

    # Type hints for attributes from EvalSuite
    name: str
    system_message: str
    rubric: EvalRubric  # EvalSuite always has a rubric (default_factory)
    max_concurrent: int
    _comparative_case_builders: list[ComparativeCaseBuilder]
    _track_manager: TrackManager
    _create_eval_case: Any  # Method from EvalSuite to create EvalCase
    _convert_to_named_expected_tool_call: Any  # Method from EvalSuite
    _add_none_critics: Any  # Method from EvalSuite
    _process_tool_calls: Any  # Method from EvalSuite
    _run_openai: Any  # Method from EvalSuite
    _run_anthropic: Any  # Method from EvalSuite

    def add_comparative_case(
        self,
        name: str,
        user_message: str,
        system_message: str | None = None,
        additional_messages: list[dict[str, str]] | None = None,
        rubric: EvalRubric | None = None,
    ) -> ComparativeCaseBuilder:
        """Create a comparative case that runs against multiple tool tracks.

        Use .for_track() on the returned builder to configure track-specific
        expected tool calls and critics.

        Args:
            name: Unique case name.
            user_message: User message (shared across all tracks).
            system_message: System message (shared, defaults to suite's system_message).
            additional_messages: Additional context messages (shared).
            rubric: Evaluation rubric (shared, defaults to suite's rubric).

        Returns:
            A ComparativeCaseBuilder for fluent track configuration.

        Example:
            suite.add_comparative_case(
                name="weather_query",
                user_message="What's the weather in NYC?",
            ).for_track(
                "Google Weather",
                expected_tool_calls=[ExpectedMCPToolCall("Google_GetWeather", city="NYC")],
                critics=[RangeCritic(field="temperature", min_val=0, max_val=100)],
            ).for_track(
                "OpenWeather",
                expected_tool_calls=[ExpectedMCPToolCall("get_current", location="NYC")],
                critics=[RangeCritic(field="main.temp", min_val=273, max_val=373)],
            )
        """
        builder = ComparativeCaseBuilder(
            suite=self,
            name=name,
            user_message=user_message,
            system_message=system_message or self.system_message,
            additional_messages=additional_messages,
            rubric=rubric or self.rubric,
        )
        # Store the builder (validated at execution time to allow fluent configuration)
        self._comparative_case_builders.append(builder)
        return builder

    async def run_comparative(
        self,
        client: Any,
        model: str,
        provider: ProviderName = "openai",
    ) -> dict[str, dict[str, Any]]:
        """Run comparative cases across all configured tracks.

        Args:
            client: The LLM client instance.
            model: The model to evaluate.
            provider: The provider name.

        Returns:
            Dictionary mapping track names to their results.
            Each track result contains:
                - model: The model name
                - suite_name: The suite name
                - track_name: The track name
                - cases: List of case results

        Example:
            results = await suite.run_comparative(client, "gpt-4o")
            # results["Google Weather"]["cases"][0] -> first case result
            # results["OpenWeather"]["cases"][0] -> same case, different track
        """
        if not self._comparative_case_builders:
            raise ValueError(
                "No comparative cases defined. Use add_comparative_case() to add cases."
            )

        # Build and validate all cases upfront
        comparative_cases: list[ComparativeCase] = []
        all_required_tracks: set[str] = set()
        for builder in self._comparative_case_builders:
            comp_case = builder.build()  # Validates that tracks are configured
            comparative_cases.append(comp_case)
            all_required_tracks.update(comp_case.track_configs.keys())

        # Validate all required tracks exist upfront (fail fast)
        missing_tracks = [t for t in all_required_tracks if not self._track_manager.has_track(t)]
        if missing_tracks:
            available = self._track_manager.get_track_names()
            raise ValueError(
                f"Missing track registries: {missing_tracks}. "
                f"Available tracks: {available}. "
                f"Ensure you registered tools with track='<track_name>'."
            )

        # Initialize track results structure
        track_results: dict[str, dict[str, Any]] = {}
        for track_name in all_required_tracks:
            track_results[track_name] = {
                "model": model,
                "suite_name": self.name,
                "track_name": track_name,
                "rubric": self.rubric,
                "cases": [],
            }

        # Prepare all async tasks for parallel execution
        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks: list[tuple[str, Any]] = []  # (track_name, task)

        for comp_case in comparative_cases:
            for track_name, track_config in comp_case.track_configs.items():
                registry = self._track_manager.get_registry(track_name)
                # We validated above that all registries exist, so this should never be None
                if registry is None:
                    raise RuntimeError(
                        f"Registry for '{track_name}' unexpectedly None after validation"
                    )

                # Create EvalCase from comparative case + track config
                expected_tool_calls = [
                    self._convert_to_named_expected_tool_call(tc)
                    for tc in track_config.expected_tool_calls
                ]
                critics = self._add_none_critics(expected_tool_calls, track_config.critics or [])

                eval_case = self._create_eval_case(
                    name=comp_case.name,
                    system_message=comp_case.system_message,
                    user_message=comp_case.user_message,
                    expected_tool_calls=expected_tool_calls,
                    rubric=comp_case.rubric or self.rubric,
                    critics=critics,
                    additional_messages=comp_case.additional_messages,
                )

                # Create task for this case+track combination
                async def run_track_case(
                    _case: Any,  # EvalCase
                    _reg: EvalSuiteToolRegistry,
                    _t_name: str,
                ) -> dict[str, Any]:
                    async with semaphore:
                        start = time.time()
                        print(f"    [TASK START] {_case.name} @ {_t_name}", flush=True)
                        if provider == "anthropic":
                            predicted_args = await self._run_anthropic(
                                client, model, _case, registry=_reg
                            )
                        else:
                            predicted_args = await self._run_openai(
                                client, model, _case, registry=_reg
                            )
                        elapsed = time.time() - start
                        print(
                            f"    [TASK DONE] {_case.name} @ {_t_name} ({elapsed:.1f}s)",
                            flush=True,
                        )

                        filled_actual_tool_calls = self._process_tool_calls(
                            predicted_args, registry=_reg
                        )
                        evaluation = _case.evaluate(filled_actual_tool_calls)

                        return {
                            "name": _case.name,
                            "track": _t_name,
                            "input": _case.user_message,
                            "system_message": _case.system_message,
                            "additional_messages": _case.additional_messages,
                            "expected_tool_calls": [
                                {"name": tc.name, "args": tc.args}
                                for tc in _case.expected_tool_calls
                            ],
                            "predicted_tool_calls": [
                                {"name": name, "args": args}
                                for name, args in filled_actual_tool_calls
                            ],
                            "evaluation": evaluation,
                        }

                task = run_track_case(eval_case, registry, track_name)
                tasks.append((track_name, task))

        # Execute all tasks in parallel (respecting max_concurrent via semaphore)
        results = await asyncio.gather(*[task for _, task in tasks])

        # Organize results by track
        for (track_name, _), result in zip(tasks, results):
            track_results[track_name]["cases"].append(result)

        return track_results
