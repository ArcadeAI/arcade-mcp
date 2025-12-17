"""
Evaluation and capture mode execution logic for the CLI.

This module contains the async execution functions for running evaluations
and capture mode operations.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from rich.console import Console
from rich.text import Text
from tqdm import tqdm

from arcade_cli.display import display_eval_results
from arcade_cli.utils import filter_failed_evaluations

if TYPE_CHECKING:
    from arcade_evals import CaptureResult

logger = logging.getLogger(__name__)


# --- Result Types for Error Handling ---


@dataclass
class EvalTaskResult:
    """Result of running a single evaluation task."""

    suite_name: str
    model: str
    success: bool
    result: Any | None = None  # EvalResult on success
    error: str | None = None
    error_type: str | None = None

    @classmethod
    def from_success(cls, suite_name: str, model: str, result: Any) -> EvalTaskResult:
        """Create a successful result."""
        return cls(suite_name=suite_name, model=model, success=True, result=result)

    @classmethod
    def from_error(cls, suite_name: str, model: str, error: Exception) -> EvalTaskResult:
        """Create a failed result from an exception."""
        return cls(
            suite_name=suite_name,
            model=model,
            success=False,
            error=str(error),
            error_type=type(error).__name__,
        )


@dataclass
class CaptureTaskResult:
    """Result of running a single capture task."""

    suite_name: str
    model: str
    success: bool
    result: list[CaptureResult] | None = None  # List of CaptureResult on success
    error: str | None = None
    error_type: str | None = None

    @classmethod
    def from_success(
        cls, suite_name: str, model: str, result: list[CaptureResult]
    ) -> CaptureTaskResult:
        """Create a successful result."""
        return cls(suite_name=suite_name, model=model, success=True, result=result)

    @classmethod
    def from_error(cls, suite_name: str, model: str, error: Exception) -> CaptureTaskResult:
        """Create a failed result from an exception."""
        return cls(
            suite_name=suite_name,
            model=model,
            success=False,
            error=str(error),
            error_type=type(error).__name__,
        )


# --- Task Wrappers with Error Handling ---


async def _run_eval_task(
    suite_func: Callable[..., Any],
    model: str,
    provider_api_key: str | None,
    max_concurrent: int,
    provider: str,
) -> EvalTaskResult:
    """
    Run a single evaluation task with error handling.

    Returns EvalTaskResult with success/failure info instead of raising.
    """
    suite_name = suite_func.__name__

    try:
        result = await suite_func(
            provider_api_key=provider_api_key,
            model=model,
            max_concurrency=max_concurrent,
            provider=provider,
        )
        return EvalTaskResult.from_success(suite_name, model, result)

    except Exception as e:
        logger.warning(
            "Evaluation task failed: suite=%s, model=%s, error=%s: %s",
            suite_name,
            model,
            type(e).__name__,
            str(e),
        )
        return EvalTaskResult.from_error(suite_name, model, e)


async def _run_capture_task(
    suite_func: Callable[..., Any],
    model: str,
    provider_api_key: str | None,
    max_concurrent: int,
    provider: str,
    include_context: bool,
) -> CaptureTaskResult:
    """
    Run a single capture task with error handling.

    Returns CaptureTaskResult with success/failure info instead of raising.
    """
    suite_name = suite_func.__name__

    try:
        result = await suite_func(
            provider_api_key=provider_api_key,
            model=model,
            max_concurrency=max_concurrent,
            provider=provider,
            capture_mode=True,
            include_context=include_context,
        )
        return CaptureTaskResult.from_success(suite_name, model, result)

    except Exception as e:
        logger.warning(
            "Capture task failed: suite=%s, model=%s, error=%s: %s",
            suite_name,
            model,
            type(e).__name__,
            str(e),
        )
        return CaptureTaskResult.from_error(suite_name, model, e)


# --- Main Runner Functions ---


async def run_evaluations(
    eval_suites: list[Callable[..., Any]],
    models_list: list[str],
    provider_api_key: str | None,
    max_concurrent: int,
    provider: str,
    show_details: bool,
    output_file: str | None,
    failed_only: bool,
    console: Console,
) -> None:
    """
    Run evaluation suites and display results.

    Individual task failures are caught and reported without crashing the entire batch.

    Args:
        eval_suites: List of decorated evaluation suite functions.
        models_list: List of model names to run evaluations against.
        provider_api_key: API key for the provider.
        max_concurrent: Maximum concurrent evaluations.
        provider: Provider name (e.g., "openai", "anthropic").
        show_details: Whether to show detailed results.
        output_file: Optional file path to write results.
        failed_only: Whether to show only failed evaluations.
        console: Rich console for output.
    """
    tasks = []

    for suite_func in eval_suites:
        console.print(
            Text.assemble(
                ("Running evaluations in ", "bold"),
                (suite_func.__name__, "bold blue"),
            )
        )
        for model in models_list:
            task = asyncio.create_task(
                _run_eval_task(
                    suite_func=suite_func,
                    model=model,
                    provider_api_key=provider_api_key,
                    max_concurrent=max_concurrent,
                    provider=provider,
                )
            )
            tasks.append(task)

    # Track progress
    task_results: list[EvalTaskResult] = []
    with tqdm(total=len(tasks), desc="Evaluations Progress") as pbar:
        for f in asyncio.as_completed(tasks):
            result = await f
            task_results.append(result)
            pbar.update(1)

    # Separate successes and failures
    successful = [r for r in task_results if r.success]
    failed = [r for r in task_results if not r.success]

    # Report failures
    if failed:
        console.print(f"\n[bold yellow]⚠ {len(failed)} evaluation(s) failed:[/bold yellow]")
        for fail in failed:
            console.print(
                f"  - {fail.suite_name} ({fail.model}): [red]{fail.error_type}[/red] - {fail.error}"
            )

    # Process successful results
    all_evaluations = [r.result for r in successful if r.result is not None]

    if not all_evaluations:
        console.print("\n[bold red]No evaluations completed successfully.[/bold red]")
        return

    # Filter to show only failed evaluations if requested
    original_counts = None
    if failed_only:
        all_evaluations, original_counts = filter_failed_evaluations(all_evaluations)

    display_eval_results(
        all_evaluations,
        show_details=show_details,
        output_file=output_file,
        failed_only=failed_only,
        original_counts=original_counts,
    )

    # Summary when there were failures
    if failed:
        console.print(f"\n[bold]Summary:[/bold] {len(successful)} succeeded, {len(failed)} failed")


async def run_capture(
    eval_suites: list[Callable[..., Any]],
    models_list: list[str],
    provider_api_key: str | None,
    max_concurrent: int,
    provider: str,
    include_context: bool,
    capture_file: str | None,
    console: Console,
) -> None:
    """
    Run evaluation suites in capture mode and output results.

    Capture mode records tool calls without scoring them.
    Individual task failures are caught and reported without crashing the entire batch.

    Args:
        eval_suites: List of decorated evaluation suite functions.
        models_list: List of model names to run against.
        provider_api_key: API key for the provider.
        max_concurrent: Maximum concurrent operations.
        provider: Provider name (e.g., "openai", "anthropic").
        include_context: Whether to include system_message and additional_messages.
        capture_file: Optional file path to write JSON results.
        console: Rich console for output.
    """
    tasks = []

    for suite_func in eval_suites:
        console.print(
            Text.assemble(
                ("Capturing tool calls from ", "bold"),
                (suite_func.__name__, "bold cyan"),
            )
        )
        for model in models_list:
            task = asyncio.create_task(
                _run_capture_task(
                    suite_func=suite_func,
                    model=model,
                    provider_api_key=provider_api_key,
                    max_concurrent=max_concurrent,
                    provider=provider,
                    include_context=include_context,
                )
            )
            tasks.append(task)

    # Track progress
    task_results: list[CaptureTaskResult] = []
    with tqdm(total=len(tasks), desc="Capture Progress") as pbar:
        for f in asyncio.as_completed(tasks):
            result = await f
            task_results.append(result)
            pbar.update(1)

    # Separate successes and failures
    successful = [r for r in task_results if r.success]
    failed = [r for r in task_results if not r.success]

    # Report failures
    if failed:
        console.print(f"\n[bold yellow]⚠ {len(failed)} capture(s) failed:[/bold yellow]")
        for fail in failed:
            console.print(
                f"  - {fail.suite_name} ({fail.model}): [red]{fail.error_type}[/red] - {fail.error}"
            )

    # Collect successful captures
    all_captures: list[CaptureResult] = []
    for r in successful:
        if r.result is not None:
            all_captures.extend(r.result)

    if not all_captures:
        console.print("\n[bold red]No captures completed successfully.[/bold red]")
        return

    # Prepare output
    output_data = {
        "captures": [cap.to_dict(include_context=include_context) for cap in all_captures]
    }

    # Output to file or console
    if capture_file:
        with open(capture_file, "w") as outfile:
            json.dump(output_data, outfile, indent=2)
        console.print(f"\n✓ Capture results written to [bold]{capture_file}[/bold]")
    else:
        console.print("\n[bold]Capture Results:[/bold]")
        console.print(json.dumps(output_data, indent=2))

    # Summary
    total_cases = sum(len(cap.captured_cases) for cap in all_captures)
    total_calls = sum(
        sum(len(case.tool_calls) for case in cap.captured_cases) for cap in all_captures
    )
    console.print(
        f"\n[bold green]Captured {total_calls} tool calls across {total_cases} cases[/bold green]"
    )

    # Summary when there were failures
    if failed:
        console.print(f"\n[bold]Summary:[/bold] {len(successful)} succeeded, {len(failed)} failed")
