"""
Evaluation and capture mode execution logic for the CLI.

This module contains the async execution functions for running evaluations
and capture mode operations.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.text import Text

from arcade_cli.display import display_eval_results
from arcade_cli.formatters import get_capture_formatter
from arcade_cli.utils import ModelSpec, filter_failed_evaluations

if TYPE_CHECKING:
    from arcade_evals import CaptureResult

logger = logging.getLogger(__name__)


# All supported output formats
ALL_FORMATS = ["txt", "md", "html", "json"]


def parse_output_formats(format_str: str, console: Console | None = None) -> list[str]:
    """
    Parse output format string into a list of formats.

    Supports:
    - Single format: "md" -> ["md"]
    - Comma-separated: "md,html" -> ["md", "html"]
    - "all" keyword: "all" -> ["txt", "md", "html", "json"]

    Args:
        format_str: The format string from CLI.
        console: Optional Rich console for error messages (unused now - raises instead).

    Returns:
        List of valid format strings.

    Raises:
        ValueError: If any invalid formats are provided.
    """
    if format_str.lower() == "all":
        return ALL_FORMATS.copy()

    formats = [f.strip().lower() for f in format_str.split(",")]
    valid_formats = [f for f in formats if f in ALL_FORMATS]
    invalid_formats = [f for f in formats if f and f not in ALL_FORMATS]

    # Fail fast on invalid formats (parse-time validation)
    if invalid_formats:
        valid_list = ", ".join(ALL_FORMATS)
        raise ValueError(
            f"Invalid format(s): {', '.join(invalid_formats)}. Valid formats: {valid_list}"
        )

    return valid_formats


# --- Result Types for Error Handling ---


@dataclass
class EvalTaskResult:
    """Result of running a single evaluation task."""

    suite_name: str
    model: str
    provider: str
    success: bool
    result: Any | None = None  # EvalResult on success
    error: str | None = None
    error_type: str | None = None

    @property
    def display_name(self) -> str:
        """Get display name in format 'provider/model'."""
        return f"{self.provider}/{self.model}"

    @classmethod
    def from_success(
        cls, suite_name: str, model: str, provider: str, result: Any
    ) -> EvalTaskResult:
        """Create a successful result."""
        return cls(
            suite_name=suite_name, model=model, provider=provider, success=True, result=result
        )

    @classmethod
    def from_error(
        cls, suite_name: str, model: str, provider: str, error: Exception
    ) -> EvalTaskResult:
        """Create a failed result from an exception."""
        return cls(
            suite_name=suite_name,
            model=model,
            provider=provider,
            success=False,
            error=str(error),
            error_type=type(error).__name__,
        )


@dataclass
class CaptureTaskResult:
    """Result of running a single capture task."""

    suite_name: str
    model: str
    provider: str
    success: bool
    result: list[CaptureResult] | None = None  # List of CaptureResult on success
    error: str | None = None
    error_type: str | None = None

    @property
    def display_name(self) -> str:
        """Get display name in format 'provider/model'."""
        return f"{self.provider}/{self.model}"

    @classmethod
    def from_success(
        cls, suite_name: str, model: str, provider: str, result: list[CaptureResult]
    ) -> CaptureTaskResult:
        """Create a successful result."""
        return cls(
            suite_name=suite_name, model=model, provider=provider, success=True, result=result
        )

    @classmethod
    def from_error(
        cls, suite_name: str, model: str, provider: str, error: Exception
    ) -> CaptureTaskResult:
        """Create a failed result from an exception."""
        return cls(
            suite_name=suite_name,
            model=model,
            provider=provider,
            success=False,
            error=str(error),
            error_type=type(error).__name__,
        )


# --- Task Wrappers with Error Handling ---


async def _run_eval_task(
    suite_func: Callable[..., Any],
    model_spec: ModelSpec,
    max_concurrent: int,
    include_context: bool = False,
) -> EvalTaskResult:
    """
    Run a single evaluation task with error handling.

    Returns EvalTaskResult with success/failure info instead of raising.
    """
    suite_name = suite_func.__name__

    try:
        result = await suite_func(
            provider_api_key=model_spec.api_key,
            model=model_spec.model,
            max_concurrency=max_concurrent,
            provider=model_spec.provider.value,
            include_context=include_context,
        )
        return EvalTaskResult.from_success(
            suite_name, model_spec.model, model_spec.provider.value, result
        )

    except Exception as e:
        logger.warning(
            "Evaluation task failed: suite=%s, model=%s, provider=%s, error=%s: %s",
            suite_name,
            model_spec.model,
            model_spec.provider.value,
            type(e).__name__,
            str(e),
            exc_info=True,  # Include full traceback for debugging
        )
        return EvalTaskResult.from_error(suite_name, model_spec.model, model_spec.provider.value, e)


async def _run_capture_task(
    suite_func: Callable[..., Any],
    model_spec: ModelSpec,
    max_concurrent: int,
    include_context: bool,
) -> CaptureTaskResult:
    """
    Run a single capture task with error handling.

    Returns CaptureTaskResult with success/failure info instead of raising.
    """
    suite_name = suite_func.__name__

    try:
        result = await suite_func(
            provider_api_key=model_spec.api_key,
            model=model_spec.model,
            max_concurrency=max_concurrent,
            provider=model_spec.provider.value,
            capture_mode=True,
            include_context=include_context,
        )
        return CaptureTaskResult.from_success(
            suite_name, model_spec.model, model_spec.provider.value, result
        )

    except Exception as e:
        logger.warning(
            "Capture task failed: suite=%s, model=%s, provider=%s, error=%s: %s",
            suite_name,
            model_spec.model,
            model_spec.provider.value,
            type(e).__name__,
            str(e),
            exc_info=True,  # Include full traceback for debugging
        )
        return CaptureTaskResult.from_error(
            suite_name, model_spec.model, model_spec.provider.value, e
        )


# --- Main Runner Functions ---


async def run_evaluations(
    eval_suites: list[Callable[..., Any]],
    model_specs: list[ModelSpec],
    max_concurrent: int,
    show_details: bool,
    output_file: str | None,
    output_format: str,
    failed_only: bool,
    console: Console,
    include_context: bool = False,
) -> None:
    """
    Run evaluation suites and display results.

    Individual task failures are caught and reported without crashing the entire batch.

    Args:
        eval_suites: List of decorated evaluation suite functions.
        model_specs: List of ModelSpec objects containing provider, model, and API key.
        max_concurrent: Maximum concurrent evaluations.
        show_details: Whether to show detailed results.
        output_file: Optional file path to write results.
        output_format: Format for file output ('txt', 'md').
        failed_only: Whether to show only failed evaluations.
        console: Rich console for output.
        include_context: Whether to include system_message and additional_messages.
    """
    tasks = []

    for suite_func in eval_suites:
        console.print(
            Text.assemble(
                ("Running evaluations in ", "bold"),
                (suite_func.__name__, "bold blue"),
            )
        )
        for model_spec in model_specs:
            task = asyncio.create_task(
                _run_eval_task(
                    suite_func=suite_func,
                    model_spec=model_spec,
                    max_concurrent=max_concurrent,
                    include_context=include_context,
                )
            )
            tasks.append(task)

    # Track progress with Rich progress bar (compatible with Rich console)
    # Note: task_results is collected synchronously as each async task completes.
    # The append() is atomic in CPython due to the GIL, and we await each future
    # sequentially within the for-loop, so this is safe.
    task_results: list[EvalTaskResult] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False,
    ) as progress:
        task_id = progress.add_task("[cyan]Running evaluations...", total=len(tasks))
        for f in asyncio.as_completed(tasks):
            result = await f
            task_results.append(result)
            # Update progress with completed task info
            progress.update(
                task_id,
                advance=1,
                description=f"[cyan]Completed: {result.suite_name} ({result.display_name})",
            )

    # Separate successes and failures
    successful = [r for r in task_results if r.success]
    failed = [r for r in task_results if not r.success]

    # Report failures
    if failed:
        console.print(f"\n[bold yellow]⚠️  {len(failed)} evaluation(s) failed:[/bold yellow]")
        for fail in failed:
            console.print(
                f"  • {fail.suite_name} ({fail.display_name}): [red]{fail.error_type}[/red] - {fail.error}"
            )

    # Process successful results
    # Normalize results structure: ensure each result is a list (for consistent formatting)
    # - Regular evals return a single dict -> wrap in list
    # - Comparative evals return a list of dicts -> keep as is
    all_evaluations: list[list[dict[str, Any]]] = []
    for r in successful:
        if r.result is None:
            continue
        if isinstance(r.result, list):
            # Comparative eval: already a list of results (one per track)
            all_evaluations.append(r.result)
        else:
            # Regular eval: single dict, wrap in list for consistent structure
            all_evaluations.append([r.result])

    if not all_evaluations:
        console.print("\n[bold red]❌ No evaluations completed successfully.[/bold red]")
        return

    # Filter to show only failed evaluations if requested
    original_counts = None
    if failed_only:
        all_evaluations, original_counts = filter_failed_evaluations(all_evaluations)

    # Parse output_format as a list (handles comma-separated and "all")
    output_formats = parse_output_formats(output_format, console)

    display_eval_results(
        all_evaluations,
        show_details=show_details,
        output_file=output_file,
        failed_only=failed_only,
        original_counts=original_counts,
        output_formats=output_formats,
        include_context=include_context,
    )

    # Summary when there were failures
    if failed:
        console.print(f"\n[bold]Summary:[/bold] {len(successful)} succeeded, {len(failed)} failed")


async def run_capture(
    eval_suites: list[Callable[..., Any]],
    model_specs: list[ModelSpec],
    max_concurrent: int,
    include_context: bool,
    output_file: str | None,
    output_format: str,
    console: Console,
) -> None:
    """
    Run evaluation suites in capture mode and output results.

    Capture mode records tool calls without scoring them.
    Individual task failures are caught and reported without crashing the entire batch.

    Args:
        eval_suites: List of decorated evaluation suite functions.
        model_specs: List of ModelSpec objects containing provider, model, and API key.
        max_concurrent: Maximum concurrent operations.
        include_context: Whether to include system_message and additional_messages.
        output_file: Optional file path to write results.
        output_format: Output format ('json', 'txt', 'md', 'html').
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
        for model_spec in model_specs:
            task = asyncio.create_task(
                _run_capture_task(
                    suite_func=suite_func,
                    model_spec=model_spec,
                    max_concurrent=max_concurrent,
                    include_context=include_context,
                )
            )
            tasks.append(task)

    # Track progress with Rich progress bar (compatible with Rich console)
    # Note: task_results is collected synchronously as each async task completes.
    # The append() is atomic in CPython due to the GIL, and we await each future
    # sequentially within the for-loop, so this is safe.
    task_results: list[CaptureTaskResult] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False,
    ) as progress:
        task_id = progress.add_task("[cyan]Capturing tool calls...", total=len(tasks))
        for f in asyncio.as_completed(tasks):
            result = await f
            task_results.append(result)
            # Update progress with completed task info
            progress.update(
                task_id,
                advance=1,
                description=f"[cyan]Completed: {result.suite_name} ({result.display_name})",
            )

    # Separate successes and failures
    successful = [r for r in task_results if r.success]
    failed = [r for r in task_results if not r.success]

    # Report failures
    if failed:
        console.print(f"\n[bold yellow]⚠️  {len(failed)} capture(s) failed:[/bold yellow]")
        for fail in failed:
            console.print(
                f"  • {fail.suite_name} ({fail.display_name}): [red]{fail.error_type}[/red] - {fail.error}"
            )

    # Collect successful captures
    all_captures: list[CaptureResult] = []
    for r in successful:
        if r.result is not None:
            all_captures.extend(r.result)

    if not all_captures:
        console.print("\n[bold red]❌ No captures completed successfully.[/bold red]")
        return

    # Parse output formats (handles comma-separated and "all")
    output_formats = parse_output_formats(output_format, console)

    # Output to file(s) or console
    if output_file:
        # Get base path without extension
        base_path = Path(output_file)
        base_name = base_path.stem
        parent_dir = base_path.parent

        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            console.print(
                f"\n[red]❌ Error: Permission denied creating directory {parent_dir}[/red]"
            )
            return
        except OSError as e:
            console.print(f"\n[red]❌ Error creating directory: {e}[/red]")
            return

        for fmt in output_formats:
            # Define file_path early so it's available in exception handlers
            file_path = parent_dir / f"{base_name}.{fmt}"
            try:
                formatter = get_capture_formatter(fmt)
                formatted_output = formatter.format(all_captures, include_context=include_context)

                # Build output path with proper extension
                file_path = parent_dir / f"{base_name}.{formatter.file_extension}"

                with open(file_path, "w", encoding="utf-8") as outfile:
                    outfile.write(formatted_output)
                console.print(
                    f"\n[green]✓ Capture results written to[/green] [bold]{file_path}[/bold]"
                )

            except ValueError as e:
                console.print(f"\n[red]❌ {e}[/red]")
            except PermissionError:
                console.print(f"\n[red]❌ Error: Permission denied writing to {file_path}[/red]")
            except OSError as e:
                console.print(f"\n[red]❌ Error writing file: {e}[/red]")
    else:
        # Console output: always use JSON for best copy-paste experience
        console.print("\n[bold]Capture Results:[/bold]")
        json_formatter = get_capture_formatter("json")
        console.print(json_formatter.format(all_captures, include_context=include_context))

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
